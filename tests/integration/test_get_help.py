"""US8: Get help end to end, with scripted models (scenarios E08-E12)."""

import json

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from claim_intake.agents import create_agents
from claim_intake.contracts import (
    HelpReplyLlmOutput,
    IntakeLlmOutput,
    ProcessingStatus,
    RequestCategory,
    Sentiment,
    Team,
)
from claim_intake.existing_claims import get_help
from claim_intake.orchestration import Deps
from claim_intake.storage import ClaimStore, EventLog, HelpStore, ReportWriter, load_samples
from tests.builders import triage_output
from tests.conftest import failing_model, structured_model

RC = RequestCategory
NO_SUGGESTIONS = IntakeLlmOutput(suggestions=[])
OPENING = HelpReplyLlmOutput(opening_line="We're sorry for the wait, and we're here to help.")
DELAY = "It's been a week and nobody has called me back. I'm really frustrated."


@pytest.fixture
def claims(workdirs):
    load_samples(workdirs)
    return ClaimStore(workdirs)


def run_help(workdirs, fixed_now, text, *answers, claim_id=None, model=None):
    deps = Deps(
        agents=create_agents(model or structured_model(*answers)),
        store=ClaimStore(workdirs),
        reports=ReportWriter(workdirs),
        events=EventLog(workdirs),
        now=lambda: fixed_now,
    )
    return get_help(claim_id, text, deps)


def help_files(workdirs) -> list:
    folder = workdirs / "data" / "help"
    return sorted(folder.glob("*.json")) if folder.exists() else []


def all_text(workdirs) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in workdirs.rglob("*") if p.is_file())


def test_ac_8_1_service_delay_end_to_end_saves_record_report_reference(workdirs, fixed_now):
    triage = triage_output(sentiment=Sentiment.FRUSTRATED, categories=[RC.SERVICE_DELAY])

    result = run_help(workdirs, fixed_now, DELAY, NO_SUGGESTIONS, triage, OPENING)

    assert result.processing_status == ProcessingStatus.COMPLETED
    assert result.customer_message.endswith("Reference: HELP-2026-0001")
    assert "Our Customer Relations team will contact you by Monday, Sep 28." in (
        result.customer_message
    )
    record = HelpStore(workdirs).load("HELP-2026-0001")
    assert [p.team for p in record.routed] == [Team.CUSTOMER_RELATIONS]
    assert result.report_path.endswith("HELP-2026-0001_20260924T101500.md")


def test_ac_8_3_complaint_and_speak_to_adjuster_route_both_teams(workdirs, fixed_now):
    triage = triage_output(categories=[RC.COMPLAINT, RC.SPEAK_TO_ADJUSTER])

    result = run_help(
        workdirs,
        fixed_now,
        "I'm unhappy. Let me talk to my adjuster.",
        NO_SUGGESTIONS,
        triage,
        OPENING,
    )

    assert "A claims adjuster will contact you" in result.customer_message
    assert "Our Customer Relations team will contact you" in result.customer_message


def test_ac_8_4_out_of_scope_writes_no_record_or_reference(workdirs, fixed_now):
    triage = triage_output(categories=[RC.OUT_OF_SCOPE])

    result = run_help(workdirs, fixed_now, "Can I get a rental car?", NO_SUGGESTIONS, triage)

    assert result.customer_message.startswith("I'm sorry, I can only help with claims here.")
    assert "Reference" not in result.customer_message
    assert help_files(workdirs) == []
    assert list((workdirs / "output").iterdir()) == []


def test_ac_8_6_linked_claim_gains_help_history_and_is_otherwise_unchanged(
    workdirs, fixed_now, claims
):
    before = claims.load("CLM-2026-0005")
    triage = triage_output(categories=[RC.CLAIM_QUESTION])

    run_help(
        workdirs,
        fixed_now,
        "When will my adjuster call?",
        NO_SUGGESTIONS,
        triage,
        OPENING,
        claim_id="CLM-2026-0005",
    )

    after = claims.load("CLM-2026-0005")
    assert after.history[-1].event == "HELP_REQUESTED"
    assert after.history[-1].detail == "HELP-2026-0001"
    assert after.model_copy(update={"history": before.history}) == before
    assert HelpStore(workdirs).load("HELP-2026-0001").claim_id == "CLM-2026-0005"


def test_ac_8_7_lawyer_mention_routes_adjuster_next_day_without_naming_special_review(
    workdirs, fixed_now, claims
):
    triage = triage_output(categories=[RC.CLAIM_QUESTION], legal_representation_mentioned=True)

    result = run_help(
        workdirs,
        fixed_now,
        "My lawyer will be contacting you about this claim.",
        NO_SUGGESTIONS,
        triage,
        OPENING,
        claim_id="CLM-2026-0005",
    )

    assert "A claims adjuster will contact you by Friday, Sep 25." in result.customer_message
    assert "special" not in result.customer_message.lower()
    teams = [p.team for p in HelpStore(workdirs).load("HELP-2026-0001").routed]
    assert Team.SPECIAL_REVIEW in teams


def test_ac_8_9_no_personal_values_anywhere_and_event_lines_have_help_task(workdirs, fixed_now):
    triage = triage_output(sentiment=Sentiment.FRUSTRATED, categories=[RC.SERVICE_DELAY])
    text = f"{DELAY} Call me at 555-201-3344."

    result = run_help(workdirs, fixed_now, text, NO_SUGGESTIONS, triage, OPENING)

    assert "555-201-3344" not in all_text(workdirs)
    assert "555-201-3344" not in result.customer_message
    log = (workdirs / "logs" / "events.log").read_text(encoding="utf-8").splitlines()
    assert {json.loads(line)["task"] for line in log} == {"GET_HELP"}


def test_ac_8_12_residual_pii_opens_minimal_privacy_help_record(workdirs, fixed_now):
    # Given the triage model leaks a phone number into its rationale (which goes in the report)
    leaky_triage = triage_output(
        categories=[RC.SERVICE_DELAY], rationale="Callback to 555-201-3344 was missed."
    )

    # When the request is processed, the final privacy guard catches it
    result = run_help(workdirs, fixed_now, DELAY, NO_SUGGESTIONS, leaky_triage, OPENING)

    assert result.processing_status == ProcessingStatus.MANUAL_REVIEW_REQUIRED
    assert result.customer_message == (
        "We've received your request. A specialist will review it by Tuesday, Sep 29.\n"
        "Reference: HELP-2026-0001"
    )
    record = HelpStore(workdirs).load("HELP-2026-0001")
    assert record.sentiment is None and record.categories == []
    assert [(p.team, p.business_days) for p in record.routed] == [(Team.PRIVACY_REVIEW, 3)]
    assert "555-201-3344" not in all_text(workdirs)


def test_ac_8_13_model_failure_creates_no_record_and_leaves_claim_unchanged(
    workdirs, fixed_now, claims
):
    before = (claims.dir / "CLM-2026-0005.json").read_bytes()
    error = ModelHTTPError(503, "deepseek/deepseek-v4-flash-0731", "upstream unavailable")

    result = run_help(
        workdirs, fixed_now, DELAY, claim_id="CLM-2026-0005", model=failing_model(error)
    )

    assert result.customer_message == (
        "We couldn't finish processing right now. Please try again shortly."
    )
    assert help_files(workdirs) == []
    assert (claims.dir / "CLM-2026-0005.json").read_bytes() == before
    reports = list((workdirs / "output").iterdir())
    assert len(reports) == 1
    assert "- **Task:** Get help with my claim" in reports[0].read_text(encoding="utf-8")
