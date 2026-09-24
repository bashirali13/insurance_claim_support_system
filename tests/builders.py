"""Small builders so each test states only the facts it cares about."""

from claim_intake.contracts import (
    AssessmentLlmOutput,
    IncidentType,
    SanitizedSubmission,
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


def sanitized(text: str = "Rear-ended at a red light on Main St.") -> SanitizedSubmission:
    return SanitizedSubmission(text=text, pii_types_removed=[], requires_manual_review=False)
