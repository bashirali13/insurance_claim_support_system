"""Shared test setup: no real model calls, a fixed clock, and scripted models."""

import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

import pytest  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from pydantic_ai import models  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def fixed_now() -> datetime:
    """Thursday, Sep 24 2026, 10:15."""
    return datetime(2026, 9, 24, 10, 15)


@pytest.fixture
def workdirs(tmp_path: Path) -> Path:
    for sub in ("data/claims", "output", "logs"):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path


def _as_args(output: BaseModel | dict) -> dict:
    return output.model_dump(mode="json") if isinstance(output, BaseModel) else output


def structured_model(*outputs: BaseModel | dict) -> FunctionModel:
    """A model that answers each call with the next output as its structured result.

    Pass a dict instead of a model to send deliberately invalid output.
    """
    queue = list(outputs)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        output = queue.pop(0) if len(queue) > 1 else queue[0]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, _as_args(output))])

    return FunctionModel(respond)


def failing_model(exc: Exception) -> FunctionModel:
    """A model whose every call raises `exc`."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise exc

    return FunctionModel(respond)


class CapturedCall:
    """What a capture_model received on its most recent call."""

    prompt: str = ""
    instructions: str = ""


def capture_model(output: BaseModel | dict) -> tuple[FunctionModel, CapturedCall]:
    """A model that answers with `output` and records the prompt text and instructions it saw."""
    seen = CapturedCall()

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.prompt = "\n".join(
            str(part.content)
            for message in messages
            for part in message.parts
            if part.part_kind == "user-prompt"
        )
        seen.instructions = info.instructions or ""
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, _as_args(output))])

    return FunctionModel(respond), seen
