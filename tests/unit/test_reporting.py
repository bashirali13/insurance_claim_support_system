"""US4: customer reply and internal report templates (contracts/cli.md, contracts/files.md)."""

from datetime import date, datetime

from claim_intake.contracts import (
    IncidentType,
    MissingItem,
    PiiType,
    PipelineStep,
    ProcessingStatus,
    RiskIndicator,
    RiskLevel,
    Team,
    TriState,
)
from claim_intake.reporting import render_reply, render_report, render_status_only_report
from tests.builders import claim_assessment, risk_assessment, sanitized, summary_output

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
