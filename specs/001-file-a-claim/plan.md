# Implementation Plan: File a New Claim

**Branch**: `001-file-a-claim` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-file-a-claim/spec.md` (approved, 5 clarifications)

## Summary

Deliver the "File a new claim" menu option end to end. A customer's free-text narrative passes
through four agents coordinated by an orchestrator:

1. **Intake & PII:** regex scrub → model-suggested spans applied only if verbatim → re-scan
2. **Claim Assessment:** model classifies and extracts facts → rules add missing information and
   coverage lines
3. **Sentiment & Risk:** model reads sentiment and two flags → rules add indicators, risk level,
   teams, and a business-day follow-up date
4. **Claim Summary:** model writes the opening line, bullets, and staff summary → templates render
   the customer reply and internal report

Everything passes a final privacy guard before a protected claim record, a report, and text-free
event-log lines are written. Each agent returns a **narrow LLM output model**, and deterministic
code builds the full contract (research R3), so every safety decision is plain, testable code.

## Technical Context

**Language/Version**: Python 3.13 (managed with `uv`)

**Primary Dependencies**: `pydantic` 2.13, `pydantic-ai-slim[openai]` 2.49 (`OpenRouterModel`,
`OpenRouterProvider`, `FunctionModel`/`TestModel`), `python-dotenv`. Dev: `pytest`, `ruff`.

**Storage**: local filesystem only: `data/claims/*.json`, `output/*.md`, `logs/events.log`

**Testing**: pytest. Model calls are blocked by default (`ALLOW_MODEL_REQUESTS = False`), and
agents are driven by `FunctionModel`. `@pytest.mark.live` tests use the real model.

**Target Platform**: a local terminal on Windows, macOS, or Linux

**Project Type**: single-project CLI application with a UI-agnostic core

**Performance Goals**: processing typically under 60 seconds per claim (SC-004), at 4 model calls
per claim with a 30-second timeout each

**Constraints**:
- no PII in any stored, logged, or displayed output
- narrative ≤ 5,000 characters
- at most 2 retries per model failure
- temperature 0
- the core never prints

**Scale/Scope**: one customer per session. Claim volumes are small, in the hundreds of files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|---|---|---|---|
| I. Spec-Driven | Approved spec with AC IDs exists before code | ✅ spec approved, 46 ACs | ✅ design artifacts trace to FR and AC IDs |
| II. Test-First, AC-driven | Every test names an AC, and code exists only for tests; no network in unit tests | ✅ planned | ✅ `FunctionModel` + request blocking (R4); SC-007 collection check in quickstart |
| III. Privacy by Construction | Layered PII; separate raw and sanitized types; no map leaves intake; guard on all outputs | ✅ | ✅ `RawSubmission` vs `SanitizedSubmission`; guard covers reply, report, record, and log (R5, R6, R11) |
| IV. Typed Agent Contracts | 4 agents + orchestrator; frozen and `extra="forbid"`; enums; validated handoffs | ✅ | ✅ `data-model.md`, `contracts/agents.md` |
| V. Deterministic Safety | Rules own validation, checklist, risk, routing, and dates; sentiment ≠ risk; text is data | ✅ | ✅ narrow LLM output models (R3); phrase check + delimiters (R7); output validator (R8) |
| VI. Human-in-the-Loop | No fault, coverage, approval, or payment statements; escalate when uncertain | ✅ | ✅ forbidden-term validator (R8); report notice; privacy review path |
| VII. Simplicity | Linear flow; shallow tree; no extra frameworks or DB | ✅ | ✅ standard-library CLI and templates; files only; no Presidio, Jinja, or TUI library |
| Tech constraints | Python/uv/PydanticAI/OpenRouter via `.env`; statuses as listed | ✅ | ✅ R1, R13; `ProcessingStatus` matches the constitution |

**Result: PASS.** No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-file-a-claim/
├── spec.md              # approved specification
├── plan.md              # this file
├── research.md          # Phase 0 decisions (R1–R14)
├── data-model.md        # contracts, enums, rule tables
├── quickstart.md        # validation run guide
├── contracts/
│   ├── cli.md           # terminal texts and flows
│   ├── agents.md        # pipeline, boundaries, model instructions
│   └── files.md         # claim record, report, event log formats
├── checklists/requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/claim_intake/
├── __init__.py
├── cli.py                  # menu, input loop, printing (only module that prints)
├── config.py               # load_settings(): .env → Settings; ConfigError
├── contracts.py            # all enums and frozen Pydantic models (data-model.md)
├── pii.py                  # detectors, placeholders, apply_suggestions, find_pii (no model)
├── rules.py                # checklist, coverage lines, indicators, risk level, teams, follow-up, status
├── dates.py                # add_business_days
├── agents/
│   ├── __init__.py         # Agents dataclass + create_agents(model)
│   ├── intake.py           # scrub(): regex → suggestions → apply → re-scan
│   ├── assessment.py       # assess(): LLM output + rules → ClaimAssessment
│   ├── risk.py             # evaluate(): LLM output + rules → RiskAssessment
│   └── summary.py          # compose(): LLM output (validated) + templates → reply, report
├── orchestration.py        # file_claim(raw_text, deps, on_progress) → TaskResult
├── reporting.py            # reply/report templates, customer wording tables, status-only report
└── storage.py              # ClaimStore (claim numbers, atomic JSON), ReportWriter, EventLog

tests/
├── conftest.py             # blocks model requests; fixed clock; tmp data dirs; FunctionModel helpers
├── fixtures/
│   └── narratives/         # pii_cases.json, incident_cases.json (fictional)
├── unit/
│   ├── test_pii.py              # US1 (AC-1.x)
│   ├── test_intake.py           # US1 (AC-1.3, 1.4, 1.7, 1.8)
│   ├── test_assessment.py       # US2 (AC-2.x)
│   ├── test_rules.py            # US2/US3 rule tables (AC-2.6, 2.8, 3.2–3.6, 3.8)
│   ├── test_risk.py             # US3 (AC-3.1, 3.7, 3.9)
│   ├── test_summary.py          # US4 (AC-4.x)
│   └── test_storage.py          # FR-028/029/033 via AC-5.4
├── integration/
│   ├── test_file_claim.py       # orchestrator end-to-end with FunctionModel (AC-5.3–5.11)
│   └── test_cli.py              # scripted stdin menu flows (AC-5.1, 5.2, 5.5–5.7, 5.12)
└── live/
    └── test_live_eval.py        # @live: SC-001, SC-002, real structured output
```

**Structure Decision**: a single package with flat modules for pure logic (`pii`, `rules`,
`dates`, `contracts`, `reporting`, `storage`) and an `agents/` package holding the four model-backed
agents. This keeps the tree shallow (Principle VII) while matching the one-module-per-agent mental
model. Contracts live in one module because they form a single vocabulary shared by every step.
`cli.py` is the only adapter; a future local web UI would be a sibling adapter calling
`orchestration.file_claim`.

## Implementation Order (for /speckit-tasks)

Follows the spec's story priorities. Each step is Red → Green → Refactor.

1. **Foundation:** `conftest.py` (request blocking, fixed clock, tmp dirs); `contracts.py` grows
   only as tests need types.
2. **US1:** `pii.py` (pure regex) → `agents/intake.py` (suggestions + re-scan).
3. **US2:** `rules.missing_information`, `rules.coverage_lines` → `agents/assessment.py`.
4. **US3:** `dates.py` → `rules` (indicators, level, teams, follow-up) → `agents/risk.py`.
5. **US4:** `reporting.py` templates → `agents/summary.py` with the output validator → privacy guard.
6. **US5:** `storage.py` → `orchestration.py` → `config.py` → `cli.py` → rename the entry point.
7. **Live evaluation:** fixtures and `@live` tests for SC-001 and SC-002 (the R2 fallback is
   decided here).

## Documentation Sync

- `docs/user-experience.md` §4 is updated to match the spec: the hit-and-run + injury example is
  `HIGH` risk and `ESCALATED` (two indicators), not `MEDIUM`.
- `CLAUDE.md` Commands gains `uv run claim-support` when the CLI lands (US5).

## Complexity Tracking

No constitution violations to justify.
