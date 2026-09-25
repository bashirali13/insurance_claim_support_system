# 07 — Phase 002 Merge and Spec 003: Hardening and Release

**Date:** 2026-09-25
**Phase:** 002 merged → 003-hardening-and-release (specify → clarify → approved) + constitution
v1.1.0
**Artifacts:** `specs/003-hardening-and-release/spec.md`, `checklists/requirements.md`,
`.specify/memory/constitution.md`

## Objective

Close phase 002 and specify the final phase: no raw errors ever, a staff trace mode, an end-to-end
adversarial suite, and release documentation (README, architecture diagram, sample outputs).

## Key Prompts (condensed)

1. *"Move ahead with PR #3 merge and beginning the next phase."*
2. Four clarify answers, each accepting the recommendation.
3. *"Feel free to make that amendment. Spec approved. Write to prompt history. Run speckit plan."*

## What Happened

- **Phase 002 merged:** PR #3 was merged with a merge commit after the user confirmed the
  completion check. `main` is green (283 tests).
- **A probe found a real crash:** before writing the spec, Claude checked two terminal failure
  modes. When input ends unexpectedly (end-of-file), the app **crashed with a raw traceback**, and
  Ctrl+C does the same. That evidence made "the customer never sees a raw error" the top-priority
  story.
- **Phase 003 scope:** four stories, continuing the numbering (US9–US12, AC-9.x–AC-12.x):
  - graceful failure
  - trace mode
  - an adversarial end-to-end suite (plus the phase 002 observation about empty history details
    for contact changes)
  - release documentation
- **No new customer features** are in scope. The local web UI stays the stretch phase 004.

## Decisions Accepted (Clarify Session 2026-09-25)

| # | Question | Decision |
|---|---|---|
| 1 | After an unexpected bug, return to the menu or exit? | **Return to the menu** with "Something went wrong on our side. Please try again later." and a status-only report with the new status `FAILED_UNEXPECTED` |
| 2 | Where does `--trace` output go? | **Terminal only**; never written to disk |
| 3 | What format for the architecture diagram? | **Mermaid** in `docs/architecture.md`, with a summary in the README |
| 4 | Real-model or scripted sample outputs? | **Real-model runs**, reviewed and committed; a test checks for PII and required sections, not exact wording |
| — | Ctrl+C exit code (filled in without asking) | **130**, the conventional code for an interrupted program |

## Constitution Amendment v1.0.0 → v1.1.0

- **Change:** the failure-status list gains `FAILED_UNEXPECTED`, for programming errors outside
  the existing categories, always shown to customers as a fixed, non-technical message.
- **Type:** MINOR (the section is materially expanded; no principle is removed or redefined).
- **Process:** Claude flagged during clarify that a new status conflicts with the constitution's
  explicit list. The user approved the amendment, and it was committed on its own
  (`docs: amend constitution to v1.1.0`) before any code, with this entry as its prompt-history
  note, as the governance section requires. Under the phase-only branching rule, it rides in the
  phase 003 PR rather than a separate `docs/` PR.

## Pushbacks and Clarifications

- None this round; all four recommendations were accepted.
- The questions again focused on unhappy paths and privacy surface (trace storage, sample
  provenance), consistent with the lesson from phases 001 and 002.

## Deferred or Rejected Scope

- **Deferred:** local web UI (stretch phase 004); holiday-aware dates; customers viewing their help
  requests; staff actions (confirming pending changes, closing claims).
- **Rejected:** saving traces to disk; image-based diagrams; scripted-only sample outputs.

## Next

`/speckit-plan` for 003: a last-resort error boundary in the CLI, EOF and Ctrl+C handling, trace
rendering from contracts, the adversarial scenario suite plus a live set, the contact-change history
detail, and the README, architecture, and samples workflow.
