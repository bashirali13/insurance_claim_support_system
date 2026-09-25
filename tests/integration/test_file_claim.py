"""US5: the orchestrator end to end, with every agent answered by a scripted model."""

import json
from datetime import date

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from claim_intake.agents import create_agents
from claim_intake.contracts import (
    ClaimStatus,
    CoverageLine,
    IntakeLlmOutput,
    PiiSuggestion,
    ProcessingStatus,
    SuggestedPiiType,
    Team,
    TriState,
    UmUimSubtype,
)
from claim_intake.orchestration import PROGRESS_LABELS, Deps, file_claim
from claim_intake.storage import ClaimStore, EventLog, ReportWriter
from tests.builders import assessment_output, risk_output, summary_output
from tests.conftest import failing_model, structured_model

# Scenario S10 from docs/customer-scenarios.md.
NARRATIVE = (
    "Yesterday around 6pm I was stopped at a red light on Main St when a pickup hit me from "
    "behind and drove off. My bumper is crushed and my neck is sore. You can reach me at "
    "555-201-3344.\n- Jordan Reyes"
)
PERSONAL_VALUES = ("555-201-3344", "Jordan Reyes")

INTAKE = IntakeLlmOutput(
    suggestions=[PiiSuggestion(text="Jordan Reyes", pii_type=SuggestedPiiType.PERSON)]
)
HIT_AND_RUN = assessment_output(
    um_uim_subtype=UmUimSubtype.HIT_AND_RUN,
    customer_side_injured=TriState.YES,
    police_report_mentioned=TriState.UNKNOWN,
    damage_areas=["bumper"],
    key_facts=["Rear-ended at a red light", "Other driver left the scene", "Neck is sore"],
)
MODEL_ERROR = ModelHTTPError(503, "deepseek/deepseek-v4-flash-0731", "upstream unavailable")


def make_deps(workdirs, fixed_now, model) -> Deps:
    return Deps(
        agents=create_agents(model),
        store=ClaimStore(workdirs),
        reports=ReportWriter(workdirs),
        events=EventLog(workdirs),
        now=lambda: fixed_now,
    )


def happy_model(assessment=HIT_AND_RUN):
    return structured_model(INTAKE, assessment, risk_output(), summary_output())


def all_written_text(workdirs) -> str:
    files = [p for p in workdirs.rglob("*") if p.is_file()]
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def claim_files(workdirs) -> list:
    return list((workdirs / "data" / "claims").glob("*.json"))


def event_lines(workdirs) -> list[dict]:
    log = (workdirs / "logs" / "events.log").read_text(encoding="utf-8")
    return [json.loads(line) for line in log.splitlines()]


def test_ac_5_3_progress_reports_four_steps_in_order(workdirs, fixed_now):
    seen = []

    file_claim(
        NARRATIVE,
        make_deps(workdirs, fixed_now, happy_model()),
        on_progress=lambda n, label: seen.append((n, label)),
    )

    assert seen == [(n, label) for n, label in enumerate(PROGRESS_LABELS, start=1)]


def test_ac_5_4_hit_and_run_with_injury_saves_escalated_record_and_report(workdirs, fixed_now):
    result = file_claim(NARRATIVE, make_deps(workdirs, fixed_now, happy_model()))

    assert result.processing_status == ProcessingStatus.COMPLETED
    assert result.claim_id == "CLM-2026-0001"
    saved = ClaimStore(workdirs).load("CLM-2026-0001")
    assert saved.status == ClaimStatus.ESCALATED
    assert saved.assessment.coverage_lines == [
        CoverageLine.COLLISION,
        CoverageLine.UM_UIM,
        CoverageLine.PIP_MEDPAY,
    ]
    assert saved.follow_up_date == date(2026, 9, 25)
    assert "by Friday, Sep 25" in result.customer_message
    assert result.report_path.endswith("CLM-2026-0001_20260924T101500.md")
    for value in PERSONAL_VALUES:
        assert value not in all_written_text(workdirs)
        assert value not in result.customer_message


def leaky_fact_model():
    return happy_model(HIT_AND_RUN.model_copy(update={"key_facts": ["call me at 555-201-3344"]}))


def test_ac_4_6_pii_in_extracted_fact_blocks_record_report_and_reply(workdirs, fixed_now):
    result = file_claim(NARRATIVE, make_deps(workdirs, fixed_now, leaky_fact_model()))

    assert result.processing_status == ProcessingStatus.MANUAL_REVIEW_REQUIRED
    assert ClaimStore(workdirs).load(result.claim_id).assessment is None
    assert "555-201-3344" not in all_written_text(workdirs)
    assert "555-201-3344" not in result.customer_message


def test_ac_5_8_privacy_review_issues_claim_number_and_minimal_record(workdirs, fixed_now):
    result = file_claim(NARRATIVE, make_deps(workdirs, fixed_now, leaky_fact_model()))

    saved = ClaimStore(workdirs).load(result.claim_id)
    assert saved.status == ClaimStatus.ESCALATED
    assert saved.teams == [Team.PRIVACY_REVIEW]
    assert saved.follow_up_date == date(2026, 9, 29)
    assert f"Your claim number: {result.claim_id}" in result.customer_message
    assert (
        "We've received your submission. A specialist will review it by Tuesday, Sep 29 "
        "before processing." in result.customer_message
    )


def test_ac_5_9_model_http_error_returns_safe_message_and_unfiled_report(workdirs, fixed_now):
    result = file_claim(NARRATIVE, make_deps(workdirs, fixed_now, failing_model(MODEL_ERROR)))

    assert result.processing_status == ProcessingStatus.FAILED_MODEL_ERROR
    assert result.customer_message == (
        "We couldn't finish processing right now. Please try again shortly."
    )
    assert result.claim_id is None
    assert [p.name for p in (workdirs / "output").iterdir()] == ["UNFILED_20260924T101500.md"]
    assert claim_files(workdirs) == []


def test_ac_5_9_invalid_model_output_returns_safe_message_no_record(workdirs, fixed_now):
    invalid_intake = {"suggestions": [{"text": "x", "pii_type": "NOT_A_TYPE"}]}

    result = file_claim(NARRATIVE, make_deps(workdirs, fixed_now, structured_model(invalid_intake)))

    assert result.processing_status == ProcessingStatus.FAILED_VALIDATION
    assert result.customer_message == (
        "We couldn't finish processing right now. Please try again shortly."
    )
    assert claim_files(workdirs) == []


def break_saving(deps: Deps, monkeypatch) -> Deps:
    def refuse(record):
        raise OSError("disk full")

    monkeypatch.setattr(deps.store, "save", refuse)
    return deps


def test_ac_5_10_save_failure_returns_could_not_save_message(workdirs, fixed_now, monkeypatch):
    deps = break_saving(make_deps(workdirs, fixed_now, happy_model()), monkeypatch)

    result = file_claim(NARRATIVE, deps)

    assert result.processing_status == ProcessingStatus.FAILED_OUTPUT
    assert result.customer_message == "We couldn't save your request. Please try again."
    assert claim_files(workdirs) == []


@pytest.mark.parametrize("scenario", ["model_error", "invalid_output", "save_failure", "privacy"])
def test_ac_5_11_failure_messages_contain_no_technical_detail(
    scenario, workdirs, fixed_now, monkeypatch
):
    models = {
        "model_error": failing_model(MODEL_ERROR),
        "invalid_output": structured_model({"suggestions": "not a list"}),
        "save_failure": happy_model(),
        "privacy": leaky_fact_model(),
    }
    deps = make_deps(workdirs, fixed_now, models[scenario])
    if scenario == "save_failure":
        deps = break_saving(deps, monkeypatch)

    message = file_claim(NARRATIVE, deps).customer_message.lower()

    for detail in ("error", "traceback", "exception", "deepseek", "openrouter", "\\", "risk"):
        assert detail not in message
    assert "data/claims" not in message and "output/" not in message


def test_ac_5_13_event_log_has_one_line_per_step(workdirs, fixed_now):
    file_claim(NARRATIVE, make_deps(workdirs, fixed_now, happy_model()))

    assert [line["step"] for line in event_lines(workdirs)] == [
        "INTAKE",
        "ASSESSMENT",
        "RISK",
        "SUMMARY",
        "PRIVACY_GUARD",
        "SAVE",
    ]


def test_ac_5_13_event_log_lines_have_only_allowed_fields(workdirs, fixed_now):
    file_claim(NARRATIVE, make_deps(workdirs, fixed_now, happy_model()))

    for line in event_lines(workdirs):
        assert set(line) == {"ts", "claim_id", "step", "outcome", "duration_ms", "error_category"}


def test_ac_5_13_event_log_contains_no_narrative_words(workdirs, fixed_now):
    file_claim(NARRATIVE, make_deps(workdirs, fixed_now, happy_model()))

    log = (workdirs / "logs" / "events.log").read_text(encoding="utf-8").lower()
    for word in ("pickup", "bumper", "neck", "jordan", "555-201-3344"):
        assert word not in log
