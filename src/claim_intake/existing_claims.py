"""Menu options 2-4 for claims that already exist (specs/002, contracts/agents.md)."""

from collections.abc import Callable
from datetime import date

from claim_intake import rules
from claim_intake.agents import assessment, intake, risk
from claim_intake.contracts import (
    ClaimRecord,
    HistoryEntry,
    MenuTask,
    PendingChange,
    PipelineStep,
    ProcessingStatus,
    RawSubmission,
    TaskResult,
    Team,
)
from claim_intake.dates import add_business_days
from claim_intake.orchestration import (
    PRIVACY_REVIEW_DAYS,
    Deps,
    StepFailed,
    TaskRun,
    is_private,
    with_model_retries,
)
from claim_intake.reporting import (
    format_follow_up,
    render_status,
    render_update_reply,
    render_update_report,
)
from claim_intake.storage import ClaimStore

UPDATE_PROGRESS_LABELS = (
    "Protecting your personal information",
    "Comparing with your existing claim",
    "Updating your claim",
)
NOTHING_CHANGED = "We didn't find any new or changed details. Nothing was updated."
PENDING_CONFIRMATION_DAYS = 1
CONTACT_CHANGE_DAYS = 3


def _ignore_progress(step: int, label: str) -> None:
    pass


def check_status(claim_id: str, store: ClaimStore, today: date) -> str:
    """Option 2: rendered from the saved record only. No model call, no writes (AC-6.8)."""
    return render_status(store.load(claim_id), today)


def _update_privacy_review(run: TaskRun, record: ClaimRecord, step: PipelineStep) -> TaskResult:
    """AC-7.10: the update is NOT applied; Privacy Review joins the claim's existing teams."""
    follow_up = add_business_days(run.filed_at.date(), PRIVACY_REVIEW_DAYS)
    teams = [*record.teams, *([] if Team.PRIVACY_REVIEW in record.teams else [Team.PRIVACY_REVIEW])]
    reviewed = record.model_copy(
        update={
            "teams": teams,
            "follow_up_date": follow_up,
            "history": [
                *record.history,
                HistoryEntry(at=run.filed_at, event="PRIVACY_REVIEW_OPENED"),
            ],
        }
    )
    try:
        run.deps.store.save(reviewed)
        path = run.write_status_report(ProcessingStatus.MANUAL_REVIEW_REQUIRED, step, None)
    except OSError as exc:
        return run.fail(StepFailed(ProcessingStatus.FAILED_OUTPUT, step, type(exc).__name__))
    return TaskResult(
        processing_status=ProcessingStatus.MANUAL_REVIEW_REQUIRED,
        claim_id=record.claim_id,
        customer_message=(
            "We've received your update. A specialist will review it by "
            f"{format_follow_up(follow_up)} before it's added to your claim."
        ),
        report_path=str(path),
    )


def update_claim(
    claim_id: str,
    raw_text: str,
    deps: Deps,
    on_progress: Callable[[int, str], None] = _ignore_progress,
) -> TaskResult:
    """Option 3 (US7). The caller has already refused closed and privacy-review claims."""
    run = TaskRun(deps, MenuTask.UPDATE_DETAILS, claim_id=claim_id)
    record = deps.store.load(claim_id)
    agents = deps.agents
    today = run.filed_at.date()
    try:
        submission = run.step(
            PipelineStep.INTAKE,
            lambda: with_model_retries(lambda: intake.scrub(RawSubmission(text=raw_text), agents)),
        )
        on_progress(1, UPDATE_PROGRESS_LABELS[0])
        if submission.requires_manual_review:
            return _update_privacy_review(run, record, PipelineStep.INTAKE)

        proposed = run.step(
            PipelineStep.ASSESSMENT,
            lambda: with_model_retries(
                lambda: assessment.update(submission, record.assessment, agents)
            ),
        )
        changes = rules.diff_facts(record.assessment, proposed.updated)
        contact = proposed.contact_change_requested
        on_progress(2, UPDATE_PROGRESS_LABELS[1])
        if changes.is_empty and not contact:
            return TaskResult(
                processing_status=ProcessingStatus.COMPLETED,
                claim_id=claim_id,
                customer_message=NOTHING_CHANGED,
                report_path=None,
            )

        facts = assessment.complete(changes.applied)
        routing = run.step(
            PipelineStep.RISK,
            lambda: with_model_retries(lambda: risk.evaluate(submission, facts, today, agents)),
        )

        # FR-208 to FR-210: teams and date are replaced by the latest result.
        teams = [*routing.teams, *([Team.POLICY_SERVICES] if contact else [])]
        promises = [routing.follow_up_business_days]
        promises += [PENDING_CONFIRMATION_DAYS] if changes.sensitive else []
        promises += [CONTACT_CHANGE_DAYS] if contact else []
        pending = [
            PendingChange(
                field=c.field, requested_value=c.new or "UNKNOWN", requested_at=run.filed_at
            )
            for c in changes.sensitive
        ]
        changed_fields = [c.field for c in [*changes.added, *changes.corrected, *changes.sensitive]]
        updated = ClaimRecord(
            claim_id=claim_id,
            status=rules.status_after_update(
                record.status, routing.risk_level, facts.missing_information
            ),
            filed_at=record.filed_at,
            assessment=facts,
            teams=teams,
            follow_up_date=rules.earliest_follow_up(today, promises),
            history=[
                *record.history,
                HistoryEntry(
                    at=run.filed_at,
                    event="DETAILS_UPDATED",
                    detail=", ".join(changed_fields) or None,
                ),
            ],
            pending_changes=[*record.pending_changes, *pending],
        )

        def render():
            reply = render_update_reply(
                claim_id,
                changes,
                contact_change_requested=contact,
                teams=routing.teams,
                routing_date=routing.follow_up_date,
                pending_date=add_business_days(today, PENDING_CONFIRMATION_DAYS),
                contact_date=add_business_days(today, CONTACT_CHANGE_DAYS),
                missing=facts.missing_information,
            )
            report = render_update_report(
                claim_id,
                run.filed_at,
                changes,
                contact_change_requested=contact,
                submission=submission,
                assessment=facts,
                risk=routing,
                teams=teams,
                follow_up_date=updated.follow_up_date,
            )
            return reply, report

        reply, report = run.step(PipelineStep.SUMMARY, render)
        on_progress(3, UPDATE_PROGRESS_LABELS[2])

        private = run.step(
            PipelineStep.PRIVACY_GUARD,
            lambda: is_private(reply.text, report.markdown, updated.model_dump_json()),
        )
        if not private:
            return _update_privacy_review(run, record, PipelineStep.PRIVACY_GUARD)

        def save():
            deps.store.save(updated)
            return deps.reports.write(report, claim_id, run.filed_at)

        path = run.step(PipelineStep.SAVE, save)
    except StepFailed as failure:
        return run.fail(failure)

    return TaskResult(
        processing_status=ProcessingStatus.COMPLETED,
        claim_id=claim_id,
        customer_message=reply.text,
        report_path=str(path),
    )
