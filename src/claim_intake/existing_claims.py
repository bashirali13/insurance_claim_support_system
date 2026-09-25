"""Menu options 2-4 for claims that already exist (specs/002, contracts/agents.md)."""

import time
from collections.abc import Callable
from datetime import date

from claim_intake import rules
from claim_intake.agents import assessment, intake, risk, summary
from claim_intake.contracts import (
    ClaimRecord,
    HelpRecord,
    HistoryEntry,
    MenuTask,
    PendingChange,
    PipelineStep,
    ProcessingStatus,
    RawSubmission,
    TaskResult,
    Team,
    TeamPromise,
)
from claim_intake.dates import add_business_days
from claim_intake.orchestration import (
    PRIVACY_REVIEW_DAYS,
    Deps,
    StepFailed,
    TaskRun,
    ignore_progress,
    is_private,
    with_model_retries,
)
from claim_intake.reporting import (
    HELP_TASK,
    format_follow_up,
    render_help_reply,
    render_help_report,
    render_status,
    render_status_only_report,
    render_update_reply,
    render_update_report,
)
from claim_intake.storage import ClaimStore, HelpStore

UPDATE_PROGRESS_LABELS = (
    "Protecting your personal information",
    "Comparing with your existing claim",
    "Updating your claim",
)
NOTHING_CHANGED = "We didn't find any new or changed details. Nothing was updated."
PENDING_CONFIRMATION_DAYS = 1
CONTACT_CHANGE_DAYS = 3


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
    on_progress: Callable[[int, str], None] = ignore_progress,
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


# --- Option 4: Get help (US8) -------------------------------------------------------------------

HELP_PROGRESS_LABELS = (
    "Protecting your personal information",
    "Understanding your request",
    "Routing to the right team",
)


def _link_claim(store: ClaimStore, claim_id: str, help_id: str, at) -> None:
    """AC-8.6: the linked claim only gains a history entry; nothing else changes."""
    claim = store.load(claim_id)
    entry = HistoryEntry(at=at, event="HELP_REQUESTED", detail=help_id)
    store.save(claim.model_copy(update={"history": [*claim.history, entry]}))


def _help_privacy_review(
    run: TaskRun,
    help_store: HelpStore,
    help_id: str | None,
    claim_id: str | None,
    step: PipelineStep,
) -> TaskResult:
    """AC-8.12: a minimal, text-free help record routed to Privacy Review."""
    started = time.perf_counter()
    follow_up = add_business_days(run.filed_at.date(), PRIVACY_REVIEW_DAYS)
    help_id = help_id or help_store.reserve_help_id(run.filed_at.year)
    record = HelpRecord(
        help_id=help_id,
        claim_id=claim_id,
        filed_at=run.filed_at,
        sentiment=None,
        categories=[],
        routed=[
            TeamPromise(
                team=Team.PRIVACY_REVIEW,
                business_days=PRIVACY_REVIEW_DAYS,
                follow_up_date=follow_up,
            )
        ],
        history=[HistoryEntry(at=run.filed_at, event="HELP_REQUESTED")],
    )
    try:
        help_store.save(record)
        report = render_status_only_report(
            help_id,
            run.filed_at,
            ProcessingStatus.MANUAL_REVIEW_REQUIRED,
            failed_step=step,
            error_category=None,
            task=HELP_TASK,
        )
        path = run.deps.reports.write(report, help_id, run.filed_at)
        if claim_id:
            _link_claim(run.deps.store, claim_id, help_id, run.filed_at)
    except OSError as exc:
        help_store.release(help_id)
        return run.fail(StepFailed(ProcessingStatus.FAILED_OUTPUT, step, type(exc).__name__))
    run.log(step, ProcessingStatus.MANUAL_REVIEW_REQUIRED, started)
    return TaskResult(
        processing_status=ProcessingStatus.MANUAL_REVIEW_REQUIRED,
        claim_id=claim_id,
        customer_message=(
            "We've received your request. A specialist will review it by "
            f"{format_follow_up(follow_up)}.\nReference: {help_id}"
        ),
        report_path=str(path),
    )


def get_help(
    claim_id: str | None,
    raw_text: str,
    deps: Deps,
    on_progress: Callable[[int, str], None] = ignore_progress,
) -> TaskResult:
    """Option 4 (US8). `claim_id` is a verified, existing claim number or None."""
    run = TaskRun(deps, MenuTask.GET_HELP, claim_id=claim_id)
    help_store = HelpStore(deps.store.root)
    agents = deps.agents
    today = run.filed_at.date()
    help_id: str | None = None
    try:
        submission = run.step(
            PipelineStep.INTAKE,
            lambda: with_model_retries(lambda: intake.scrub(RawSubmission(text=raw_text), agents)),
        )
        on_progress(1, HELP_PROGRESS_LABELS[0])
        if submission.requires_manual_review:
            return _help_privacy_review(run, help_store, None, claim_id, PipelineStep.INTAKE)

        triage = run.step(
            PipelineStep.RISK,
            lambda: with_model_retries(lambda: risk.triage(submission, agents)),
        )
        promises = rules.help_routing(triage, submission.text)
        on_progress(2, HELP_PROGRESS_LABELS[1])
        if not promises:  # out of scope or "how do I file": redirect only, nothing saved
            reply = render_help_reply([], triage.categories, opening=None, help_id=None)
            return TaskResult(
                processing_status=ProcessingStatus.COMPLETED,
                claim_id=claim_id,
                customer_message=reply.text,
                report_path=None,
            )

        routed = [
            TeamPromise(
                team=team, business_days=days, follow_up_date=add_business_days(today, days)
            )
            for team, days in promises
        ]

        def compose():
            nonlocal help_id
            help_id = help_store.reserve_help_id(run.filed_at.year)
            run.claim_id = claim_id or help_id  # event log: the claim, else the reference
            opening = with_model_retries(
                lambda: summary.help_opening(submission, agents, triage.categories)
            )
            reply = render_help_reply(
                routed, triage.categories, opening=opening.opening_line, help_id=help_id
            )
            report = render_help_report(
                help_id, run.filed_at, submission, triage, routed, claim_id=claim_id
            )
            return reply, report

        reply, report = run.step(PipelineStep.SUMMARY, compose)
        on_progress(3, HELP_PROGRESS_LABELS[2])

        record = HelpRecord(
            help_id=help_id,
            claim_id=claim_id,
            filed_at=run.filed_at,
            sentiment=triage.sentiment,
            categories=triage.categories,
            routed=routed,
            history=[HistoryEntry(at=run.filed_at, event="HELP_REQUESTED")],
        )
        private = run.step(
            PipelineStep.PRIVACY_GUARD,
            lambda: is_private(reply.text, report.markdown, record.model_dump_json()),
        )
        if not private:
            return _help_privacy_review(
                run, help_store, help_id, claim_id, PipelineStep.PRIVACY_GUARD
            )

        def save():
            help_store.save(record)
            path = deps.reports.write(report, help_id, run.filed_at)
            if claim_id:
                _link_claim(deps.store, claim_id, help_id, run.filed_at)
            return path

        path = run.step(PipelineStep.SAVE, save)
    except StepFailed as failure:
        if help_id:  # AC-8.13: no reference survives a failure
            help_store.release(help_id)
        run.claim_id = claim_id
        return run.fail(failure)

    return TaskResult(
        processing_status=ProcessingStatus.COMPLETED,
        claim_id=claim_id,
        customer_message=reply.text,
        report_path=str(path),
    )
