"""US7: adding or correcting details on sample claim CLM-2026-0005 (scenarios E04-E07)."""

import json
from datetime import date

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from claim_intake.agents import create_agents
from claim_intake.contracts import (
    AssessmentLlmOutput,
    ClaimStatus,
    IntakeLlmOutput,
    MissingItem,
    ProcessingStatus,
    Team,
    TriState,
    UpdateLlmOutput,
)
from claim_intake.existing_claims import check_status, update_claim
from claim_intake.orchestration import Deps
from claim_intake.storage import ClaimStore, EventLog, ReportWriter, load_samples
from tests.builders import risk_output
from tests.conftest import failing_model, structured_model

CLAIM = "CLM-2026-0005"
NO_SUGGESTIONS = IntakeLlmOutput(suggestions=[])


@pytest.fixture
def store(workdirs):
    load_samples(workdirs)
    return ClaimStore(workdirs)


def saved_facts(store, **changes) -> AssessmentLlmOutput:
    """The saved 0005 facts as the update model would return them, with `changes` applied."""
    saved = store.load(CLAIM).assessment
    facts = AssessmentLlmOutput(**saved.model_dump(include=set(AssessmentLlmOutput.model_fields)))
    return facts.model_copy(update=changes)


def run_update(workdirs, fixed_now, text, *answers, model=None):
    deps = Deps(
        agents=create_agents(model or structured_model(*answers)),
        store=ClaimStore(workdirs),
        reports=ReportWriter(workdirs),
        events=EventLog(workdirs),
        now=lambda: fixed_now,
    )
    return update_claim(CLAIM, text, deps)


def answers(store, contact=False, **changes):
    update = UpdateLlmOutput(
        updated=saved_facts(store, **changes), contact_change_requested=contact
    )
    return NO_SUGGESTIONS, update, risk_output()


def all_text(workdirs) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in workdirs.rglob("*") if p.is_file())


def test_ac_7_1_police_report_added_updates_record_missing_list_and_history(
    workdirs, fixed_now, store
):
    result = run_update(
        workdirs,
        fixed_now,
        "The police report number is 26-44817.",
        *answers(store, police_report_mentioned=TriState.YES),
    )

    saved = store.load(CLAIM)
    assert result.processing_status == ProcessingStatus.COMPLETED
    assert "  • Added: police report" in result.customer_message
    assert MissingItem.POLICE_REPORT not in saved.assessment.missing_information
    assert saved.history[-1].event == "DETAILS_UPDATED"
    assert saved.history[-1].detail == "police_report_mentioned"


def test_ac_7_2_time_correction_is_saved(workdirs, fixed_now, store):
    result = run_update(
        workdirs,
        fixed_now,
        "It was actually around 7pm, not 6pm.",
        *answers(store, incident_date="around 7pm"),
    )

    assert "when it happened (yesterday around 6pm → around 7pm)" in result.customer_message
    assert store.load(CLAIM).assessment.incident_date == "around 7pm"


def test_ac_7_3_contact_change_routes_policy_services_and_stores_no_value(
    workdirs, fixed_now, store
):
    result = run_update(
        workdirs, fixed_now, "My new phone number is 555-908-1200.", *answers(store, contact=True)
    )

    saved = store.load(CLAIM)
    assert Team.POLICY_SERVICES in saved.teams
    assert "Policy Services team will confirm your new contact details" in result.customer_message
    assert "by Tuesday, Sep 29" in result.customer_message
    assert "555-908-1200" not in all_text(workdirs)
    assert "555-908-1200" not in result.customer_message


def test_ac_7_4_sensitive_correction_is_pending_and_original_kept(workdirs, fixed_now, store):
    result = run_update(
        workdirs,
        fixed_now,
        "Actually nobody was hurt.",
        *answers(store, customer_side_injured=TriState.NO),
    )

    saved = store.load(CLAIM)
    assert saved.assessment.customer_side_injured == TriState.YES
    assert [(p.field, p.requested_value) for p in saved.pending_changes] == [
        ("customer_side_injured", "NO")
    ]
    assert "An adjuster will confirm this change with you by Friday, Sep 25" in (
        result.customer_message
    )
    status = check_status(CLAIM, store, fixed_now.date())
    assert "Waiting for an adjuster to confirm:\n    • injuries to you or your passengers" in status


def test_ac_7_5_routing_recomputed_teams_replaced_escalation_kept(workdirs, fixed_now, store):
    before = store.load(CLAIM)
    store.save(before.model_copy(update={"teams": [Team.CLAIMS_ADJUSTER, Team.CUSTOMER_RELATIONS]}))

    run_update(
        workdirs,
        fixed_now,
        "The police report number is 26-44817.",
        *answers(store, police_report_mentioned=TriState.YES),
    )

    saved = store.load(CLAIM)
    assert saved.teams == [Team.CLAIMS_ADJUSTER]  # replaced: a calm update drops Customer Relations
    assert saved.status == ClaimStatus.ESCALATED  # never de-escalates
    assert saved.follow_up_date == date(2026, 9, 25)  # injury on file → 1 business day


def test_ac_7_6_no_change_update_writes_nothing(workdirs, fixed_now, store):
    before = (store.dir / f"{CLAIM}.json").read_bytes()

    result = run_update(workdirs, fixed_now, "Just checking in.", *answers(store))

    assert result.customer_message == (
        "We didn't find any new or changed details. Nothing was updated."
    )
    assert (store.dir / f"{CLAIM}.json").read_bytes() == before
    assert list((workdirs / "output").iterdir()) == []


def test_ac_7_8_update_writes_report_and_event_lines_with_update_task(workdirs, fixed_now, store):
    result = run_update(
        workdirs,
        fixed_now,
        "The police report number is 26-44817.",
        *answers(store, police_report_mentioned=TriState.YES),
    )

    assert result.report_path.endswith(f"{CLAIM}_20260924T101500.md")
    report = (workdirs / "output" / f"{CLAIM}_20260924T101500.md").read_text(encoding="utf-8")
    assert "- **Task:** Add or correct details" in report
    log = (workdirs / "logs" / "events.log").read_text(encoding="utf-8").splitlines()
    assert {json.loads(line)["task"] for line in log} == {"UPDATE_DETAILS"}


def test_ac_7_9_model_failure_leaves_claim_unchanged_with_safe_message(workdirs, fixed_now, store):
    before = (store.dir / f"{CLAIM}.json").read_bytes()
    error = ModelHTTPError(503, "deepseek/deepseek-v4-flash-0731", "upstream unavailable")

    result = run_update(workdirs, fixed_now, "It was 7pm.", model=failing_model(error))

    assert result.processing_status == ProcessingStatus.FAILED_MODEL_ERROR
    assert result.customer_message == (
        "We couldn't finish processing right now. Please try again shortly."
    )
    assert (store.dir / f"{CLAIM}.json").read_bytes() == before  # never deleted or changed
    reports = list((workdirs / "output").iterdir())
    assert len(reports) == 1
    assert "- **Task:** Add or correct details" in reports[0].read_text(encoding="utf-8")


def test_ac_7_10_residual_pii_opens_privacy_review_without_applying_update(
    workdirs, fixed_now, store
):
    leaky = answers(
        store, police_report_mentioned=TriState.YES, key_facts=["call me at 555-201-3344"]
    )

    result = run_update(workdirs, fixed_now, "Police report 26-44817.", *leaky)

    saved = store.load(CLAIM)
    assert result.processing_status == ProcessingStatus.MANUAL_REVIEW_REQUIRED
    assert result.customer_message == (
        "We've received your update. A specialist will review it by Tuesday, Sep 29 "
        "before it's added to your claim."
    )
    assert saved.assessment.police_report_mentioned == TriState.UNKNOWN  # update not applied
    assert saved.teams == [Team.CLAIMS_ADJUSTER, Team.PRIVACY_REVIEW]
    assert saved.follow_up_date == date(2026, 9, 29)
    assert saved.history[-1].event == "PRIVACY_REVIEW_OPENED"
    assert "555-201-3344" not in all_text(workdirs)
