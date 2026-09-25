"""US9: the customer never sees a raw error (contracts/cli.md, phase 003)."""

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from claim_intake import cli
from claim_intake.contracts import HelpReplyLlmOutput, IntakeLlmOutput, RequestCategory
from tests.builders import assessment_output, risk_output, triage_output
from tests.integration.conftest import CTRL_C, HEADER, make_deps, snapshot

UNEXPECTED = "Something went wrong on our side. Please try again later."
STOPPED = "Stopped. Nothing further was sent."
GOODBYE = "Thank you for contacting Northstar Auto Insurance. Goodbye."
NARRATIVE = "Hail dented my hood yesterday at home in Cedar Falls."
NO_SUGGESTIONS = IntakeLlmOutput(suggestions=[])


def answers_then(*outputs, fail_with: BaseException) -> FunctionModel:
    """Answer each model call in order, then raise `fail_with` on the next call."""
    queue = list(outputs)

    def respond(messages, info):
        if not queue:
            raise fail_with
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, queue.pop(0).model_dump(mode="json"))]
        )

    return FunctionModel(respond)


def run(capsys, deps) -> tuple[int, str]:
    code = cli.safe_run(deps)
    return code, capsys.readouterr().out


def reports(workdirs) -> list[str]:
    return [p.read_text(encoding="utf-8") for p in (workdirs / "output").glob("*.md")]


def new_files(before: dict, workdirs, folder: str) -> list:
    return [p for p in snapshot(workdirs) if p not in before and folder in p.as_posix()]


# --- AC-9.1: unexpected bugs ---------------------------------------------------------------


def broken(*args, **kwargs):
    raise ZeroDivisionError("bug")


def test_ac_9_1_unexpected_error_in_filing_shows_message_reports_and_returns_to_menu(
    keyboard, sample_deps, workdirs, monkeypatch, capsys
):
    monkeypatch.setattr(cli, "file_claim", broken)
    keyboard("1", NARRATIVE, "", "5")

    code, out = run(capsys, sample_deps)

    assert code == 0
    assert UNEXPECTED in out
    assert out.count(HEADER) == 2  # back at the menu afterwards
    (report,) = reports(workdirs)
    assert "FAILED_UNEXPECTED" in report
    assert "ZeroDivisionError" in report
    assert "- **Task:** File a new claim" in report


@pytest.mark.parametrize(
    ("option", "flow", "script", "task"),
    [
        ("3", "update_claim", ["CLM-2026-0005", NARRATIVE, ""], "Add or correct details"),
        ("4", "get_help", ["", "Nobody called me back.", ""], "Get help with my claim"),
    ],
)
def test_ac_9_1_unexpected_error_in_update_and_help_also_reported(
    option, flow, script, task, keyboard, sample_deps, workdirs, monkeypatch, capsys
):
    monkeypatch.setattr(cli, flow, broken)
    keyboard(option, *script, "5")

    _, out = run(capsys, sample_deps)

    assert UNEXPECTED in out
    (report,) = reports(workdirs)
    assert "FAILED_UNEXPECTED" in report and f"- **Task:** {task}" in report


def test_ac_9_1_unexpected_error_in_status_check_writes_nothing(
    keyboard, sample_deps, workdirs, monkeypatch, capsys
):
    monkeypatch.setattr(cli, "check_status", broken)
    before = snapshot(workdirs)
    keyboard("2", "CLM-2026-0005", "5")

    _, out = run(capsys, sample_deps)

    assert UNEXPECTED in out
    assert snapshot(workdirs) == before


def test_ac_9_1_unexpected_error_after_reservation_leaves_no_claim_file(
    keyboard, workdirs, fixed_now, capsys
):
    model = answers_then(
        NO_SUGGESTIONS, assessment_output(), risk_output(), fail_with=ZeroDivisionError("bug")
    )
    deps = make_deps(workdirs, fixed_now, model)
    before = snapshot(workdirs)
    keyboard("1", NARRATIVE, "", "5")

    _, out = run(capsys, deps)

    assert UNEXPECTED in out
    assert new_files(before, workdirs, "data/claims") == []


def test_ac_9_1_unexpected_error_after_reference_leaves_no_help_record(
    keyboard, sample_deps, workdirs, fixed_now, capsys
):
    triage = triage_output(categories=[RequestCategory.SERVICE_DELAY])
    deps = make_deps(
        workdirs, fixed_now, answers_then(NO_SUGGESTIONS, triage, fail_with=ZeroDivisionError())
    )
    keyboard("4", "", "Nobody called me back.", "", "5")

    _, out = run(capsys, deps)

    assert UNEXPECTED in out
    assert list((workdirs / "data" / "help").glob("*.json")) == []


# --- AC-9.2 / AC-9.3: end of input and Ctrl+C ------------------------------------------------

PROMPTS = {
    "at the menu": [],
    "at a claim-number prompt": ["2"],
    "mid-narrative": ["1", "Hail dented"],
}


@pytest.mark.parametrize("where", PROMPTS)
def test_ac_9_2_end_of_input_at_any_prompt_says_goodbye_and_exits_0(
    where, keyboard, sample_deps, capsys
):
    keyboard(*PROMPTS[where])  # the script simply runs out

    code, out = run(capsys, sample_deps)

    assert code == 0
    assert out.rstrip().endswith(GOODBYE)
    assert UNEXPECTED not in out


@pytest.mark.parametrize("where", PROMPTS)
def test_ac_9_3_ctrl_c_at_a_prompt_prints_stopped_and_exits_130(
    where, keyboard, sample_deps, capsys
):
    keyboard(*PROMPTS[where], CTRL_C)

    code, out = run(capsys, sample_deps)

    assert code == 130
    assert out.rstrip().endswith(STOPPED)


def test_ac_9_3_ctrl_c_during_filing_leaves_no_claim_file(keyboard, workdirs, fixed_now, capsys):
    model = answers_then(
        NO_SUGGESTIONS, assessment_output(), risk_output(), fail_with=KeyboardInterrupt()
    )
    before = snapshot(workdirs)
    keyboard("1", NARRATIVE, "")

    code, out = run(capsys, make_deps(workdirs, fixed_now, model))

    assert code == 130
    assert STOPPED in out
    assert new_files(before, workdirs, "data/claims") == []


def test_ac_9_3_ctrl_c_during_help_releases_the_reference(
    keyboard, sample_deps, workdirs, fixed_now, capsys
):
    triage = triage_output(categories=[RequestCategory.SERVICE_DELAY])
    model = answers_then(NO_SUGGESTIONS, triage, fail_with=KeyboardInterrupt())
    keyboard("4", "", "Nobody called me back.", "")

    code, _ = run(capsys, make_deps(workdirs, fixed_now, model))

    assert code == 130
    assert list((workdirs / "data" / "help").glob("*.json")) == []


# --- AC-9.4: nothing technical ever reaches the customer -----------------------------------


@pytest.mark.parametrize(
    "scenario", ["bug_in_filing", "bug_in_status", "end_of_input", "ctrl_c", "ctrl_c_in_help"]
)
def test_ac_9_4_no_failure_output_contains_technical_detail(
    scenario, keyboard, sample_deps, workdirs, fixed_now, monkeypatch, capsys
):
    deps = sample_deps
    if scenario == "bug_in_filing":
        monkeypatch.setattr(cli, "file_claim", broken)
        keyboard("1", NARRATIVE, "", "5")
    elif scenario == "bug_in_status":
        monkeypatch.setattr(cli, "check_status", broken)
        keyboard("2", "CLM-2026-0005", "5")
    elif scenario == "end_of_input":
        keyboard("1", "Hail dented")
    elif scenario == "ctrl_c":
        keyboard("2", CTRL_C)
    else:
        triage = triage_output(categories=[RequestCategory.SERVICE_DELAY])
        opening = HelpReplyLlmOutput(opening_line="Sorry.")
        deps = make_deps(
            workdirs,
            fixed_now,
            answers_then(NO_SUGGESTIONS, triage, opening, fail_with=KeyboardInterrupt()),
        )
        keyboard("4", "", "Nobody called me back.", "")

    _, out = run(capsys, deps)

    for detail in (
        "Traceback",
        "ZeroDivisionError",
        "KeyboardInterrupt",
        "EOFError",
        "deepseek",
        "openrouter",
        ".py",
        "\\",
    ):
        assert detail not in out
