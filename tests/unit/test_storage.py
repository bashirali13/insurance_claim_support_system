"""US5: claim numbers, atomic claim records, and report files (FR-028, FR-029; research R9)."""

from datetime import date, datetime

from claim_intake.contracts import (
    ClaimRecord,
    ClaimStatus,
    HelpRecord,
    HistoryEntry,
    InternalReport,
    RequestCategory,
    Sentiment,
    Team,
    TeamPromise,
)
from claim_intake.storage import ClaimStore, HelpStore, ReportWriter
from tests.builders import claim_assessment

FILED_AT = datetime(2026, 9, 24, 10, 15)


def record(claim_id: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        status=ClaimStatus.SUBMITTED,
        filed_at=FILED_AT,
        assessment=claim_assessment(),
        teams=[Team.CLAIMS_ADJUSTER],
        follow_up_date=date(2026, 9, 28),
        history=[HistoryEntry(at=FILED_AT, event="FILED")],
    )


def test_ac_5_4_claim_numbers_are_sequential_per_year_and_unique_across_restarts(workdirs):
    store = ClaimStore(workdirs)
    first, second = store.reserve_claim_id(2026), store.reserve_claim_id(2026)

    after_restart = ClaimStore(workdirs).reserve_claim_id(2026)

    assert (first, second, after_restart) == ("CLM-2026-0001", "CLM-2026-0002", "CLM-2026-0003")


def test_ac_5_4_record_is_written_atomically_as_json(workdirs):
    store = ClaimStore(workdirs)
    claim_id = store.reserve_claim_id(2026)

    store.save(record(claim_id))

    assert store.load(claim_id) == record(claim_id)
    assert list((workdirs / "data" / "claims").glob("*.tmp")) == []


def test_ac_5_4_released_claim_id_leaves_no_file(workdirs):
    store = ClaimStore(workdirs)
    claim_id = store.reserve_claim_id(2026)

    store.release(claim_id)

    assert not (workdirs / "data" / "claims" / f"{claim_id}.json").exists()


def test_ac_5_4_report_file_named_claim_id_and_timestamp(workdirs):
    writer = ReportWriter(workdirs)

    filed = writer.write(InternalReport(markdown="# Report"), "CLM-2026-0007", FILED_AT)
    unfiled = writer.write(InternalReport(markdown="# Report"), None, FILED_AT)

    assert filed.name == "CLM-2026-0007_20260924T101500.md"
    assert unfiled.name == "UNFILED_20260924T101500.md"
    assert filed.read_text(encoding="utf-8") == "# Report"


# --- US8: help references and records --------------------------------------------------------


def test_ac_8_1_help_references_sequential_and_unique_across_restarts(workdirs):
    first = HelpStore(workdirs).reserve_help_id(2026)

    after_restart = HelpStore(workdirs).reserve_help_id(2026)

    assert (first, after_restart) == ("HELP-2026-0001", "HELP-2026-0002")


def test_ac_8_9_help_record_round_trips(workdirs):
    store = HelpStore(workdirs)
    help_id = store.reserve_help_id(2026)
    record = HelpRecord(
        help_id=help_id,
        claim_id="CLM-2026-0005",
        filed_at=FILED_AT,
        sentiment=Sentiment.FRUSTRATED,
        categories=[RequestCategory.SERVICE_DELAY],
        routed=[
            TeamPromise(
                team=Team.CUSTOMER_RELATIONS, business_days=2, follow_up_date=date(2026, 9, 28)
            )
        ],
        history=[HistoryEntry(at=FILED_AT, event="HELP_REQUESTED")],
    )

    store.save(record)

    assert store.load(help_id) == record
    assert (workdirs / "data" / "help" / f"{help_id}.json").exists()
