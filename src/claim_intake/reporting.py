"""Customer reply and internal report templates (contracts/cli.md, contracts/files.md).

The model supplies only the opening line, recorded points, and staff summary. Everything else,
including every date, team, and missing item, is rendered here from the structured contracts.
"""

from datetime import date, datetime

from claim_intake.contracts import (
    ClaimAssessment,
    ClaimRecord,
    ClaimStatus,
    CustomerReply,
    FactChanges,
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
    Team.POLICY_SERVICES: "Our Policy Services team",
    Team.PRIVACY_REVIEW: "A specialist",
}

STATUS_WORDING = {
    ClaimStatus.SUBMITTED: "Received and waiting for review",
    ClaimStatus.AWAITING_INFORMATION: "Waiting for information from you",
    ClaimStatus.UNDER_REVIEW: "Under review by a claims adjuster",
    ClaimStatus.ESCALATED: "With a specialist team for priority review",
    ClaimStatus.CLOSED: "Closed",
}

HISTORY_WORDING = {
    "FILED": "Claim filed",
    "DETAILS_UPDATED": "Details added by you",
    "HELP_REQUESTED": "Help request received",
    "PRIVACY_REVIEW_OPENED": "Specialist review started",
}

# How claim fields are named to customers (updates and pending confirmations).
FIELD_WORDING = {
    "incident_date": "when it happened",
    "location": "where it happened",
    "damage_areas": "damage",
    "police_report_mentioned": "police report",
    "vehicle_drivable": "whether the car can be driven",
    "other_property_damaged": "damage to other property",
    "incident_type": "what kind of incident it was",
    "um_uim_subtype": "the other driver's insurance situation",
    "customer_side_injured": "injuries to you or your passengers",
    "others_injured": "injuries to other people",
    "other_party_involved": "whether another party was involved",
}


def format_follow_up(day: date) -> str:
    """e.g. 'Friday, Sep 25'."""
    return f"{day:%A}, {day:%b} {day.day}"


def format_day(day: date) -> str:
    """e.g. 'Sep 23, 2026'."""
    return f"{day:%b} {day.day}, {day.year}"


def incident_wording(incident: IncidentType) -> str:
    return incident.replace("_", " ").capitalize()


def render_status(record: ClaimRecord, today: date) -> str:
    """Option 2 reply (contracts/cli.md). Built from the saved record only; no model."""
    a = record.assessment
    filed = format_day(record.filed_at.date())
    header = f"Claim {record.claim_id}"
    header += f": {incident_wording(a.incident_type)} (filed {filed})" if a else f" (filed {filed})"
    last = record.history[-1]
    lines = [
        header,
        f"  Status:      {STATUS_WORDING[record.status]}",
        f"  Last update: {format_day(last.at.date())} - {HISTORY_WORDING[last.event]}",
    ]
    if a and a.missing_information:
        lines.append("  Still needed:")
        lines += [f"    • {MISSING_WORDING[item]}" for item in a.missing_information]
    if a and record.pending_changes:
        lines.append("  Waiting for an adjuster to confirm:")
        lines += [f"    • {FIELD_WORDING[change.field]}" for change in record.pending_changes]
    role = next((TEAM_ROLE[t] for t in record.teams if t in TEAM_ROLE), None)
    if record.status != ClaimStatus.CLOSED and record.follow_up_date >= today and role:
        by = format_follow_up(record.follow_up_date)
        lines.append(f"  Next step:   {role} will contact you by {by}.")
    return "\n".join(lines)


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


FILE_CLAIM_TASK = "File a new claim"
UPDATE_TASK = "Add or correct details"


def _header(
    claim_id: str | None, filed_at: datetime, status: ProcessingStatus, task: str = FILE_CLAIM_TASK
) -> list[str]:
    return [
        f"# Claim Intake Report — {claim_id or 'UNFILED'}",
        f"- **Processing status:** {status}",
        f"- **Task:** {task}",
        f"- **Filed:** {filed_at:%Y-%m-%d %H:%M}",
    ]


def _risk_section(risk: RiskAssessment) -> list[str]:
    return [
        "",
        "## Sentiment and Risk",
        f"- **Sentiment:** {risk.sentiment}",
        f"- **Risk level:** {risk.risk_level}",
        f"- **Indicators:** {', '.join(risk.indicators) or NONE_RECORDED}",
        f"- **Rationale:** {risk.rationale}",
    ]


def _privacy_section(pii_types_removed: list[PiiType]) -> list[str]:
    removed = ", ".join(pii_types_removed) or NONE_RECORDED
    return ["", "## Privacy", f"- **Personal information types removed:** {removed}"]


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
    lines += _risk_section(risk)
    lines += [
        "",
        "## Routing and Follow-up",
        f"- **Teams:** {', '.join(risk.teams)}",
        f"- **Follow up by:** {risk.follow_up_date.isoformat()} "
        f"({risk.follow_up_business_days} business day(s))",
    ]
    lines += _privacy_section(pii_types_removed)
    lines += ["", "---", DECISION_NOTICE, ""]
    return InternalReport(markdown="\n".join(lines))


# --- Updates (specs/002 US7, contracts/cli.md option 3) -----------------------------------------

# Teams with their own line in an update reply, so they're left out of "What happens next".
_OWN_LINE_TEAMS = {Team.POLICY_SERVICES}


def _change_lines(changes: FactChanges) -> list[str]:
    lines = []
    for c in changes.added:
        detail = f" ({c.new})" if c.field == "damage_areas" else ""
        lines.append(f"Added: {FIELD_WORDING[c.field]}{detail}")
    for c in changes.corrected:
        old, new = c.old or "unknown", c.new or "unknown"
        lines.append(f"Corrected: {FIELD_WORDING[c.field]} ({old} → {new})")
    return lines


def render_update_reply(
    claim_id: str,
    changes: FactChanges,
    *,
    contact_change_requested: bool,
    teams: list[Team],
    routing_date: date,
    pending_date: date,
    contact_date: date,
    missing: list[MissingItem],
) -> CustomerReply:
    lines = [f"Thanks, your claim {claim_id} is updated.", *_bullets(_change_lines(changes))]
    if changes.sensitive:
        fields = ", ".join(FIELD_WORDING[c.field] for c in changes.sensitive)
        by = format_follow_up(pending_date)
        lines += [f"  • An adjuster will confirm this change with you by {by}:", f"    {fields}"]
    if contact_change_requested:
        by = format_follow_up(contact_date)
        lines += [
            f"  • Our Policy Services team will confirm your new contact details with you by {by}.",
            "    We didn't store them here.",
        ]
    by = format_follow_up(routing_date)
    next_steps = [
        f"{TEAM_ROLE[t]} will contact you by {by}."
        for t in teams
        if t in TEAM_ROLE and t not in _OWN_LINE_TEAMS
    ]
    if next_steps:
        lines += ["", "What happens next:", *_bullets(next_steps)]
    if missing:
        lines += ["", "Still needed:", *_bullets([MISSING_WORDING[m] for m in missing])]
    return CustomerReply(text="\n".join(lines))


def render_update_report(
    claim_id: str,
    filed_at: datetime,
    changes: FactChanges,
    *,
    contact_change_requested: bool,
    submission: SanitizedSubmission,
    assessment: ClaimAssessment,
    risk: RiskAssessment,
    teams: list[Team],
    follow_up_date: date,
) -> InternalReport:
    def described(items):
        return [f"{c.field}: {c.old or 'unknown'} → {c.new or 'unknown'}" for c in items]

    lines = _header(claim_id, filed_at, ProcessingStatus.COMPLETED, UPDATE_TASK)
    lines += _list_section("Added", [f"{FIELD_WORDING[c.field]}: {c.new}" for c in changes.added])
    lines += _list_section("Corrected", described(changes.corrected))
    lines += _list_section("Pending Adjuster Confirmation", described(changes.sensitive))
    contact = ["Customer asked to change contact details (value not stored)"]
    lines += _list_section("Contact Change", contact if contact_change_requested else [])
    lines += _list_section(
        "Missing Information", [MISSING_WORDING[m] for m in assessment.missing_information]
    )
    lines += _risk_section(risk)
    lines += [
        "",
        "## Routing and Follow-up",
        f"- **Teams:** {', '.join(teams)}",
        f"- **Follow up by:** {follow_up_date.isoformat()}",
    ]
    lines += _privacy_section(submission.pii_types_removed)
    lines += ["", "---", DECISION_NOTICE, ""]
    return InternalReport(markdown="\n".join(lines))


def render_status_only_report(
    claim_id: str | None,
    filed_at: datetime,
    status: ProcessingStatus,
    failed_step: PipelineStep | None,
    error_category: str | None,
    task: str = FILE_CLAIM_TASK,
) -> InternalReport:
    """Used for every failure and for privacy review: no narrative, no facts."""
    lines = _header(claim_id, filed_at, status, task)
    lines += [
        f"- **Failed step:** {failed_step or NONE_RECORDED}",
        f"- **Error category:** {error_category or NONE_RECORDED}",
        "",
        "---",
        DECISION_NOTICE,
        "",
    ]
    return InternalReport(markdown="\n".join(lines))
