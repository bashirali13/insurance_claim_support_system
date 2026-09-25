"""US4: customer reply and internal report templates (contracts/cli.md, contracts/files.md)."""

from datetime import date, datetime

from claim_intake.contracts import (
    IncidentType,
    MissingItem,
    PiiType,
    PipelineStep,
    ProcessingStatus,
    RequestCategory,
    RiskIndicator,
    RiskLevel,
    Team,
    TeamPromise,
    TriState,
)
from claim_intake.reporting import (
    render_help_reply,
    render_help_report,
    render_reply,
    render_report,
    render_status_only_report,
    render_update_reply,
    render_update_report,
)
from claim_intake.rules import diff_facts
from tests.builders import (
    assessment_output,
    claim_assessment,
    risk_assessment,
    sanitized,
    summary_output,
    triage_output,
)

CLAIM_ID = "CLM-2026-0007"
FILED_AT = datetime(2026, 9, 24, 10, 15)


def reply_text(assessment=None, risk=None, summary=None) -> str:
    return render_reply(
        CLAIM_ID,
        summary or summary_output(),
        assessment or claim_assessment(),
        risk or risk_assessment(),
    ).text


def test_ac_4_1_reply_sections_in_order_with_claim_number_and_dated_next_step():
    injured = claim_assessment(customer_side_injured=TriState.YES)
    text = reply_text(
        assessment=injured,
        risk=risk_assessment(follow_up_business_days=1, follow_up_date=date(2026, 9, 25)),
    )

    assert f"Your claim number: {CLAIM_ID}" in text
    assert "A claims adjuster will contact you by Friday, Sep 25." in text
    order = [
        "Your claim number",
        "Here's what we recorded:",
        "What happens next:",
        "What we still need from you:",
    ]
    positions = [text.index(heading) for heading in order]
    assert positions == sorted(positions)
    assert "  • Police report number" in text


def test_ac_4_1_still_needed_section_omitted_when_nothing_missing():
    text = reply_text(assessment=claim_assessment())

    assert "What we still need from you" not in text
    assert "option 3" not in text


def test_ac_4_1_mixed_claim_reply_says_adjuster_will_separate():
    text = reply_text(assessment=claim_assessment(incident_type=IncidentType.MIXED))

    assert "You described more than one incident. An adjuster will help separate them." in text


def test_ac_4_1_mixed_claim_reply_never_asks_to_refile():
    text = reply_text(assessment=claim_assessment(incident_type=IncidentType.MIXED)).lower()

    assert not ("file" in text and "separately" in text)


def test_ac_4_2_injury_adds_care_and_medical_guidance_line():
    text = reply_text(assessment=claim_assessment(others_injured=TriState.YES))

    assert "We're sorry to hear someone was hurt." in text
    assert "please seek medical care right away" in text


def test_ac_4_2_no_medical_line_without_injury():
    text = reply_text(assessment=claim_assessment())

    assert "medical care" not in text


def test_ac_4_3_reply_never_mentions_special_review_or_risk():
    risky = risk_assessment(
        indicators=[RiskIndicator.POSSIBLE_PROMPT_INJECTION],
        risk_level=RiskLevel.HIGH,
        teams=[Team.CLAIMS_ADJUSTER, Team.SPECIAL_REVIEW],
    )

    text = reply_text(risk=risky)

    for hidden in ("Special Review", "SPECIAL_REVIEW", "risk", "HIGH", "INJECTION"):
        assert hidden.lower() not in text.lower()


def test_ac_4_3_reply_names_customer_relations_when_routed_there():
    text = reply_text(risk=risk_assessment(teams=[Team.CLAIMS_ADJUSTER, Team.CUSTOMER_RELATIONS]))

    assert "Our Customer Relations team will contact you by Monday, Sep 28." in text


REPORT_SECTIONS = [
    f"# Claim Intake Report — {CLAIM_ID}",
    "## Summary",
    "## Incident",
    "## Facts",
    "## Coverage Lines to Review",
    "## Missing Information",
    "## Contradictions",
    "## Sentiment and Risk",
    "## Routing and Follow-up",
    "## Privacy",
    "> Supports intake and triage only. Not a coverage, fault, or claim decision.",
]


def test_ac_4_5_report_has_all_sections_in_order_and_decision_notice():
    report = render_report(
        CLAIM_ID,
        FILED_AT,
        summary_output(),
        sanitized(),
        claim_assessment(),
        risk_assessment(),
        pii_types_removed=[PiiType.PHONE, PiiType.PERSON],
    ).markdown

    positions = [report.index(section) for section in REPORT_SECTIONS]
    assert positions == sorted(positions)
    assert "- **Processing status:** COMPLETED" in report
    assert "PHONE, PERSON" in report


def test_ac_4_5_empty_lists_render_none_recorded():
    report = render_report(
        CLAIM_ID,
        FILED_AT,
        summary_output(),
        sanitized(),
        claim_assessment(),
        risk_assessment(),
        pii_types_removed=[],
    ).markdown

    contradictions = report.split("## Contradictions")[1].split("##")[0]
    assert "None recorded." in contradictions


def test_ac_5_8_status_only_report_contains_no_narrative_or_facts():
    report = render_status_only_report(
        CLAIM_ID,
        FILED_AT,
        ProcessingStatus.MANUAL_REVIEW_REQUIRED,
        failed_step=PipelineStep.INTAKE,
        error_category=None,
    ).markdown

    assert "- **Processing status:** MANUAL_REVIEW_REQUIRED" in report
    assert "- **Failed step:** INTAKE" in report
    assert "## Summary" not in report
    assert "## Facts" not in report
    assert REPORT_SECTIONS[-1] in report
    assert MissingItem.POLICE_REPORT not in report


# --- US7: update reply and report ---------------------------------------------------------------

UPDATE_SAVED = assessment_output(
    incident_date="yesterday around 6pm",
    customer_side_injured=TriState.YES,
    police_report_mentioned=TriState.UNKNOWN,
)
FRIDAY, TUESDAY = date(2026, 9, 25), date(2026, 9, 29)


def update_text(changes, *, contact=False, missing=(), teams=(Team.CLAIMS_ADJUSTER,)) -> str:
    return render_update_reply(
        CLAIM_ID,
        changes,
        contact_change_requested=contact,
        teams=list(teams),
        routing_date=FRIDAY,
        pending_date=FRIDAY,
        contact_date=TUESDAY,
        missing=list(missing),
    ).text


def test_ac_7_1_update_reply_lists_added_items_in_customer_wording():
    changes = diff_facts(
        UPDATE_SAVED, UPDATE_SAVED.model_copy(update={"police_report_mentioned": TriState.YES})
    )

    text = update_text(changes)

    assert text.startswith(f"Thanks, your claim {CLAIM_ID} is updated.")
    assert "  • Added: police report" in text
    assert "  • A claims adjuster will contact you by Friday, Sep 25." in text


def test_ac_7_2_update_reply_shows_old_to_new_for_corrections():
    changes = diff_facts(
        UPDATE_SAVED, UPDATE_SAVED.model_copy(update={"incident_date": "around 7pm"})
    )

    assert "  • Corrected: when it happened (yesterday around 6pm → around 7pm)" in update_text(
        changes
    )


def test_ac_7_3_update_reply_contact_change_line_with_three_day_date():
    text = update_text(diff_facts(UPDATE_SAVED, UPDATE_SAVED), contact=True)

    assert (
        "  • Our Policy Services team will confirm your new contact details with you by "
        "Tuesday, Sep 29.\n    We didn't store them here."
    ) in text


def test_ac_7_4_update_reply_pending_line_names_field_and_one_day_date():
    changes = diff_facts(
        UPDATE_SAVED, UPDATE_SAVED.model_copy(update={"customer_side_injured": TriState.NO})
    )

    assert (
        "  • An adjuster will confirm this change with you by Friday, Sep 25:\n"
        "    injuries to you or your passengers"
    ) in update_text(changes)


def test_ac_7_8_update_report_sections_and_notice():
    changes = diff_facts(
        UPDATE_SAVED, UPDATE_SAVED.model_copy(update={"police_report_mentioned": TriState.YES})
    )

    report = render_update_report(
        CLAIM_ID,
        FILED_AT,
        changes,
        contact_change_requested=False,
        submission=sanitized("The police report number is 26-44817."),
        assessment=claim_assessment(),
        risk=risk_assessment(),
        teams=[Team.CLAIMS_ADJUSTER],
        follow_up_date=FRIDAY,
    ).markdown

    sections = [
        "- **Task:** Add or correct details",
        "## Added",
        "## Corrected",
        "## Pending Adjuster Confirmation",
        "## Contact Change",
        "## Missing Information",
        "## Sentiment and Risk",
        "## Routing and Follow-up",
        "## Privacy",
        REPORT_SECTIONS[-1],
    ]
    positions = [report.index(s) for s in sections]
    assert positions == sorted(positions)
    assert "police report" in report.split("## Added")[1].split("##")[0]


def test_ac_7_9_status_only_report_names_update_task():
    report = render_status_only_report(
        CLAIM_ID,
        FILED_AT,
        ProcessingStatus.FAILED_MODEL_ERROR,
        failed_step=PipelineStep.ASSESSMENT,
        error_category="ModelHTTPError",
        task="Add or correct details",
    ).markdown

    assert "- **Task:** Add or correct details" in report


# --- US8: help reply and report -------------------------------------------------------------

MONDAY = date(2026, 9, 28)
OPENING = "We're sorry for the wait, and we're here to help."


def promise(team: Team, days: int = 2, day: date = MONDAY) -> TeamPromise:
    return TeamPromise(team=team, business_days=days, follow_up_date=day)


def help_text(routed, categories, help_id="HELP-2026-0001", opening=OPENING) -> str:
    return render_help_reply(routed, categories, opening=opening, help_id=help_id).text


def test_ac_8_1_help_reply_lists_team_dates_and_reference():
    text = help_text(
        [promise(Team.CLAIMS_ADJUSTER), promise(Team.CUSTOMER_RELATIONS)],
        [RequestCategory.SERVICE_DELAY, RequestCategory.SPEAK_TO_ADJUSTER],
    )

    assert text == (
        f"{OPENING}\n"
        "  • A claims adjuster will contact you by Monday, Sep 28.\n"
        "  • Our Customer Relations team will contact you by Monday, Sep 28.\n"
        "Reference: HELP-2026-0001"
    )


def test_ac_8_4_redirect_only_reply_has_no_reference():
    text = help_text([], [RequestCategory.OUT_OF_SCOPE], help_id=None, opening=None)

    assert text == (
        "I'm sorry, I can only help with claims here. For billing, policy changes, rentals, "
        "or roadside help, please call Northstar Auto Insurance at the number on your "
        "insurance card."
    )


def test_ac_8_5_file_a_claim_line_points_to_option_1():
    text = help_text([], [RequestCategory.FILE_A_CLAIM], help_id=None, opening=None)

    assert text == "To file a new claim, choose option 1 from the menu."


def test_ac_8_7_help_reply_never_mentions_special_review():
    text = help_text(
        [promise(Team.CLAIMS_ADJUSTER, 1), promise(Team.SPECIAL_REVIEW, 1)],
        [RequestCategory.CLAIM_QUESTION],
    )

    assert "special" not in text.lower()


def test_ac_8_8_distressed_out_of_scope_reply_has_redirect_and_team():
    text = help_text([promise(Team.CUSTOMER_RELATIONS)], [RequestCategory.OUT_OF_SCOPE])

    assert "Our Customer Relations team will contact you by Monday, Sep 28." in text
    assert "I'm sorry, I can only help with claims here." in text
    assert text.endswith("Reference: HELP-2026-0001")


def test_ac_8_9_help_report_sections_and_notice():
    report = render_help_report(
        "HELP-2026-0001",
        FILED_AT,
        sanitized("Nobody has called me back."),
        triage_output(categories=[RequestCategory.SERVICE_DELAY]),
        [promise(Team.CUSTOMER_RELATIONS)],
        claim_id="CLM-2026-0005",
    ).markdown

    sections = [
        "# Claim Intake Report — HELP-2026-0001",
        "- **Task:** Get help with my claim",
        "- **Claim:** CLM-2026-0005",
        "## Request",
        "## Categories",
        "## Sentiment",
        "## Routing and Follow-up",
        "## Privacy",
        REPORT_SECTIONS[-1],
    ]
    positions = [report.index(s) for s in sections]
    assert positions == sorted(positions)
