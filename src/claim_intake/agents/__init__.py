"""The model-backed agents. Built together from one model so tests can swap it in one place."""

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake.agents import assessment, intake, risk, summary
from claim_intake.contracts import (
    AssessmentLlmOutput,
    IntakeLlmOutput,
    RiskLlmOutput,
    SummaryLlmOutput,
)


@dataclass(frozen=True)
class Agents:
    intake: Agent[None, IntakeLlmOutput]
    assessment: Agent[None, AssessmentLlmOutput]
    risk: Agent[None, RiskLlmOutput]
    summary: Agent[None, SummaryLlmOutput]


def create_agents(model: Model) -> Agents:
    return Agents(
        intake=intake.build_agent(model),
        assessment=assessment.build_agent(model),
        risk=risk.build_agent(model),
        summary=summary.build_agent(model),
    )
