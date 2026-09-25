"""The model-backed agents. Built together from one model so tests can swap it in one place."""

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake.agents import assessment, intake, risk, summary
from claim_intake.contracts import (
    AssessmentLlmOutput,
    HelpReplyLlmOutput,
    HelpTriageLlmOutput,
    IntakeLlmOutput,
    RiskLlmOutput,
    SummaryLlmOutput,
    UpdateLlmOutput,
)


@dataclass(frozen=True)
class Agents:
    intake: Agent[None, IntakeLlmOutput]
    assessment: Agent[None, AssessmentLlmOutput]
    assessment_update: Agent[None, UpdateLlmOutput]
    risk: Agent[None, RiskLlmOutput]
    help_triage: Agent[None, HelpTriageLlmOutput]
    summary: Agent[None, SummaryLlmOutput]
    help_reply: Agent[None, HelpReplyLlmOutput]


def create_agents(model: Model) -> Agents:
    return Agents(
        intake=intake.build_agent(model),
        assessment=assessment.build_agent(model),
        assessment_update=assessment.build_update_agent(model),
        risk=risk.build_agent(model),
        help_triage=risk.build_help_agent(model),
        summary=summary.build_agent(model),
        help_reply=summary.build_help_agent(model),
    )
