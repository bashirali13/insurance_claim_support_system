"""US10: each flow returns sanitized trace entries built only from structured contract fields."""

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from claim_intake.contracts import (
    HelpReplyLlmOutput,
    IntakeLlmOutput,
    PiiSuggestion,
    RequestCategory,
    SuggestedPiiType,
    TriState,
    UmUimSubtype,
    UpdateLlmOutput,
)
from claim_intake.existing_claims import get_help, update_claim
from claim_intake.orchestration import file_claim
from claim_intake.reporting import render_trace
from claim_intake.storage import ClaimStore, load_samples
from tests.builders import assessment_output, risk_output, summary_output, triage_output
from tests.conftest import failing_model, structured_model
from tests.integration.conftest import make_deps

S10 = (
    "Yesterday around 6pm a pickup hit me from behind on Main St and drove off. My neck is "
    "sore. Call 555-201-3344. - Jordan Reyes"
)
INTAKE = IntakeLlmOutput(
    suggestions=[PiiSuggestion(text="Jordan Reyes", pii_type=SuggestedPiiType.PERSON)]
)
NO_SUGGESTIONS = IntakeLlmOutput(suggestions=[])
HIT_AND_RUN = assessment_output(
    um_uim_subtype=UmUimSubtype.HIT_AND_RUN,
    customer_side_injured=TriState.YES,
    police_report_mentioned=TriState.UNKNOWN,
)
OPENING = HelpReplyLlmOutput(opening_line="We're sorry for the wait, and we're here to help.")
MODEL_ERROR = ModelHTTPError(503, "deepseek/deepseek-v4-flash-0731", "upstream unavailable")


def steps(result) -> list[str]:
    return [e.step for e in result.trace]


def values(result, step: str) -> dict:
    return next(e.values for e in result.trace if e.step == step)


def file_s10(workdirs, fixed_now):
    model = structured_model(INTAKE, HIT_AND_RUN, risk_output(), summary_output())
    return file_claim(S10, make_deps(workdirs, fixed_now, model))


def update_0005(workdirs, fixed_now, **changes):
    load_samples(workdirs)
    saved = ClaimStore(workdirs).load("CLM-2026-0005").assessment
    facts = assessment_output(
        **{k: getattr(saved, k) for k in type(assessment_output()).model_fields} | changes
    )
    model = structured_model(
        NO_SUGGESTIONS,
        UpdateLlmOutput(updated=facts, contact_change_requested=False),
        risk_output(),
    )
    return update_claim("CLM-2026-0005", "An update.", make_deps(workdirs, fixed_now, model))


def ask_help(workdirs, fixed_now, *categories):
    model = structured_model(NO_SUGGESTIONS, triage_output(categories=list(categories)), OPENING)
    return get_help(None, "Nobody called me back.", make_deps(workdirs, fixed_now, model))


def test_ac_10_1_filing_trace_has_intake_assessment_risk_saved(workdirs, fixed_now):
    result = file_s10(workdirs, fixed_now)

    assert steps(result) == ["intake", "assessment", "risk", "saved"]
    assert values(result, "intake") == {"pii_removed": "PERSON, PHONE", "manual_review": "no"}
    assert values(result, "assessment")["incident"] == "COLLISION"
    assert values(result, "assessment")["coverage_lines"] == "COLLISION, UM_UIM, PIP_MEDPAY"
    assert values(result, "risk")["risk"] == "HIGH"
    assert values(result, "risk")["follow_up_by"] == "2026-09-25"
    assert values(result, "saved")["claim"] == "CLM-2026-0001"


def test_ac_10_2_update_trace_lists_added_corrected_pending_fields(workdirs, fixed_now):
    result = update_0005(
        workdirs,
        fixed_now,
        police_report_mentioned=TriState.YES,
        incident_date="around 7pm",
        customer_side_injured=TriState.NO,
    )

    assert steps(result) == ["intake", "assessment", "risk", "saved"]
    assessed = values(result, "assessment")
    assert assessed["added"] == "police_report_mentioned"
    assert assessed["corrected"] == "incident_date"
    assert assessed["pending"] == "customer_side_injured"
    assert assessed["contact_change"] == "no"


def test_ac_10_2_help_trace_lists_categories_and_teams(workdirs, fixed_now):
    result = ask_help(workdirs, fixed_now, RequestCategory.SERVICE_DELAY)

    assert steps(result) == ["intake", "triage", "routing", "saved"]
    assert values(result, "triage")["categories"] == "SERVICE_DELAY"
    assert values(result, "routing")["teams"] == "CUSTOMER_RELATIONS by 2026-09-28"
    assert values(result, "saved")["reference"] == "HELP-2026-0001"


def test_ac_10_2_redirect_only_help_trace_says_no_team_routed(workdirs, fixed_now):
    result = ask_help(workdirs, fixed_now, RequestCategory.OUT_OF_SCOPE)

    assert values(result, "routing") == {"teams": "no team routed"}


@pytest.mark.parametrize("flow", ["filing", "update", "help"])
def test_ac_10_3_failure_trace_has_failed_step_and_category(flow, workdirs, fixed_now):
    deps = make_deps(workdirs, fixed_now, failing_model(MODEL_ERROR))
    load_samples(workdirs)
    if flow == "filing":
        result = file_claim(S10, deps)
    elif flow == "update":
        result = update_claim("CLM-2026-0005", "It was 7pm.", deps)
    else:
        result = get_help(None, "Nobody called me back.", deps)

    assert result.trace[-1].step == "failed"
    assert result.trace[-1].values == {"step": "INTAKE", "error_category": "ModelHTTPError"}


@pytest.mark.parametrize("flow", ["filing", "update", "help"])
def test_ac_10_4_trace_has_no_narrative_prose_or_personal_values(flow, workdirs, fixed_now):
    if flow == "filing":
        result = file_s10(workdirs, fixed_now)
    elif flow == "update":
        result = update_0005(workdirs, fixed_now, incident_date="around 7pm")
    else:
        result = ask_help(workdirs, fixed_now, RequestCategory.SERVICE_DELAY)

    block = render_trace(result.trace)
    forbidden = [
        "555-201-3344",  # personal value
        "Jordan",
        "pickup",  # narrative words
        "Nobody called",
        "Thank you for telling us",  # model-written opening lines
        "sorry for the wait",
        "Rear-end collision with no injuries",  # model rationale
        "Customer was rear-ended",  # model staff summary
    ]
    for text in forbidden:
        assert text not in block
