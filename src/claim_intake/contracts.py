"""Typed contracts passed between the orchestrator and agents (see data-model.md)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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
