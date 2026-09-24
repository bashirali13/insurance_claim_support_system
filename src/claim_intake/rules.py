"""Fixed business rules (data-model.md). Deterministic, no model calls."""

from claim_intake.contracts import (
    AssessmentLlmOutput,
    CoverageLine,
    IncidentType,
    MissingItem,
    TriState,
    UmUimSubtype,
)

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
