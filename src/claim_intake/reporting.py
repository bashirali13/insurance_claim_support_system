"""Customer reply and internal report templates (contracts/cli.md, contracts/files.md).

The model supplies only the opening line, recorded points, and staff summary. Everything else,
including every date, team, and missing item, is rendered here from the structured contracts.
"""

from datetime import date, datetime

from claim_intake.contracts import (
    ClaimAssessment,
    CustomerReply,
    IncidentType,
    InternalReport,
    MissingItem,
    PiiType,
    PipelineStep,
    ProcessingStatus,
    RiskAssessment,
    SanitizedSubmission,
    SummaryLlmOutput,
    Team,
    TriState,
)

RULE = "-" * 50
DECISION_NOTICE = "> Supports intake and triage only. Not a coverage, fault, or claim decision."
NONE_RECORDED = "None recorded."

MISSING_WORDING = {
    MissingItem.WHAT_HAPPENED: "A short description of what happened",
    MissingItem.INCIDENT_DATE: "When it happened (date and approximate time)",
    MissingItem.LOCATION: "Where it happened",
    MissingItem.DAMAGE_DESCRIPTION: "A description of the damage",
    MissingItem.OTHER_PARTY_INVOLVEMENT: "Whether another vehicle or person was involved",
    MissingItem.POLICE_REPORT: "Police report number",
}

# Teams the customer is told about. Special Review is internal and never named (AC-4.3).
TEAM_ROLE = {
    Team.CLAIMS_ADJUSTER: "A claims adjuster",
    Team.CUSTOMER_RELATIONS: "Our Customer Relations team",
}


def format_follow_up(day: date) -> str:
    """e.g. 'Friday, Sep 25'."""
    return f"{day:%A}, {day:%b} {day.day}"


def _bullets(items: list[str]) -> list[str]:
    return [f"  • {item}" for item in items]


def render_reply(
    claim_id: str,
    summary: SummaryLlmOutput,
    assessment: ClaimAssessment,
    risk: RiskAssessment,
) -> CustomerReply:
    injured = assessment.injury_present == TriState.YES
    by = format_follow_up(risk.follow_up_date)

    next_steps = [f"{TEAM_ROLE[t]} will contact you by {by}." for t in risk.teams if t in TEAM_ROLE]
    if injured:
        next_steps.append("If anyone's symptoms get worse, please seek medical care right away.")
    if assessment.incident_type == IncidentType.MIXED:
        next_steps.append(
            "You described more than one incident. An adjuster will help separate them."
        )

    lines = [RULE, f" Your claim number: {claim_id}", RULE, summary.opening_line]
    if injured:
        lines.append("We're sorry to hear someone was hurt.")
    lines += ["", "Here's what we recorded:", *_bullets(summary.recorded_points)]
    lines += ["", "What happens next:", *_bullets(next_steps)]
    if assessment.missing_information:
        needed = [MISSING_WORDING[item] for item in assessment.missing_information]
        lines += ["", "What we still need from you:", *_bullets(needed)]
        lines += ["", "Choose option 3 anytime to add these details."]
    lines.append(RULE)
    return CustomerReply(text="\n".join(lines))


def _list_section(title: str, items: list[str]) -> list[str]:
    return ["", f"## {title}", *([f"- {i}" for i in items] or [NONE_RECORDED])]


def _header(claim_id: str | None, filed_at: datetime, status: ProcessingStatus) -> list[str]:
    return [
        f"# Claim Intake Report — {claim_id or 'UNFILED'}",
        f"- **Processing status:** {status}",
        "- **Task:** File a new claim",
        f"- **Filed:** {filed_at:%Y-%m-%d %H:%M}",
    ]


def render_report(
    claim_id: str,
    filed_at: datetime,
    summary: SummaryLlmOutput,
    submission: SanitizedSubmission,
    assessment: ClaimAssessment,
    risk: RiskAssessment,
    pii_types_removed: list[PiiType],
) -> InternalReport:
    a = assessment
    lines = _header(claim_id, filed_at, ProcessingStatus.COMPLETED)
    lines += ["", "## Summary", summary.narrative_summary]
    lines += [
        "",
        "## Incident",
        f"- **Type:** {a.incident_type}",
        f"- **UM/UIM sub-type:** {a.um_uim_subtype or NONE_RECORDED}",
        f"- **When:** {a.incident_date or NONE_RECORDED}",
        f"- **Where:** {a.location or NONE_RECORDED}",
        "- **Customer's words (protected):**",
        *[f"  > {line}" for line in submission.text.splitlines()],
    ]
    lines += [
        "",
        "## Facts",
        f"- **Damage:** {', '.join(a.damage_areas) or NONE_RECORDED}",
        f"- **Injury present:** {a.injury_present} (customer side: {a.customer_side_injured}, "
        f"others: {a.others_injured})",
        f"- **Other party involved:** {a.other_party_involved}",
        f"- **Other property damaged:** {a.other_property_damaged}",
        f"- **Vehicle drivable:** {a.vehicle_drivable}",
        f"- **Police report mentioned:** {a.police_report_mentioned}",
        *[f"- {fact}" for fact in a.key_facts],
    ]
    lines += _list_section("Coverage Lines to Review", [str(c) for c in a.coverage_lines])
    lines += _list_section(
        "Missing Information", [MISSING_WORDING[m] for m in a.missing_information]
    )
    lines += _list_section(
        "Contradictions", [f'"{c.statement_a}" vs. "{c.statement_b}"' for c in a.contradictions]
    )
    lines += [
        "",
        "## Sentiment and Risk",
        f"- **Sentiment:** {risk.sentiment}",
        f"- **Risk level:** {risk.risk_level}",
        f"- **Indicators:** {', '.join(risk.indicators) or NONE_RECORDED}",
        f"- **Rationale:** {risk.rationale}",
    ]
    lines += [
        "",
        "## Routing and Follow-up",
        f"- **Teams:** {', '.join(risk.teams)}",
        f"- **Follow up by:** {risk.follow_up_date.isoformat()} "
        f"({risk.follow_up_business_days} business day(s))",
    ]
    lines += [
        "",
        "## Privacy",
        f"- **Personal information types removed:** "
        f"{', '.join(pii_types_removed) or NONE_RECORDED}",
    ]
    lines += ["", "---", DECISION_NOTICE, ""]
    return InternalReport(markdown="\n".join(lines))


def render_status_only_report(
    claim_id: str | None,
    filed_at: datetime,
    status: ProcessingStatus,
    failed_step: PipelineStep | None,
    error_category: str | None,
) -> InternalReport:
    """Used for every failure and for privacy review: no narrative, no facts."""
    lines = _header(claim_id, filed_at, status)
    lines += [
        f"- **Failed step:** {failed_step or NONE_RECORDED}",
        f"- **Error category:** {error_category or NONE_RECORDED}",
        "",
        "---",
        DECISION_NOTICE,
        "",
    ]
    return InternalReport(markdown="\n".join(lines))
