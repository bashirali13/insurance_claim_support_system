"""The orchestrator for "File a new claim" (contracts/agents.md).

It passes validated contracts between agents, never interprets claims itself, never prints, and
turns every failure into a safe TaskResult with a status-only report.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import openai
from pydantic import ValidationError
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior

from claim_intake import rules
from claim_intake.agents import Agents, assessment, intake, risk, summary
from claim_intake.contracts import (
    ClaimAssessment,
    ClaimRecord,
    CustomerReply,
    EventLogEntry,
    HistoryEntry,
    InternalReport,
    MenuTask,
    PipelineStep,
    ProcessingStatus,
    RawSubmission,
    RiskAssessment,
    TaskResult,
    Team,
)
from claim_intake.dates import add_business_days
from claim_intake.pii import find_pii
from claim_intake.reporting import TASK_WORDING, format_follow_up, render_status_only_report
from claim_intake.storage import ClaimStore, EventLog, ReportWriter

PROGRESS_LABELS = (
    "Protecting your personal information",
    "Reviewing what happened",
    "Checking if a specialist should help",
    "Preparing your summary",
)
TRY_AGAIN = "We couldn't finish processing right now. Please try again shortly."
COULD_NOT_SAVE = "We couldn't save your request. Please try again."
FAILURE_MESSAGES = {
    ProcessingStatus.FAILED_MODEL_ERROR: TRY_AGAIN,
    ProcessingStatus.FAILED_VALIDATION: TRY_AGAIN,
    ProcessingStatus.FAILED_OUTPUT: COULD_NOT_SAVE,
}
PRIVACY_REVIEW_DAYS = 3
MODEL_RETRIES = 2
TRANSIENT_MODEL_ERRORS = (ModelAPIError, TimeoutError, openai.APIConnectionError)


@dataclass(frozen=True)
class Deps:
    agents: Agents
    store: ClaimStore
    reports: ReportWriter
    events: EventLog
    now: Callable[[], datetime]


class StepFailed(Exception):
    def __init__(self, status: ProcessingStatus, step: PipelineStep, error_category: str):
        self.status, self.step, self.error_category = status, step, error_category


def _status_for(exc: Exception) -> ProcessingStatus:
    if isinstance(exc, UnexpectedModelBehavior | ValidationError):
        return ProcessingStatus.FAILED_VALIDATION
    if isinstance(exc, TRANSIENT_MODEL_ERRORS):
        return ProcessingStatus.FAILED_MODEL_ERROR
    if isinstance(exc, OSError):
        return ProcessingStatus.FAILED_OUTPUT
    raise exc


def with_model_retries[T](call: Callable[[], T]) -> T:
    """Retry temporary model failures; invalid output is retried inside each agent instead."""
    for attempt in range(MODEL_RETRIES + 1):
        try:
            return call()
        except TRANSIENT_MODEL_ERRORS:
            if attempt == MODEL_RETRIES:
                raise
    raise AssertionError("unreachable")


class TaskRun:
    """One task run: tracks the claim number and writes one event-log line per step.

    `claim_id` is preset for an existing claim. Only a number this run reserved itself is ever
    released on failure, so a failed update can never delete a customer's claim.
    """

    def __init__(
        self, deps: Deps, task: MenuTask = MenuTask.FILE_CLAIM, claim_id: str | None = None
    ):
        self.deps = deps
        self.filed_at = deps.now()
        self.claim_id = claim_id
        self.task = task
        self.reserved = False

    def reserve(self) -> str:
        if self.claim_id is None:
            self.claim_id = self.deps.store.reserve_claim_id(self.filed_at.year)
            self.reserved = True
        return self.claim_id

    def log(self, step: PipelineStep, outcome: ProcessingStatus, started: float, error=None):
        self.deps.events.append(
            EventLogEntry(
                ts=self.deps.now(),
                claim_id=self.claim_id,
                task=self.task,
                step=step,
                outcome=outcome,
                duration_ms=round((time.perf_counter() - started) * 1000),
                error_category=error,
            )
        )

    def step[T](self, step: PipelineStep, call: Callable[[], T]) -> T:
        started = time.perf_counter()
        try:
            result = call()
        except Exception as exc:
            status = _status_for(exc)
            self.log(step, status, started, type(exc).__name__)
            raise StepFailed(status, step, type(exc).__name__) from exc
        self.log(step, ProcessingStatus.COMPLETED, started)
        return result

    def privacy_review(self, step: PipelineStep) -> TaskResult:
        """Personal information could not be confirmed removed: minimal record, human review."""
        started = time.perf_counter()
        follow_up = add_business_days(self.filed_at.date(), PRIVACY_REVIEW_DAYS)
        try:
            self.reserve()
            self.deps.store.save(
                ClaimRecord(
                    claim_id=self.claim_id,
                    status=rules.initial_status(None, [], privacy_review=True),
                    filed_at=self.filed_at,
                    assessment=None,
                    teams=[Team.PRIVACY_REVIEW],
                    follow_up_date=follow_up,
                    history=[HistoryEntry(at=self.filed_at, event="PRIVACY_REVIEW_OPENED")],
                )
            )
            path = self.write_status_report(ProcessingStatus.MANUAL_REVIEW_REQUIRED, step, None)
        except OSError as exc:
            return self.fail(StepFailed(ProcessingStatus.FAILED_OUTPUT, step, type(exc).__name__))
        self.log(step, ProcessingStatus.MANUAL_REVIEW_REQUIRED, started)
        return TaskResult(
            processing_status=ProcessingStatus.MANUAL_REVIEW_REQUIRED,
            claim_id=self.claim_id,
            customer_message=(
                f"Your claim number: {self.claim_id}\n"
                "We've received your submission. A specialist will review it by "
                f"{format_follow_up(follow_up)} before processing."
            ),
            report_path=str(path),
        )

    def fail(self, failure: StepFailed) -> TaskResult:
        """No claim record survives a failure; a status-only report records what happened."""
        if self.reserved:
            self.deps.store.release(self.claim_id)
            self.claim_id, self.reserved = None, False
        try:
            path = str(
                self.write_status_report(failure.status, failure.step, failure.error_category)
            )
        except OSError:
            path = None
        return TaskResult(
            processing_status=failure.status,
            claim_id=self.claim_id,
            customer_message=FAILURE_MESSAGES[failure.status],
            report_path=path,
        )

    def write_status_report(self, status, step, error_category) -> Path:
        report = render_status_only_report(
            self.claim_id,
            self.filed_at,
            status,
            failed_step=step,
            error_category=error_category,
            task=TASK_WORDING[self.task],
        )
        return self.deps.reports.write(report, self.claim_id, self.filed_at)


def is_private(*texts: str) -> bool:
    return not any(find_pii(text) for text in texts)


def _ignore_progress(step: int, label: str) -> None:
    pass


def file_claim(
    raw_text: str,
    deps: Deps,
    on_progress: Callable[[int, str], None] = _ignore_progress,
) -> TaskResult:
    run = TaskRun(deps)
    agents = deps.agents
    try:
        submission = run.step(
            PipelineStep.INTAKE,
            lambda: with_model_retries(lambda: intake.scrub(RawSubmission(text=raw_text), agents)),
        )
        on_progress(1, PROGRESS_LABELS[0])
        if submission.requires_manual_review:
            return run.privacy_review(PipelineStep.INTAKE)

        facts: ClaimAssessment = run.step(
            PipelineStep.ASSESSMENT,
            lambda: with_model_retries(lambda: assessment.assess(submission, agents)),
        )
        on_progress(2, PROGRESS_LABELS[1])

        routing: RiskAssessment = run.step(
            PipelineStep.RISK,
            lambda: with_model_retries(
                lambda: risk.evaluate(submission, facts, run.filed_at.date(), agents)
            ),
        )
        on_progress(3, PROGRESS_LABELS[2])

        def compose_reply() -> tuple[CustomerReply, InternalReport]:
            run.reserve()
            return with_model_retries(
                lambda: summary.compose(
                    run.claim_id, run.filed_at, submission, facts, routing, agents
                )
            )

        reply, report = run.step(PipelineStep.SUMMARY, compose_reply)
        on_progress(4, PROGRESS_LABELS[3])

        record = ClaimRecord(
            claim_id=run.claim_id,
            status=rules.initial_status(routing.risk_level, facts.missing_information),
            filed_at=run.filed_at,
            assessment=facts,
            teams=routing.teams,
            follow_up_date=routing.follow_up_date,
            history=[HistoryEntry(at=run.filed_at, event="FILED")],
        )
        private = run.step(
            PipelineStep.PRIVACY_GUARD,
            lambda: is_private(reply.text, report.markdown, record.model_dump_json()),
        )
        if not private:
            return run.privacy_review(PipelineStep.PRIVACY_GUARD)

        def save() -> Path:
            deps.store.save(record)
            return deps.reports.write(report, run.claim_id, run.filed_at)

        path = run.step(PipelineStep.SAVE, save)
    except StepFailed as failure:
        return run.fail(failure)

    return TaskResult(
        processing_status=ProcessingStatus.COMPLETED,
        claim_id=run.claim_id,
        customer_message=reply.text,
        report_path=str(path),
    )
