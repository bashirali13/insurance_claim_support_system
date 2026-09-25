# 05 — Phase 001 Merge and Spec 002: Existing-Claim Support

**Date:** 2026-09-25
**Phase:** 001 merged → 002-existing-claim-support (specify → clarify → approved)
**Artifacts:** `specs/002-existing-claim-support/spec.md`, `checklists/requirements.md`

## Objective

Close phase 001 and specify menu options 2–4 (check status, add or correct details, get help)
with no remaining ambiguity.

## Key Prompts (condensed)

1. *"Give me a very high-level update, what's left, and next steps."*
2. *"Merge phase 001 to main. Begin speckit-specify on phase 2. Address anything that needs
   clarifying so there is no ambiguity."*
3. Five clarify answers: B, A, A, A, B.
4. *"Spec approved."*

## What Happened

- **Phase 001 merged:** PR #2 was merged with a merge commit after the user confirmed the
  completion check. `main` is green (174 tests).
- **Phase 002 branch:** `002-existing-claim-support`, created from `main`.
- **Continued numbering:** stories continue from phase 001 as **US6–US8**, with criteria
  **AC-6.x–AC-8.x**, so test names like `test_ac_6_1_…` never collide with phase 001's.
- **Four decisions left open on purpose:** the draft spec left four customer-visible decisions as
  "see Clarifications" rather than guessing. A fifth was found during the clarify scan.

## Claude's Key Recommendations

- **Status checks are fully deterministic:** no model call and no file changes. Claim numbers are
  normalized (case and spacing), with a format hint and a "not found" message that never reveals
  whether other claims exist.
- **Update mode diffs in code:** the model returns the full updated facts, and **code** compares
  them field by field to produce "Added", "Corrected", and "Sensitive" lists. The model never
  decides what changed.
- **Get help** uses the Sentiment & Risk agent in a *help mode* with seven fixed request
  categories, and a routing table owned by rules. Out-of-scope requests get a fixed redirect with
  no reference number.
- **No fifth agent:** update and help are *modes* of existing agents, which keeps the
  constitution's four-agent rule.
- **Phase 001 loose ends folded in:** FR-219 clarifies that re-prompted input writes no report
  (the old FR-030 wording), and FR-220 retires "coming soon".
- **Gap found:** `data/claims/` was not gitignored, so running the app in the repo could commit
  claim records.

## Decisions Accepted (Clarify Session 2026-09-25)

| # | Question | Decision |
|---|---|---|
| 1 | Should sensitive corrections (injury, incident type, other party, UM/UIM) apply immediately? | **No.** They're held as a *pending change* for adjuster confirmation within 1 business day. Routine changes apply immediately. |
| 2 | Can a claim in privacy review be updated? | **No.** No text is taken; the specialist will contact the customer. |
| 3 | How are sample claims loaded, and is runtime data in git? | `data/samples/` is committed. `--load-samples` copies without overwriting. `data/claims/` and `data/help/` are **gitignored**. |
| 4 | What about a bad claim number in Get help? | Same hint as option 2; **Enter continues without one**; only real claim numbers are linked. |
| 5 | After an update, do routed teams accumulate or get replaced? | **Replaced** (the user chose this over the recommended "accumulate"). |

## Pushbacks and Clarifications

- **Q5, the user chose differently from the recommendation.** Claude recommended accumulating
  teams so that a routine update could never silently drop Special Review or Customer Relations.
  The user chose *replace*. The spec records it as a **deliberate trade-off**: teams and the
  follow-up date become the latest result, but an `ESCALATED` status never de-escalates, and
  pending changes and contact changes still add their teams.
- **Q1 and Q2 favored keeping records trustworthy** over processing everything. A customer message
  can't lower a claim's risk before a human checks it.

## Deferred or Rejected Scope

- **Deferred:**
  - staff actions (confirming pending changes, removing teams, closing claims)
  - customers viewing their help requests
  - holiday-aware dates
- **Rejected:**
  - loading samples automatically at startup
  - committing runtime claim data
  - a fifth agent for help or update

## Next

`/speckit-plan` for 002: update-mode and help-mode agent contracts, the field-by-field diff,
pending changes, the help record and reference numbering, the sample data, and the event log `task`
field, all checked against the constitution.

## Amendment: Plan, Tasks, and Analyze

**Prompts (condensed):** *"Spec approved. Write 05, then plan."* → *"Looks good. Continue with
tasks."* → `/speckit-analyze` → *"Apply directly and re-run analyze."*

**Plan highlights:**
- **Code decides what changed.** The update model returns the full updated facts; a pure diff
  produces Added, Corrected, and Sensitive.
- **Modes, not new agents.** Update and help are *modes* of existing agents, which keeps the
  four-agent rule.
- **Templates for status and update replies**, with no model call.
- **Shared `CLM`/`HELP` numbering.**
- **Backward-compatible claim records.**

**Spec fixes made along the way (always spec-first):**

| When | Fix |
|---|---|
| Plan | FR-218 vs AC-6.8 conflict: status checks write no event-log line |
| Plan | New AC-8.12: the Get help privacy-review outcome was unspecified |
| Plan review | The user confirmed that *additions* to sensitive facts apply immediately; only corrections are held (AC-7.4) |
| Tasks | AC-7.8, AC-8.9, and AC-8.1 extended so the event-log `task` and help-opening validation are test-driven |
| Analyze | **CRITICAL C1:** new AC-8.13 for the Get help failure outcome (FR-217 had no customer-visible behavior) |
| Analyze | M1: SC-202 test over every field kind; M2: FR-208 replace rule applies only to applied updates (privacy path adds `PRIVACY_REVIEW`) |
| Analyze | Low-severity fixes: an FR-219 no-write assertion, a distressed + out-of-scope reply test, notes on log `claim_id`, `FactChanges`, and spec 001 AC-5.1 superseded |

**Result:** 34 ACs (AC-6.1–AC-8.13), all with named tests; 41 tasks; **0 critical issues** on
re-analysis.

**Lesson (again):** the analyze step catches behavior the design builds but the spec never states.
This time it was a failure path. Phase 001's lesson held: most gaps are *unhappy paths*.
