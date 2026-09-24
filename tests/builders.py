"""Small builders so each test states only the facts it cares about."""

from claim_intake import rules
from claim_intake.contracts import (
    AssessmentLlmOutput,
    ClaimAssessment,
    IncidentType,
    RiskLlmOutput,
    SanitizedSubmission,
    Sentiment,
    TriState,
)


def assessment_output(**overrides) -> AssessmentLlmOutput:
    """A complete, unremarkable collision; override only what the test is about."""
    fields = {
        "incident_type": IncidentType.COLLISION,
        "um_uim_subtype": None,
        "incident_date": "yesterday around 6pm",
        "location": "Main St",
        "damage_areas": ["rear bumper"],
        "customer_side_injured": TriState.NO,
        "others_injured": TriState.NO,
        "other_party_involved": TriState.YES,
        "other_property_damaged": TriState.NO,
        "vehicle_drivable": TriState.YES,
        "police_report_mentioned": TriState.NO,
        "key_facts": ["Rear-ended at a red light"],
        "contradictions": [],
    }
    fields.update(overrides)
    return AssessmentLlmOutput(**fields)


def claim_assessment(**overrides) -> ClaimAssessment:
    """A completed assessment, with the rule-derived fields computed as the real agent would."""
    facts = assessment_output(**overrides)
    return ClaimAssessment(
        **facts.model_dump(),
        injury_present=rules.injury_present(facts),
        missing_information=rules.missing_information(facts),
        coverage_lines=rules.coverage_lines(facts),
    )


def risk_output(**overrides) -> RiskLlmOutput:
    """A calm customer with nothing flagged; override only what the test is about."""
    fields = {
        "sentiment": Sentiment.CALM,
        "legal_representation_mentioned": False,
        "possible_prompt_injection": False,
        "rationale": "Rear-end collision with no injuries reported.",
    }
    fields.update(overrides)
    return RiskLlmOutput(**fields)


def sanitized(text: str = "Rear-ended at a red light on Main St.") -> SanitizedSubmission:
    return SanitizedSubmission(text=text, pii_types_removed=[], requires_manual_review=False)
