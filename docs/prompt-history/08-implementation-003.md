# 08: Implementing Phase 003 (Hardening and Release)

**Branch:** `003-hardening-and-release` · **Spec:** `specs/003-hardening-and-release/`

## Objective

Make the app safe to hand to a reviewer. Unexpected errors, end of input, and Ctrl+C should never
crash it or leave a half-saved claim. Add a sanitized staff trace, prove the safety guarantees
against adversarial input, and write the release documentation (README, architecture, samples).

## Key prompts

- `/speckit-implement` (phase 003), with standing permission: "As long as there's no issues, feel
  free to continue."
- Mid-implementation: "Hurry up development. Need less token usage. Make sure we have tasks
  checked and no major problems." After this, the remaining work was batched into fewer, larger
  steps.

## What was built (by user story)

- **US9, resilience:**
  - A CLI error boundary: a fixed apology, a `FAILED_UNEXPECTED` status-only report (constitution
    v1.1.0), and the menu comes back.
  - End of input exits 0, and Ctrl+C exits 130 at every prompt.
  - A malformed `MODEL_NAME` now gives the setup message.
- **US10, trace mode:** `--trace` prints structured `TraceEntry` values after each reply, in the
  terminal only. The trace is withheld entirely if a personal value is ever detected.
- **US11, adversarial verification:**
  - 16 scripted end-to-end scenarios check that no PII is stored or shown, no decision language
    appears, and the log stays structured.
  - A 13-case live set against the real model: **13/13 customer-safe (SC-304).**
- **US12, release docs:**
  - `README.md` and `docs/architecture.md` (two Mermaid diagrams).
  - 7 samples in `docs/samples/`.
  - `tests/unit/test_docs.py`, which keeps links, CLI flags, diagram modules, and sample safety
    honest.

## Defects found and fixed (Red → Green)

- End of input crashed with a traceback.
- A malformed model name crashed with a traceback.
- A failed update could release, and so delete, an existing claim's number. Now only numbers the
  run itself reserved are released.
- An unexpected bug after reserving a number left an empty claim file (analyze finding H1).
- A contact-only update recorded an empty history detail. It now records "contact change
  requested".

## Decisions and clarifications

- **Privacy-review sample:** the only scripted sample, and labeled as such, because the real model
  can't trigger a privacy review on demand (AC-12.4 amendment).
- **E10 (out of scope) has no sample:** it writes no record or report by design (FR-214).
- **Doc tests check structure and safety, never wording.** Samples come from real-model runs.
- **README and architecture review:** writing them surfaced overstated claims, which were
  corrected against the code before committing: claim-number formats, which facts are sensitive,
  the report folder (`output/`), and the failure status names.

## Deferred

- Stretch phase 004: a local web UI.
- Holidays in business-day dates (v1 skips weekends only).
