"""US6: the committed sample claims and loading them (FR-204)."""

from claim_intake.contracts import ClaimRecord, ClaimStatus
from claim_intake.pii import find_pii
from claim_intake.storage import SAMPLES_DIR, ClaimStore, load_samples

SAMPLE_IDS = [f"CLM-2026-000{n}" for n in range(1, 7)]


def test_ac_6_9_six_samples_are_valid_claim_records_covering_every_status():
    records = [
        ClaimRecord.model_validate_json((SAMPLES_DIR / f"{cid}.json").read_text(encoding="utf-8"))
        for cid in SAMPLE_IDS
    ]

    assert [r.claim_id for r in records] == SAMPLE_IDS
    assert {r.status for r in records} == set(ClaimStatus)
    assert sum(r.assessment is None for r in records) == 1  # the privacy-review sample


def test_ac_6_9_samples_contain_no_personal_information():
    for cid in SAMPLE_IDS:
        assert find_pii((SAMPLES_DIR / f"{cid}.json").read_text(encoding="utf-8")) == [], cid


def test_ac_6_9_loading_copies_missing_samples_without_overwriting(workdirs):
    store = ClaimStore(workdirs)
    existing = store.dir / "CLM-2026-0003.json"
    existing.write_text("kept as-is", encoding="utf-8")

    loaded = load_samples(workdirs)

    assert loaded == [cid for cid in SAMPLE_IDS if cid != "CLM-2026-0003"]
    assert existing.read_text(encoding="utf-8") == "kept as-is"
    assert load_samples(workdirs) == []


def test_ac_6_9_next_claim_after_loading_is_0007(workdirs):
    load_samples(workdirs)

    assert ClaimStore(workdirs).reserve_claim_id(2026) == "CLM-2026-0007"
