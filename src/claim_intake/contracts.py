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
