"""Typed contracts passed between the orchestrator and agents (see data-model.md)."""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

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
    POLICY_SERVICES = "POLICY_SERVICES"


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


# --- Persistence and results (US5) -----------------------------------------------------------


class ClaimStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    AWAITING_INFORMATION = "AWAITING_INFORMATION"
    UNDER_REVIEW = "UNDER_REVIEW"  # set by staff (sample data in this phase)
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"  # set by staff (sample data in this phase)


class HistoryEntry(Contract):
    at: datetime
    event: Literal["FILED", "PRIVACY_REVIEW_OPENED", "DETAILS_UPDATED", "HELP_REQUESTED"]
    detail: str | None = None  # changed field names or a help reference; never values


SensitiveField = Literal[
    "incident_type",
    "um_uim_subtype",
    "customer_side_injured",
    "others_injured",
    "other_party_involved",
]


class PendingChange(Contract):
    """A sensitive correction held until an adjuster confirms it (FR-209)."""

    field: SensitiveField
    requested_value: str
    requested_at: datetime


class ClaimRecord(Contract):
    """Saved as data/claims/<claim_id>.json. Never contains personal values."""

    claim_id: str = Field(pattern=r"^CLM-\d{4}-\d{4}$")
    status: ClaimStatus
    filed_at: datetime
    assessment: ClaimAssessment | None
    teams: list[Team]
    follow_up_date: date
    history: list[HistoryEntry] = Field(min_length=1)
    pending_changes: list[PendingChange] = []


class TaskResult(Contract):
    """What every UI receives from the orchestrator."""

    processing_status: ProcessingStatus
    claim_id: str | None
    customer_message: str
    report_path: str | None


class MenuTask(StrEnum):
    FILE_CLAIM = "FILE_CLAIM"
    UPDATE_DETAILS = "UPDATE_DETAILS"
    GET_HELP = "GET_HELP"


class EventLogEntry(Contract):
    """One text-free line in logs/events.log (FR-033, FR-218)."""

    ts: datetime
    claim_id: str | None
    task: MenuTask
    step: PipelineStep
    outcome: ProcessingStatus
    duration_ms: int
    error_category: str | None


# --- Updates to an existing claim (specs/002 US7) ----------------------------------------------


class UpdateLlmOutput(Contract):
    """What the update-mode model may return: the full facts after the customer's update."""

    updated: AssessmentLlmOutput
    contact_change_requested: bool


class FieldChange(Contract):
    field: str
    old: str | None
    new: str | None


class FactChanges(Contract):
    """What an update changed, decided by code (rules.diff_facts), never by the model."""

    added: list[FieldChange]
    corrected: list[FieldChange]
    sensitive: list[FieldChange]
    applied: AssessmentLlmOutput

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.corrected or self.sensitive)


# --- Get help (specs/002 US8) ------------------------------------------------------------------


class RequestCategory(StrEnum):
    COMPLAINT = "COMPLAINT"
    SERVICE_DELAY = "SERVICE_DELAY"
    CLAIM_QUESTION = "CLAIM_QUESTION"
    SPEAK_TO_ADJUSTER = "SPEAK_TO_ADJUSTER"
    CONTACT_CHANGE = "CONTACT_CHANGE"
    FILE_A_CLAIM = "FILE_A_CLAIM"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class HelpTriageLlmOutput(Contract):
    """What the help-triage model may judge. Teams and dates are decided by rules."""

    sentiment: Sentiment
    categories: list[RequestCategory] = Field(min_length=1, max_length=3)
    legal_representation_mentioned: bool
    possible_prompt_injection: bool
    rationale: str = Field(min_length=1, max_length=300)


class HelpReplyLlmOutput(Contract):
    """The only help-reply text the model writes; checked before use."""

    opening_line: str


class TeamPromise(Contract):
    team: Team
    business_days: int
    follow_up_date: date


class HelpRecord(Contract):
    """Saved as data/help/<help_id>.json. Never contains the request text or personal values."""

    help_id: str = Field(pattern=r"^HELP-\d{4}-\d{4}$")
    claim_id: str | None
    filed_at: datetime
    sentiment: Sentiment | None  # None only for privacy review (AC-8.12)
    categories: list[RequestCategory]  # empty only for privacy review
    routed: list[TeamPromise] = Field(min_length=1)
    history: list[HistoryEntry] = Field(min_length=1)
