"""US5-US8: the terminal menu and flows (contracts/cli.md), with scripted keyboard input."""

from datetime import date

import pytest

from claim_intake import cli
from claim_intake.agents import create_agents
from claim_intake.contracts import ProcessingStatus, TaskResult
from claim_intake.orchestration import Deps
from claim_intake.storage import ClaimStore, EventLog, ReportWriter, load_samples
from tests.conftest import failing_model

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


def run_app(capsys, deps=None) -> tuple[int, str]:
    code = cli.run(deps=deps)
    return code, capsys.readouterr().out


@pytest.fixture
def sample_deps(workdirs, fixed_now):
    """Sample claims loaded into a temp folder; any model call would fail loudly."""
    load_samples(workdirs)
    return Deps(
        agents=create_agents(failing_model(AssertionError("no model call expected"))),
        store=ClaimStore(workdirs),
        reports=ReportWriter(workdirs),
        events=EventLog(workdirs),
        now=lambda: fixed_now,
    )


def snapshot(root) -> dict:
    return {p: p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_ac_5_1_menu_shows_header_notice_and_five_options(keyboard, capsys):
    keyboard("5")

    _, out = run_app(capsys)

    assert HEADER in out
    assert " Your information is protected." in out
    for option in MENU_OPTIONS:
        assert option in out


def test_ac_5_1_option_4_says_coming_soon(keyboard, capsys):
    keyboard("4", "5")

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

    code = cli.main([])

    out = capsys.readouterr().out
    assert code == 1
    assert "Setup needed: OPENROUTER_API_KEY and MODEL_NAME must be set in .env" in out
    assert HEADER not in out


def test_ac_5_12_exit_says_goodbye_and_exits_0(keyboard, capsys):
    keyboard("5")

    code, out = run_app(capsys)

    assert code == 0
    assert "Thank you for contacting Northstar Auto Insurance. Goodbye." in out


# --- US6: option 2 and sample claims ------------------------------------------------------


def test_ac_6_1_option_2_prints_status_for_sample_claim(keyboard, sample_deps, capsys):
    keyboard("2", "clm-2026-0005", "5")

    _, out = run_app(capsys, sample_deps)

    assert "Claim CLM-2026-0005: Collision (filed Sep 23, 2026)" in out
    assert "Next step:   A claims adjuster will contact you by Friday, Sep 25." in out


def test_ac_6_3_malformed_number_hint_then_empty_returns_to_menu(
    keyboard, sample_deps, workdirs, capsys
):
    before = snapshot(workdirs)
    keyboard("2", "clm 2026 5", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert "Claim numbers look like CLM-2026-0007. Please try again." in out
    assert out.count(HEADER) == 2
    assert snapshot(workdirs) == before  # FR-219: no report or event-log line


def test_ac_6_4_unknown_claim_number_message(keyboard, sample_deps, capsys):
    keyboard("2", "CLM-2026-9999", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert "We couldn't find that claim number. Please check it and try again." in out


def test_ac_6_8_status_check_calls_no_model_and_writes_nothing(
    keyboard, sample_deps, workdirs, capsys
):
    before = snapshot(workdirs)
    keyboard("2", "CLM-2026-0002", "5")

    run_app(capsys, sample_deps)

    assert snapshot(workdirs) == before


def test_ac_6_9_load_samples_flag_reports_count_then_shows_menu(
    keyboard, workdirs, monkeypatch, capsys
):
    monkeypatch.chdir(workdirs)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("MODEL_NAME", "test/model")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    keyboard("5")

    code = cli.main(["--load-samples"])

    out = capsys.readouterr().out
    assert code == 0
    assert out.index("Loaded 6 sample claims.") < out.index(HEADER)


# --- US7: option 3 ------------------------------------------------------------------------


def test_ac_7_7_closed_claim_update_is_refused_without_asking_for_text(
    keyboard, sample_deps, capsys
):
    keyboard("3", "CLM-2026-0004", "5")  # no narrative lines supplied: none may be requested

    _, out = run_app(capsys, sample_deps)

    assert (
        "This claim is closed. If you need help with it, choose option 4 "
        "(Get help with my claim)." in out
    )
    assert "What would you like to add or correct?" not in out


@pytest.mark.parametrize(
    ("follow_up", "expected"),
    [
        ("2026-09-25", "They'll contact you by Friday, Sep 25"),
        ("2026-09-01", "They'll contact you soon"),
    ],
)
def test_ac_7_12_privacy_review_claim_update_is_refused(
    follow_up, expected, keyboard, sample_deps, capsys
):
    record = sample_deps.store.load("CLM-2026-0006")
    sample_deps.store.save(
        record.model_copy(update={"follow_up_date": date.fromisoformat(follow_up)})
    )
    keyboard("3", "CLM-2026-0006", "5")

    _, out = run_app(capsys, sample_deps)

    assert "This claim is with a specialist for a privacy review." in out
    assert f"{expected}, and you can share any updates with them then." in out
    assert "What would you like to add or correct?" not in out


def test_ac_7_1_option_3_flow_prints_update_reply(keyboard, sample_deps, monkeypatch, capsys):
    sent = []

    def fake_update_claim(claim_id, text, deps, on_progress=None):
        sent.append((claim_id, text))
        return TaskResult(
            processing_status=ProcessingStatus.COMPLETED,
            claim_id=claim_id,
            customer_message="(update reply)",
            report_path=None,
        )

    monkeypatch.setattr(cli, "update_claim", fake_update_claim)
    keyboard("3", "CLM-2026-0005", "The police report number is 26-44817.", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert sent == [("CLM-2026-0005", "The police report number is 26-44817.")]
    assert "What would you like to add or correct?" in out
    assert "(update reply)" in out
