"""US5-US8: the terminal menu and flows (contracts/cli.md), with scripted keyboard input."""

from datetime import date

import pytest

from claim_intake import cli
from claim_intake.contracts import IntakeLlmOutput, ProcessingStatus, TaskResult, TraceEntry
from tests.builders import assessment_output, risk_output, summary_output
from tests.conftest import structured_model
from tests.integration.conftest import HEADER, make_deps, snapshot

MENU_OPTIONS = [
    " 1. File a new claim",
    " 2. Check my claim status",
    " 3. Add or correct details on my claim",
    " 4. Get help with my claim",
    " 5. Exit",
]


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


def test_ac_5_1_menu_shows_header_notice_and_five_options(keyboard, capsys):
    keyboard("5")

    _, out = run_app(capsys)

    assert HEADER in out
    assert " Your information is protected." in out
    for option in MENU_OPTIONS:
        assert option in out


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


# --- US8: option 4 ------------------------------------------------------------------------


@pytest.fixture
def helped(monkeypatch):
    """Replace get_help so CLI tests only check prompts; records (claim_id, text)."""
    calls = []

    def fake_get_help(claim_id, text, deps, on_progress=None):
        calls.append((claim_id, text))
        return TaskResult(
            processing_status=ProcessingStatus.COMPLETED,
            claim_id=claim_id,
            customer_message="(help reply)",
            report_path=None,
        )

    monkeypatch.setattr(cli, "get_help", fake_get_help)
    return calls


def test_ac_8_11_enter_continues_without_claim_number(keyboard, sample_deps, helped, capsys):
    keyboard("4", "", "Nobody called me back.", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert helped == [(None, "Nobody called me back.")]
    assert "How can we help?" in out


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ("clm 2026 5", "Claim numbers look like CLM-2026-0007. Please try again."),
        ("CLM-2026-9999", "We couldn't find that claim number. Please check it and try again."),
    ],
)
def test_ac_8_11_unknown_or_malformed_number_hint_with_skip_option(
    entry, message, keyboard, sample_deps, helped, capsys
):
    keyboard("4", entry, "CLM-2026-0005", "When will someone call?", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert f"{message}\nPress Enter to continue without one." in out
    assert helped == [("CLM-2026-0005", "When will someone call?")]


def test_ac_8_1_option_4_flow_prints_help_reply(keyboard, sample_deps, helped, capsys):
    keyboard("4", "CLM-2026-0005", "I'd like to speak to my adjuster.", "", "5")

    _, out = run_app(capsys, sample_deps)

    assert "(help reply)" in out
    assert "coming soon" not in out


# --- US10: --trace --------------------------------------------------------------------------


@pytest.fixture
def traced_filing(monkeypatch):
    """A filing result carrying one trace entry, so CLI tests only check printing."""

    def fake_file_claim(text, deps, on_progress=None):
        return TaskResult(
            processing_status=ProcessingStatus.COMPLETED,
            claim_id="CLM-2026-0001",
            customer_message="(reply)",
            report_path=None,
            trace=[TraceEntry(step="saved", values={"claim": "CLM-2026-0001"})],
        )

    monkeypatch.setattr(cli, "file_claim", fake_file_claim)


def test_ac_10_1_trace_flag_prints_block_after_reply(keyboard, traced_filing, capsys):
    keyboard("1", "Hail dented my hood.", "", "5")

    cli.safe_run(None, trace=True)

    out = capsys.readouterr().out
    assert out.index("(reply)") < out.index("└ trace ─ saved")
    assert "claim: CLM-2026-0001" in out


def test_ac_10_5_no_trace_printed_without_flag(keyboard, traced_filing, capsys):
    keyboard("1", "Hail dented my hood.", "", "5")

    cli.safe_run(None)

    assert "trace ─" not in capsys.readouterr().out


def test_ac_10_5_trace_is_never_written_to_disk(keyboard, workdirs, fixed_now, capsys):
    model = structured_model(
        IntakeLlmOutput(suggestions=[]), assessment_output(), risk_output(), summary_output()
    )
    keyboard("1", "Hail dented my hood.", "", "5")

    cli.safe_run(make_deps(workdirs, fixed_now, model), trace=True)

    assert "trace ─" in capsys.readouterr().out
    for path in workdirs.rglob("*"):
        if path.is_file():
            assert "trace ─" not in path.read_text(encoding="utf-8")
