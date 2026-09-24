# 04 — Implementing Phase 001: File a New Claim

**Date:** 2026-09-24
**Phase:** 001-file-a-claim (`/speckit-implement`, T001–T040)
**Result:** US1–US5 built test-first. 174 deterministic tests, 48 of 48 acceptance criteria covered,
live evaluation passed.

## Objective

Build the "File a new claim" option end to end with strict Red → Green → Refactor, where every test
names the acceptance criterion it proves, and validate it against the real model.

## Key Prompts (condensed)

1. `/speckit-implement`, with a pause after US1 to review the tests and code.
2. *"We should also have a document of end-goal prompts we'd expect from a user. Good for testing."*
3. *"Agree on theft/damage. Accept billing-type requests for this phase and let a later phase
   handle them."*
4. *"As long as there's no issues, feel free to continue."*

## How the Work Was Done

- **One commit rhythm per story:** `test:` (Red, with the failure reason confirmed, always a
  missing module or type, never a typo) → `feat:` (Green) → `refactor:`.
- **Scripted models for unit tests:** a `FunctionModel` answers each agent with fixed structured
  output, and real model calls are blocked in tests.
- **Small builders:** `tests/builders.py` means each test states only the facts it cares about.
- **Checkpoints:** the story checkpoints ran green at 27 → 74 → 108 → 136 → 174 tests.

## Decisions and Changes Made During Implementation

| Topic | Decision | Why |
|---|---|---|
| Scenario catalog | New `docs/customer-scenarios.md`: 30 phase-001 scenarios with rule-derived outcomes, plus 12 phase-002 drafts | The user asked for realistic end-goal inputs; it seeds the live fixtures and walkthroughs |
| Thefts | No "description of damage" for `THEFT` (FR-013, AC-2.6) | Found while deriving S03/S04; "describe the damage" reads oddly for a stolen car |
| Non-claims via option 1 | Accepted as `UNKNOWN` in phase 001; phase 002 "Get help" redirects them | User decision (S28) |
| Injury contradictions | `Contradiction.about_injury` flag (model-judged) | Code needed to know *which* contradictions affect injury for the 1-day rule |
| Indicator derivation | AC-3.4 extended so each fact-based indicator has an AC | Found while writing US3 tests; only `INJURY_REPORTED` had one |
| Plate context word | "tag" dropped from the plate context words | "price tag 20" would have been scrubbed as a plate |
| Reply wording | "We're sorry to hear someone was hurt." and "If anyone's symptoms get worse…" | The injured person may be a passenger, not "you" |
| Library banner | `PYDANTIC_AI_NO_BANNER=1` set in the CLI and tests | PydanticAI prints a banner on first run, which would leak into the customer terminal |
| Ruff | `src` layout and first-party packages configured | Import sorting treated our own package as third-party |

## Live Evaluation (DeepSeek V4 Flash via OpenRouter)

| Check | Result |
|---|---|
| SC-001 PII (20 cases) | **0 leaks** |
| SC-002 incident type (21 cases) | **100%** (target ≥ 90%) |
| Structured output (research R2 risk) | Tool-call output works for all four agents; the `PromptedOutput` fallback isn't needed |
| Watch item: bare license plates | **2 of 3 missed** at first. After adding plate guidance to the intake instructions, **0 of 3** |
| SC-004 processing time (5-claim CLI walkthrough) | **median 29.7 s** (max 53.8 s; target < 60 s typical) |

**Care taken on the plate fix:** the first draft of the new instructions used the exact evaluation
values as examples, which would have contaminated the test. It was caught and replaced with values
that appear in no fixture.

## Pushbacks and Corrections

- **Catalog expectation vs. system (S21):** the live run tagged PIP/MedPay on the contradicted-injury
  claim. The system followed the approved coverage rule correctly; the catalog expectation was too
  narrow, so the doc was corrected rather than the code.
- **Self-caught slips:** a leftover draft test with a `del` hack, a stray `"""` in the intake
  instructions, and the evaluation-leakage issue above. All were fixed before commit.
- **No refactor for its own sake:** T021, T026, and T035 recorded "no changes needed" rather than
  making cosmetic edits.

## Known Limitations Carried Forward

- **"Choose option 3 anytime to add these details."** is shown while option 3 is still "coming
  soon". Phase 002 enables it.
- **FR-030 wording** says every failure writes a status-only report, but rejected input (empty or
  too long) only re-prompts. No AC requires a report for a re-prompt, so none is written. Clarify
  the FR wording in phase 002 or 003.
- **Unexpected programming errors** (non-model, non-I/O) would still surface as a traceback. The
  hardening phase (003) should add a last-resort safe message, with an AC.
- **Live evaluation takes about 12 minutes** for the full set. It's opt-in (`-m live`) and not part
  of the default suite.

## Next

Push `001-file-a-claim`, open the phase PR, present the phase-completion check, and merge only
after the user confirms. Then `/speckit-specify` for **002-existing-claim-support** (check status,
add or correct details, get help), seeded by scenarios E01–E12.
