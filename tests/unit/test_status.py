"""US6: claim-number handling and the status reply (contracts/cli.md option 2). No model."""

from datetime import date, datetime

import pytest

from claim_intake.contracts import ClaimRecord, ClaimStatus, PendingChange
from claim_intake.reporting import render_status
from claim_intake.rules import normalize_claim_number
from claim_intake.storage import SAMPLES_DIR

TODAY = date(2026, 9, 24)  # Thursday


def sample(claim_id: str) -> ClaimRecord:
    path = SAMPLES_DIR / f"{claim_id}.json"
    return ClaimRecord.model_validate_json(path.read_text(encoding="utf-8"))


def test_ac_6_2_claim_number_is_trimmed_and_uppercased():
    assert normalize_claim_number("  clm-2026-0005 ") == "CLM-2026-0005"


@pytest.mark.parametrize("text", ["clm 2026 5", "CLM-26-5", "CLM-2026-00051", "2026-0005", ""])
def test_ac_6_3_malformed_claim_numbers_are_rejected(text):
    assert normalize_claim_number(text) is None


def test_ac_6_1_status_block_for_hit_and_run_sample():
    record = sample("CLM-2026-0005").model_copy(
        update={
            "pending_changes": [
                PendingChange(
                    field="customer_side_injured",
                    requested_value="NO",
                    requested_at=datetime(2026, 9, 24, 9, 0),
                )
            ]
        }
    )

    assert render_status(record, TODAY) == (
        "Claim CLM-2026-0005: Collision (filed Sep 23, 2026)\n"
        "  Status:      With a specialist team for priority review\n"
        "  Last update: Sep 23, 2026 - Claim filed\n"
        "  Still needed:\n"
        "    • Police report number\n"
        "  Waiting for an adjuster to confirm:\n"
        "    • injuries to you or your passengers\n"
        "  Next step:   A claims adjuster will contact you by Friday, Sep 25."
    )


@pytest.mark.parametrize(
    ("status", "wording"),
    [
        (ClaimStatus.SUBMITTED, "Received and waiting for review"),
        (ClaimStatus.AWAITING_INFORMATION, "Waiting for information from you"),
        (ClaimStatus.UNDER_REVIEW, "Under review by a claims adjuster"),
        (ClaimStatus.ESCALATED, "With a specialist team for priority review"),
        (ClaimStatus.CLOSED, "Closed"),
    ],
)
def test_ac_6_5_status_wording(status, wording):
    record = sample("CLM-2026-0003").model_copy(update={"status": status})

    assert f"  Status:      {wording}\n" in render_status(record, TODAY)


def test_ac_6_6_privacy_review_claim_shows_no_incident_or_facts():
    text = render_status(sample("CLM-2026-0006"), TODAY)

    assert text.splitlines()[0] == "Claim CLM-2026-0006 (filed Sep 22, 2026)"
    assert "Still needed" not in text
    assert "Waiting for an adjuster" not in text
    assert "Next step:   A specialist will contact you by Friday, Sep 25." in text


def test_ac_6_7_no_follow_up_promise_when_date_passed_or_closed():
    past = render_status(sample("CLM-2026-0001"), TODAY)  # follow-up Sep 16
    closed = render_status(
        sample("CLM-2026-0003").model_copy(update={"status": ClaimStatus.CLOSED}), TODAY
    )

    assert "Next step" not in past
    assert "Next step" not in closed


def test_ac_6_7_follow_up_due_today_is_still_shown():
    text = render_status(sample("CLM-2026-0003"), TODAY)  # follow-up Sep 24

    assert "by Thursday, Sep 24." in text


def test_ac_6_1_phase_001_record_without_new_fields_still_loads():
    phase_001_json = sample("CLM-2026-0003").model_dump_json(exclude={"pending_changes"})

    record = ClaimRecord.model_validate_json(phase_001_json)

    assert record.pending_changes == []
