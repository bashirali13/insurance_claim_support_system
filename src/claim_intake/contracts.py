"""Typed contracts passed between the orchestrator and agents (see data-model.md)."""

from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    """Base for every handoff model: immutable and closed to unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
