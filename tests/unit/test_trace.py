"""US10: rendering the staff trace block (pure formatting, with a privacy gate)."""

from claim_intake.contracts import TraceEntry
from claim_intake.reporting import render_trace


def entry(step: str, **values: str) -> TraceEntry:
    return TraceEntry(step=step, values=values)


def test_ac_10_1_render_trace_matches_block_format():
    entries = [
        entry("intake", pii_removed="PERSON, PHONE", manual_review="no"),
        entry("risk", risk="HIGH", teams="CLAIMS_ADJUSTER", follow_up_by="2026-09-25"),
        entry("saved", claim="CLM-2026-0007", status="ESCALATED"),
    ]

    assert render_trace(entries) == (
        "  ┌ trace ─ intake ───────────────────────────────\n"
        "  │ pii_removed: PERSON, PHONE  manual_review: no\n"
        "  ├ trace ─ risk ─────────────────────────────────\n"
        "  │ risk: HIGH  teams: CLAIMS_ADJUSTER  follow_up_by: 2026-09-25\n"
        "  └ trace ─ saved ────────────────────────────────\n"
        "    claim: CLM-2026-0007  status: ESCALATED"
    )


def test_ac_10_1_long_value_lines_wrap_at_100_characters():
    many = ", ".join(f"INDICATOR_NUMBER_{n}" for n in range(8))

    block = render_trace([entry("risk", indicators=many, risk="HIGH")])

    assert all(len(line) <= 100 for line in block.splitlines())
    assert "risk: HIGH" in block


def test_ac_10_3_failed_entry_shows_step_and_error_category():
    block = render_trace([entry("failed", step="ASSESSMENT", error_category="ModelHTTPError")])

    assert "trace ─ failed" in block
    assert "step: ASSESSMENT  error_category: ModelHTTPError" in block


def test_ac_10_4_trace_is_withheld_when_privacy_check_fails():
    block = render_trace([entry("intake", pii_removed="555-201-3344")])

    assert block == "  (trace withheld: privacy check)"
