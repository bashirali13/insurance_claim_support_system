# 06 — Implementing Phase 002: Existing-Claim Support

**Date:** 2026-09-25
**Phase:** 002-existing-claim-support (`/speckit-implement`, T001–T041)
**Result:** menu options 2–4 built test-first. 283 deterministic tests; all 34 acceptance criteria
(AC-6.1–AC-8.13) covered; live evaluation passed.

## Objective

Turn on "Check my claim status", "Add or correct details", and "Get help with my claim", reusing
phase 001's pipeline and safeguards, with every behavior driven by an acceptance-criterion test.

## Key Prompts (condensed)

1. `/speckit-implement`, continuing through the stories with pauses only for issues (the standing
   preference from phase 001).

## How the Work Went

**Checkpoints:** 175 tests after the foundation → 200 (US6) → 242 (US7) → 283 (US8). Every story
followed Red → Green → Refactor, and each Red failed for the expected reason (a missing module or
type).

**Phase 001 tests changed on purpose, never silently:**
- The AC-5.13 event-log field list gained `task`, updated test-first.
- The "coming soon" test was narrowed as each option came online, then removed.
- `cli.main` now takes `argv`, so the config test passes `[]`.

**Refactors kept behavior identical:**
- `NumberedFiles` is shared by claim and help numbering.
- `agents/validation.py` holds one text-safety check for the summary and help replies.
- The orchestration helpers are now public (`TaskRun`, `StepFailed`, …) because two modules use
  them.
- There is a single `ignore_progress`.

## Issues Found and Fixed During Implementation

| Issue | How it was found | Fix |
|---|---|---|
| A malformed `MODEL_NAME` (no `provider/` prefix) **crashed at startup with a traceback** | A smoke test with a dummy model name | Spec 001 AC-5.7 extended first, then a Red test, then `load_settings` requires `provider/model` |
| A failed **update could have deleted the customer's claim**: phase 001's failure handler released any claim number it held | Design review before US7; guarded by the AC-7.9 test | `TaskRun` releases only numbers it reserved itself |
| Shell escaping turned `"\n"` into literal line breaks in generated code (three times) | Lint and syntax errors | Switched to the Edit tool for code containing escapes. A `chr(10)` workaround was noticed and removed for consistency. |
| Import-order and helper-placement slips | ruff | Fixed before each commit |

## Live Evaluation (DeepSeek V4 Flash via OpenRouter)

| Check | Result |
|---|---|
| SC-203 update mode reflects the stated change (13 cases) | **92%** (target ≥ 90%). The one miss, U13 ("police found the other driver… no insurance"), also marked a police report as mentioned, an arguable inference; the UM/UIM correction was still correctly held as sensitive |
| SC-204 help triage (14 cases, 2 per category) | **100%** |
| SC-201 status check | **0.8 ms** (target < 1 s) |
| Real CLI walkthrough of options 2–4 | Matched the spec: added and corrected details, a held sensitive change visible in the status, a contact change never stored, closed claim refused, routed help with a reference, redirect-only, lawyer mention → adjuster next day with Special Review hidden |

## Observations Carried Forward

- A contact-change-only update writes a `DETAILS_UPDATED` history entry with no field names,
  because a contact change isn't a claim field. It's harmless, but a `detail` like "contact change
  requested" would read better. This is a candidate for phase 003.
- Teams are replaced after updates (the clarify Q5 trade-off). In the walkthrough, 0005 kept
  Claims Adjuster and gained Policy Services, and stayed `ESCALATED`. Behavior is as specified.
- The live evaluation remains opt-in (`-m live`); the phase 002 set runs in about 2 minutes.
- Still planned for phase 003: a last-resort friendly message for unexpected programming errors,
  trace mode, the adversarial suite, the architecture diagram, and the README.

## Next

Push `002-existing-claim-support`, open the phase PR, present the completion check, and merge only
after the user confirms. Then phase 003: hardening and release.
