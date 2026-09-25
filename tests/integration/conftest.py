"""Shared helpers for terminal-level tests: scripted keyboard, sample-claim deps, file snapshots."""

import pytest

from claim_intake.agents import create_agents
from claim_intake.orchestration import Deps
from claim_intake.storage import ClaimStore, EventLog, ReportWriter, load_samples
from tests.conftest import failing_model

HEADER = " Northstar Auto Insurance: Claim Support"
CTRL_C = object()  # put in a keyboard script to simulate the customer pressing Ctrl+C


@pytest.fixture
def keyboard(monkeypatch):
    """Feed lines to input() in order, like a real terminal.

    When the script runs out, input() raises EOFError (the terminal closed). A CTRL_C entry raises
    KeyboardInterrupt at that prompt.
    """

    def type_lines(*lines) -> None:
        queue = list(lines)

        def fake_input(prompt=""):
            if not queue:
                raise EOFError
            line = queue.pop(0)
            if line is CTRL_C:
                raise KeyboardInterrupt
            return line

        monkeypatch.setattr("builtins.input", fake_input)

    return type_lines


def make_deps(workdirs, fixed_now, model) -> Deps:
    return Deps(
        agents=create_agents(model),
        store=ClaimStore(workdirs),
        reports=ReportWriter(workdirs),
        events=EventLog(workdirs),
        now=lambda: fixed_now,
    )


@pytest.fixture
def sample_deps(workdirs, fixed_now):
    """Sample claims loaded into a temp folder; any model call would fail loudly."""
    load_samples(workdirs)
    return make_deps(workdirs, fixed_now, failing_model(AssertionError("no model call expected")))


def snapshot(root) -> dict:
    return {p: p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}
