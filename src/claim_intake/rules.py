"""Fixed business rules (data-model.md). Deterministic, no model calls."""

import re
from datetime import date

from claim_intake.contracts import (
    AssessmentLlmOutput,
    ClaimAssessment,
    ClaimStatus,
    CoverageLine,
    FactChanges,
    FieldChange,
    HelpTriageLlmOutput,
    IncidentType,
    MissingItem,
    RequestCategory,
    RiskIndicator,
    RiskLevel,
    RiskLlmOutput,
    Sentiment,
    Team,
    TriState,
    UmUimSubtype,
)
from claim_intake.dates import add_business_days

COMPREHENSIVE_INCIDENTS = {
    IncidentType.THEFT,
    IncidentType.VANDALISM,
    IncidentType.WEATHER,
    IncidentType.FIRE,
    IncidentType.GLASS,
    IncidentType.ANIMAL_STRIKE,
}


def injury_present(facts: AssessmentLlmOutput) -> TriState:
    """An injury contradiction makes injury unknown; otherwise YES if anyone was hurt."""
    sides = (facts.customer_side_injured, facts.others_injured)
    if any(c.about_injury for c in facts.contradictions):
        return TriState.UNKNOWN
    if TriState.YES in sides:
        return TriState.YES
    if TriState.UNKNOWN in sides:
        return TriState.UNKNOWN
    return TriState.NO


def missing_information(facts: AssessmentLlmOutput) -> list[MissingItem]:
    """Per-incident checklist (FR-013). Returned in MissingItem declaration order."""
    incident = facts.incident_type
    missing: set[MissingItem] = set()

    if incident == IncidentType.MIXED:
        return []
    if incident == IncidentType.UNKNOWN:
        missing.add(MissingItem.WHAT_HAPPENED)
    if facts.incident_date is None:
        missing.add(MissingItem.INCIDENT_DATE)
    if facts.location is None:
        missing.add(MissingItem.LOCATION)
    if not facts.damage_areas and incident not in {IncidentType.UNKNOWN, IncidentType.THEFT}:
        missing.add(MissingItem.DAMAGE_DESCRIPTION)

    no_police_report = facts.police_report_mentioned != TriState.YES
    if incident == IncidentType.COLLISION:
        if facts.other_party_involved == TriState.UNKNOWN:
            missing.add(MissingItem.OTHER_PARTY_INVOLVEMENT)
        needs_report = (
            facts.um_uim_subtype == UmUimSubtype.HIT_AND_RUN
            or injury_present(facts) == TriState.YES
        )
        if needs_report and no_police_report:
            missing.add(MissingItem.POLICE_REPORT)
    if incident in {IncidentType.THEFT, IncidentType.VANDALISM} and no_police_report:
        missing.add(MissingItem.POLICE_REPORT)

    return [item for item in MissingItem if item in missing]


def coverage_lines(facts: AssessmentLlmOutput) -> list[CoverageLine]:
    """Coverage lines to review (FR-014), in CoverageLine declaration order."""
    lines: set[CoverageLine] = set()
    if facts.incident_type == IncidentType.COLLISION:
        lines.add(CoverageLine.COLLISION)
    if facts.incident_type in COMPREHENSIVE_INCIDENTS:
        lines.add(CoverageLine.COMPREHENSIVE)
    if facts.others_injured == TriState.YES:
        lines.add(CoverageLine.LIABILITY_BODILY_INJURY)
    if facts.other_property_damaged == TriState.YES:
        lines.add(CoverageLine.LIABILITY_PROPERTY_DAMAGE)
    if facts.um_uim_subtype is not None:
        lines.add(CoverageLine.UM_UIM)
    if facts.customer_side_injured == TriState.YES:
        lines.add(CoverageLine.PIP_MEDPAY)
    return [line for line in CoverageLine if line in lines]


# --- Risk and routing (FR-016 to FR-020) ------------------------------------------------------

# FR-017a: checked by code so detection never depends only on the model being attacked.
# Phrases common in ordinary stories (e.g. "act as") are deliberately excluded.
INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore your instructions",
    "ignore your rules",
    "disregard your rules",
    "system prompt",
    "you are now an",
)

ALWAYS_HIGH = {
    RiskIndicator.LEGAL_REPRESENTATION_MENTIONED,
    RiskIndicator.POSSIBLE_PROMPT_INJECTION,
}
UPSET = {Sentiment.DISTRESSED, Sentiment.ANGRY}


def has_injection_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in INJECTION_PHRASES)


def indicators(
    assessment: ClaimAssessment, judged: RiskLlmOutput, text: str
) -> list[RiskIndicator]:
    """Fact-based indicators come from rules; only two may come from the model (FR-017)."""
    found: set[RiskIndicator] = set()
    if assessment.injury_present == TriState.YES:
        found.add(RiskIndicator.INJURY_REPORTED)
    if (
        assessment.um_uim_subtype == UmUimSubtype.HIT_AND_RUN
        and assessment.police_report_mentioned != TriState.YES
    ):
        found.add(RiskIndicator.HIT_AND_RUN_NO_POLICE_REPORT)
    if assessment.contradictions:
        found.add(RiskIndicator.CONTRADICTORY_STATEMENTS)
    if {MissingItem.INCIDENT_DATE, MissingItem.LOCATION} & set(assessment.missing_information):
        found.add(RiskIndicator.CRITICAL_INFO_MISSING)
    if assessment.incident_type == IncidentType.MIXED:
        found.add(RiskIndicator.MIXED_INCIDENTS)
    if judged.legal_representation_mentioned:
        found.add(RiskIndicator.LEGAL_REPRESENTATION_MENTIONED)
    if judged.possible_prompt_injection or has_injection_phrase(text):
        found.add(RiskIndicator.POSSIBLE_PROMPT_INJECTION)
    return [indicator for indicator in RiskIndicator if indicator in found]


def risk_level(found: list[RiskIndicator]) -> RiskLevel:
    """FR-018. Sentiment is deliberately not an input."""
    if ALWAYS_HIGH & set(found) or len(found) >= 2:
        return RiskLevel.HIGH
    if len(found) == 1:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def teams(sentiment: Sentiment, found: list[RiskIndicator]) -> list[Team]:
    """FR-019: the adjuster always; plus Customer Relations and Special Review when warranted."""
    routed = [Team.CLAIMS_ADJUSTER]
    if sentiment in UPSET:
        routed.append(Team.CUSTOMER_RELATIONS)
    if ALWAYS_HIGH & set(found):
        routed.append(Team.SPECIAL_REVIEW)
    return routed


def follow_up_days(
    assessment: ClaimAssessment, found: list[RiskIndicator], level: RiskLevel
) -> int:
    """FR-020: one business day when someone may be hurt or risk is high; otherwise two."""
    injury_contradicted = any(c.about_injury for c in assessment.contradictions)
    urgent = (
        RiskIndicator.INJURY_REPORTED in found or injury_contradicted or level == RiskLevel.HIGH
    )
    return 1 if urgent else 2


# --- Claim status (FR-029) --------------------------------------------------------------------


def initial_status(
    level: RiskLevel | None, missing: list[MissingItem], privacy_review: bool = False
) -> ClaimStatus:
    """Escalated beats awaiting-information, which beats submitted."""
    if privacy_review or level == RiskLevel.HIGH:
        return ClaimStatus.ESCALATED
    if missing:
        return ClaimStatus.AWAITING_INFORMATION
    return ClaimStatus.SUBMITTED


# --- Claim numbers (FR-201) ------------------------------------------------------------------

CLAIM_NUMBER = re.compile(r"^CLM-\d{4}-\d{4}$")


def normalize_claim_number(text: str) -> str | None:
    """Trim and uppercase; None unless it looks like CLM-2026-0007."""
    candidate = text.strip().upper()
    return candidate if CLAIM_NUMBER.match(candidate) else None


# --- Updates to an existing claim (specs/002 FR-207 to FR-210) --------------------------------

SENSITIVE_FIELDS = (
    "incident_type",
    "um_uim_subtype",
    "customer_side_injured",
    "others_injured",
    "other_party_involved",
)
SCALAR_FIELDS = (
    "incident_type",
    "um_uim_subtype",
    "incident_date",
    "location",
    "customer_side_injured",
    "others_injured",
    "other_party_involved",
    "other_property_damaged",
    "vehicle_drivable",
    "police_report_mentioned",
)
MAX_KEY_FACTS = 6


def _is_unknown(value) -> bool:
    return value is None or value in (TriState.UNKNOWN, IncidentType.UNKNOWN)


def _display(value) -> str | None:
    return None if _is_unknown(value) else str(value)


def diff_facts(saved: AssessmentLlmOutput, updated: AssessmentLlmOutput) -> FactChanges:
    """Compare saved and updated facts field by field (research R2).

    Unknown → known is *added* and applied. Known → different is *corrected* and applied, unless
    the field is sensitive; then it is held (kept as saved) for an adjuster to confirm.
    """
    added, corrected, sensitive = [], [], []
    applied = {name: getattr(saved, name) for name in AssessmentLlmOutput.model_fields}

    for name in SCALAR_FIELDS:
        old, new = getattr(saved, name), getattr(updated, name)
        if old == new:
            continue
        change = FieldChange(field=name, old=_display(old), new=_display(new))
        if _is_unknown(old):
            added.append(change)
            applied[name] = new
        elif name in SENSITIVE_FIELDS:
            sensitive.append(change)
        else:
            corrected.append(change)
            applied[name] = new

    new_damage = [d for d in updated.damage_areas if d not in saved.damage_areas]
    if new_damage:
        added.append(FieldChange(field="damage_areas", old=None, new=", ".join(new_damage)))
        applied["damage_areas"] = [*saved.damage_areas, *new_damage]

    new_facts = [f for f in updated.key_facts if f not in saved.key_facts]
    applied["key_facts"] = [*saved.key_facts, *new_facts][-MAX_KEY_FACTS:]
    applied["contradictions"] = [
        *saved.contradictions,
        *(c for c in updated.contradictions if c not in saved.contradictions),
    ]
    return FactChanges(
        added=added,
        corrected=corrected,
        sensitive=sensitive,
        applied=AssessmentLlmOutput(**applied),
    )


def status_after_update(
    current: ClaimStatus, level: RiskLevel, missing: list[MissingItem]
) -> ClaimStatus:
    """FR-208: escalation is never undone; staff-set UNDER_REVIEW is kept."""
    if current == ClaimStatus.ESCALATED or level == RiskLevel.HIGH:
        return ClaimStatus.ESCALATED
    if current == ClaimStatus.UNDER_REVIEW:
        return ClaimStatus.UNDER_REVIEW
    if missing:
        return ClaimStatus.AWAITING_INFORMATION
    return ClaimStatus.SUBMITTED


def earliest_follow_up(today: date, business_days: list[int]) -> date:
    """The claim's single follow-up date is its earliest promise."""
    return min(add_business_days(today, days) for days in business_days)


# --- Get help routing (specs/002 FR-213) --------------------------------------------------------

HELP_TEAM_FOR = {
    RequestCategory.COMPLAINT: (Team.CUSTOMER_RELATIONS, 2),
    RequestCategory.SERVICE_DELAY: (Team.CUSTOMER_RELATIONS, 2),
    RequestCategory.CLAIM_QUESTION: (Team.CLAIMS_ADJUSTER, 2),
    RequestCategory.SPEAK_TO_ADJUSTER: (Team.CLAIMS_ADJUSTER, 2),
    RequestCategory.CONTACT_CHANGE: (Team.POLICY_SERVICES, 3),
    # FILE_A_CLAIM and OUT_OF_SCOPE route nobody: the reply points elsewhere.
}


def help_routing(triage: HelpTriageLlmOutput, text: str) -> list[tuple[Team, int]]:
    """Teams and business days for a help request, one entry per team, in Team order."""
    days_for: dict[Team, int] = {}

    def route(team: Team, days: int) -> None:
        days_for[team] = min(days, days_for.get(team, days))

    for category in triage.categories:
        if category in HELP_TEAM_FOR:
            route(*HELP_TEAM_FOR[category])
    if triage.sentiment in UPSET:
        route(Team.CUSTOMER_RELATIONS, 2)
    flagged = (
        triage.legal_representation_mentioned
        or triage.possible_prompt_injection
        or has_injection_phrase(text)
    )
    if flagged:
        route(Team.CLAIMS_ADJUSTER, 1)
        route(Team.SPECIAL_REVIEW, 1)
        days_for = dict.fromkeys(days_for, 1)
    return [(team, days_for[team]) for team in Team if team in days_for]
