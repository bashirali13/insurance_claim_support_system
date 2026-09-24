"""US5: the terminal menu and filing flow (contracts/cli.md), with scripted keyboard input."""

import pytest

from claim_intake import cli
from claim_intake.contracts import ProcessingStatus, TaskResult

HEADER = " Northstar Auto Insurance: Claim Support"
MENU_OPTIONS = [
    " 1. File a new claim",
    " 2. Check my claim status",
    " 3. Add or correct details on my claim",
    " 4. Get help with my claim",
    " 5. Exit",
]


@pytest.fixture
def keyboard(monkeypatch):
    """Feed lines to input() in order; returns a setter."""

    def type_lines(*lines: str) -> None:
        queue = list(lines)
        monkeypatch.setattr("builtins.input", lambda prompt="": queue.pop(0))

    return type_lines


@pytest.fixture
def filed(monkeypatch):
    """Replace the orchestrator so CLI tests never touch agents; records the narratives sent."""
    narratives: list[str] = []

    def fake_file_claim(text, deps, on_progress=None):
        narratives.append(text)
        return TaskResult(
            processing_status=ProcessingStatus.COMPLETED,
            claim_id="CLM-2026-0001",
            customer_message="(reply)",
            report_path=None,
        )

    monkeypatch.setattr(cli, "file_claim", fake_file_claim)
    return narratives


def run_app(capsys) -> tuple[int, str]:
    code = cli.run(deps=None)
    return code, capsys.readouterr().out


def test_ac_5_1_menu_shows_header_notice_and_five_options(keyboard, capsys):
    keyboard("5")

    _, out = run_app(capsys)

    assert HEADER in out
    assert " Your information is protected." in out
    for option in MENU_OPTIONS:
        assert option in out


@pytest.mark.parametrize("choice", ["2", "3", "4"])
def test_ac_5_1_options_2_to_4_say_coming_soon(choice, keyboard, capsys):
    keyboard(choice, "5")

    _, out = run_app(capsys)

    assert "This option is coming soon." in out
    assert out.count(HEADER) == 2


def test_ac_5_1_invalid_choice_shows_hint_and_menu_again(keyboard, capsys):
    keyboard("9", "5")

    _, out = run_app(capsys)

    assert out.count("Please choose a number from 1 to 5.") == 1
    assert out.count(HEADER) == 2


def test_ac_5_2_multiline_input_ends_on_empty_line(keyboard, filed, capsys):
    keyboard("1", "I was rear-ended on Main St.", "My bumper is dented.", "", "5")

    run_app(capsys)

    assert filed == ["I was rear-ended on Main St.\nMy bumper is dented."]


def test_ac_5_5_whitespace_only_input_reprompts(keyboard, filed, capsys):
    keyboard("1", "   ", "Hail dented my hood.", "", "5")

    _, out = run_app(capsys)

    assert "Please describe what happened, then press Enter on an empty line." in out
    assert filed == ["Hail dented my hood."]


def test_ac_5_6_input_over_5000_chars_reprompts_with_limit_message(keyboard, filed, capsys):
    too_long = "a" * 5001
    just_right = "   " + "b" * 5000 + "   "
    keyboard("1", too_long, "", just_right, "", "5")

    _, out = run_app(capsys)

    assert (
        "That's longer than we can accept here (limit 5,000 characters). Please shorten it." in out
    )
    assert filed == ["b" * 5000]


def test_ac_5_7_missing_config_exits_1_without_menu(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)

    code = cli.main()

    out = capsys.readouterr().out
    assert code == 1
    assert "Setup needed: OPENROUTER_API_KEY and MODEL_NAME must be set in .env" in out
    assert HEADER not in out


def test_ac_5_12_exit_says_goodbye_and_exits_0(keyboard, capsys):
    keyboard("5")

    code, out = run_app(capsys)

    assert code == 0
    assert "Thank you for contacting Northstar Auto Insurance. Goodbye." in out
