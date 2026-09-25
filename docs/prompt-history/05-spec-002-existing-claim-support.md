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
