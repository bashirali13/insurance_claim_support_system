"""Live evaluation against the real model through OpenRouter (SC-001, SC-002; research R2).

Deselected by default. Run with:  uv run pytest -m live -s
Needs OPENROUTER_API_KEY and MODEL_NAME in .env. All narratives are fictional.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pydantic_ai import models

from claim_intake.agents import create_agents
from claim_intake.agents.assessment import assess, update
from claim_intake.agents.intake import scrub
from claim_intake.agents.risk import triage
from claim_intake.config import build_model, load_settings
from claim_intake.contracts import ClaimRecord, ProcessingStatus, RawSubmission
from claim_intake.orchestration import Deps, file_claim
from claim_intake.rules import diff_facts
from claim_intake.storage import SAMPLES_DIR, ClaimStore, EventLog, ReportWriter

pytestmark = pytest.mark.live

FIXTURES = Path(__file__).parents[1] / "fixtures" / "narratives"


def load_cases(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def agents():
    load_dotenv()
    models.ALLOW_MODEL_REQUESTS = True
    yield create_agents(build_model(load_settings(os.environ)))
    models.ALLOW_MODEL_REQUESTS = False


def test_sc_001_pattern_detectable_and_named_pii_never_survives(agents):
    leaks, watch_misses, watch_total = [], [], 0
    for case in load_cases("pii_cases.json"):
        text = scrub(RawSubmission(text=case["text"]), agents).text
        survived = [value for value in case["must_not_contain"] if value in text]
        if case["watch"]:
            watch_total += 1
            watch_misses += [(case["id"], value) for value in survived]
        elif survived:
            leaks.append((case["id"], survived, text))

    print(f"\nWatch item (bare plates): {len(watch_misses)} missed of {watch_total} cases")
    for miss in watch_misses:
        print(f"  missed {miss}")
    assert leaks == []


def test_sc_002_incident_type_accuracy_is_at_least_90_percent(agents):
    cases = load_cases("incident_cases.json")
    wrong = []
    for case in cases:
        submission = scrub(RawSubmission(text=case["text"]), agents)
        got = assess(submission, agents).incident_type
        if got != case["expected"]:
            wrong.append((case["id"], case["expected"], str(got)))

    accuracy = 1 - len(wrong) / len(cases)
    print(f"\nIncident accuracy: {accuracy:.0%} ({len(cases) - len(wrong)}/{len(cases)})")
    for miss in wrong:
        print(f"  {miss}")
    assert accuracy >= 0.9


def test_all_four_agents_return_valid_structured_output_end_to_end(agents, tmp_path):
    deps = Deps(
        agents=agents,
        store=ClaimStore(tmp_path),
        reports=ReportWriter(tmp_path),
        events=EventLog(tmp_path),
        now=datetime.now,
    )
    s10 = load_cases("pii_cases.json")[0]["text"]

    result = file_claim(s10, deps)

    print(f"\nStatus: {result.processing_status}\n{result.customer_message}")
    assert result.processing_status in {
        ProcessingStatus.COMPLETED,
        ProcessingStatus.MANUAL_REVIEW_REQUIRED,
    }


# --- Phase 002: update mode and help triage (SC-203, SC-204) ---------------------------------


def test_sc_203_update_mode_reflects_the_stated_change_at_least_90_percent(agents):
    saved = ClaimRecord.model_validate_json(
        (SAMPLES_DIR / "CLM-2026-0005.json").read_text(encoding="utf-8")
    ).assessment
    cases = load_cases("update_cases.json")
    wrong = []
    for case in cases:
        submission = scrub(RawSubmission(text=case["text"]), agents)
        proposed = update(submission, saved, agents)
        changes = diff_facts(saved, proposed.updated)
        changed = {c.field for c in [*changes.added, *changes.corrected, *changes.sensitive]}
        if changed != set(case["changed"]) or proposed.contact_change_requested != case["contact"]:
            wrong.append((case["id"], sorted(changed), proposed.contact_change_requested))

    accuracy = 1 - len(wrong) / len(cases)
    print(f"\nUpdate-mode accuracy: {accuracy:.0%} ({len(cases) - len(wrong)}/{len(cases)})")
    for miss in wrong:
        print(f"  {miss}")
    assert accuracy >= 0.9


def test_sc_204_help_triage_assigns_expected_category_at_least_90_percent(agents):
    cases = load_cases("help_cases.json")
    wrong = []
    for case in cases:
        submission = scrub(RawSubmission(text=case["text"]), agents)
        categories = [str(c) for c in triage(submission, agents).categories]
        if case["expected"] not in categories:
            wrong.append((case["id"], case["expected"], categories))

    accuracy = 1 - len(wrong) / len(cases)
    print(f"\nHelp triage accuracy: {accuracy:.0%} ({len(cases) - len(wrong)}/{len(cases)})")
    for miss in wrong:
        print(f"  {miss}")
    assert accuracy >= 0.9
