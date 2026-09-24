"""Typed contracts passed between the orchestrator and agents (see data-model.md)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    """Base for every handoff model: immutable and closed to unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PiiType(StrEnum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    SSN = "SSN"
    CARD = "CARD"
    DOB = "DOB"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    VIN = "VIN"
    PLATE = "PLATE"
    POLICY_NUMBER = "POLICY_NUMBER"
    ADDRESS = "ADDRESS"
    PERSON = "PERSON"
    OTHER_IDENTIFIER = "OTHER_IDENTIFIER"


class SuggestedPiiType(StrEnum):
    """The only kinds of PII the model may suggest (regex handles the rest)."""

    PERSON = "PERSON"
    PLATE = "PLATE"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    OTHER_IDENTIFIER = "OTHER_IDENTIFIER"


class PiiSuggestion(Contract):
    text: str
    pii_type: SuggestedPiiType


class IntakeLlmOutput(Contract):
    """What the intake model may return: spans it believes are still personal information."""

    suggestions: list[PiiSuggestion]


class RawSubmission(Contract):
    """The customer's original words. Never leaves the orchestrator and the intake step."""

    text: str


class SanitizedSubmission(Contract):
    """The only narrative type downstream agents accept."""

    text: str
    pii_types_removed: list[PiiType]
    requires_manual_review: bool


# --- Assessment (US2) ------------------------------------------------------------------------


class IncidentType(StrEnum):
    COLLISION = "COLLISION"
    THEFT = "THEFT"
    VANDALISM = "VANDALISM"
    WEATHER = "WEATHER"
    FIRE = "FIRE"
    GLASS = "GLASS"
    ANIMAL_STRIKE = "ANIMAL_STRIKE"
    UNKNOWN = "UNKNOWN"
    MIXED = "MIXED"


class UmUimSubtype(StrEnum):
    HIT_AND_RUN = "HIT_AND_RUN"
    UNINSURED = "UNINSURED"
    COVERAGE_DENIED = "COVERAGE_DENIED"
    UNDERINSURED = "UNDERINSURED"


class TriState(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class MissingItem(StrEnum):
    """Declared in the order the customer sees them."""

    WHAT_HAPPENED = "WHAT_HAPPENED"
    INCIDENT_DATE = "INCIDENT_DATE"
    LOCATION = "LOCATION"
    DAMAGE_DESCRIPTION = "DAMAGE_DESCRIPTION"
    OTHER_PARTY_INVOLVEMENT = "OTHER_PARTY_INVOLVEMENT"
    POLICE_REPORT = "POLICE_REPORT"


class CoverageLine(StrEnum):
    """Coverage lines an adjuster should review. Never a statement that something is covered."""

    COLLISION = "COLLISION"
    COMPREHENSIVE = "COMPREHENSIVE"
    LIABILITY_BODILY_INJURY = "LIABILITY_BODILY_INJURY"
    LIABILITY_PROPERTY_DAMAGE = "LIABILITY_PROPERTY_DAMAGE"
    UM_UIM = "UM_UIM"
    PIP_MEDPAY = "PIP_MEDPAY"


class Contradiction(Contract):
    statement_a: str
    statement_b: str
    about_injury: bool


class AssessmentLlmOutput(Contract):
    """What the assessment model may judge. Everything else is added by rules."""

    incident_type: IncidentType
    um_uim_subtype: UmUimSubtype | None
    incident_date: str | None
    location: str | None
    damage_areas: list[str]
    customer_side_injured: TriState
    others_injured: TriState
    other_party_involved: TriState
    other_property_damaged: TriState
    vehicle_drivable: TriState
    police_report_mentioned: TriState
    key_facts: list[str]
    contradictions: list[Contradiction]


class ClaimAssessment(AssessmentLlmOutput):
    injury_present: TriState
    missing_information: list[MissingItem]
    coverage_lines: list[CoverageLine]


# --- Sentiment, risk, and routing (US3) ------------------------------------------------------


class Sentiment(StrEnum):
    CALM = "CALM"
    CONCERNED = "CONCERNED"
    FRUSTRATED = "FRUSTRATED"
    DISTRESSED = "DISTRESSED"
    ANGRY = "ANGRY"


class RiskIndicator(StrEnum):
    INJURY_REPORTED = "INJURY_REPORTED"
    HIT_AND_RUN_NO_POLICE_REPORT = "HIT_AND_RUN_NO_POLICE_REPORT"
    CONTRADICTORY_STATEMENTS = "CONTRADICTORY_STATEMENTS"
    CRITICAL_INFO_MISSING = "CRITICAL_INFO_MISSING"
    MIXED_INCIDENTS = "MIXED_INCIDENTS"
    LEGAL_REPRESENTATION_MENTIONED = "LEGAL_REPRESENTATION_MENTIONED"
    POSSIBLE_PROMPT_INJECTION = "POSSIBLE_PROMPT_INJECTION"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Team(StrEnum):
    CLAIMS_ADJUSTER = "CLAIMS_ADJUSTER"
    CUSTOMER_RELATIONS = "CUSTOMER_RELATIONS"
    SPECIAL_REVIEW = "SPECIAL_REVIEW"
    PRIVACY_REVIEW = "PRIVACY_REVIEW"


class RiskLlmOutput(Contract):
    """What the risk model may judge. Level, teams, and dates are decided by rules."""

    sentiment: Sentiment
    legal_representation_mentioned: bool
    possible_prompt_injection: bool
    rationale: str = Field(min_length=1, max_length=300)


class RiskAssessment(Contract):
    sentiment: Sentiment
    indicators: list[RiskIndicator]
    risk_level: RiskLevel
    teams: list[Team]
    follow_up_business_days: int
    follow_up_date: date
    rationale: str


# --- Reply and report (US4) ------------------------------------------------------------------


class SummaryLlmOutput(Contract):
    """The only customer-facing text the model writes; checked before use (research R8)."""

    opening_line: str
    recorded_points: list[str] = Field(min_length=1, max_length=5)
    narrative_summary: str


class CustomerReply(Contract):
    text: str


class InternalReport(Contract):
    markdown: str


class ProcessingStatus(StrEnum):
    COMPLETED = "COMPLETED"
    REJECTED_INPUT = "REJECTED_INPUT"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    FAILED_MODEL_ERROR = "FAILED_MODEL_ERROR"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_OUTPUT = "FAILED_OUTPUT"


class PipelineStep(StrEnum):
    VALIDATE_INPUT = "VALIDATE_INPUT"
    INTAKE = "INTAKE"
    ASSESSMENT = "ASSESSMENT"
    RISK = "RISK"
    SUMMARY = "SUMMARY"
    PRIVACY_GUARD = "PRIVACY_GUARD"
    SAVE = "SAVE"
