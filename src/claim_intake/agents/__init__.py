"""The model-backed agents. Built together from one model so tests can swap it in one place."""

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake.agents import intake
from claim_intake.contracts import IntakeLlmOutput


@dataclass(frozen=True)
class Agents:
    intake: Agent[None, IntakeLlmOutput]


def create_agents(model: Model) -> Agents:
    return Agents(intake=intake.build_agent(model))
