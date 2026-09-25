"""Small builders so each test states only the facts it cares about."""

from datetime import date

from claim_intake import rules
from claim_intake.contracts import (
    AssessmentLlmOutput,
    ClaimAssessment,
    HelpTriageLlmOutput,
    IncidentType,
    RequestCategory,
    RiskAssessment,
    RiskLevel,
    RiskLlmOutput,
    SanitizedSubmission,
    Sentiment,
    SummaryLlmOutput,
    Team,
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


def risk_assessment(**overrides) -> RiskAssessment:
    """A low-risk result routed to the adjuster for Monday, Sep 28 (two business days)."""
    fields = {
        "sentiment": Sentiment.CALM,
        "indicators": [],
        "risk_level": RiskLevel.LOW,
        "teams": [Team.CLAIMS_ADJUSTER],
        "follow_up_business_days": 2,
        "follow_up_date": date(2026, 9, 28),
        "rationale": "Rear-end collision with no injuries reported.",
    }
    fields.update(overrides)
    return RiskAssessment(**fields)


def summary_output(**overrides) -> SummaryLlmOutput:
    fields = {
        "opening_line": "Thank you for telling us what happened.",
        "recorded_points": ["Rear-ended at a red light on Main St", "Damage: rear bumper"],
        "narrative_summary": "Customer was rear-ended at a red light. No injuries reported.",
    }
    fields.update(overrides)
    return SummaryLlmOutput(**fields)


def triage_output(**overrides) -> HelpTriageLlmOutput:
    """A calm claim question with nothing flagged; override only what the test is about."""
    fields = {
        "sentiment": Sentiment.CALM,
        "categories": [RequestCategory.CLAIM_QUESTION],
        "legal_representation_mentioned": False,
        "possible_prompt_injection": False,
        "rationale": "Customer asked a question about their claim.",
    }
    fields.update(overrides)
    return HelpTriageLlmOutput(**fields)


def sanitized(text: str = "Rear-ended at a red light on Main St.") -> SanitizedSubmission:
    return SanitizedSubmission(text=text, pii_types_removed=[], requires_manual_review=False)
