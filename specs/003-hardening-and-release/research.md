# Research: Hardening and Release (003)

This phase adds no new dependencies and uses only the standard library plus existing modules.
Decisions build on phases 001 and 002.

---

## R1. A last-resort error boundary lives in the CLI, not the core (US9)

- **Decision:**
  - `cli.run()` wraps each menu task in `try/except Exception`. On an unexpected exception it
    prints `UNEXPECTED_MESSAGE` and calls the core function
    `orchestration.record_unexpected(deps, task, exc)`. That function writes a status-only report
    (`FAILED_UNEXPECTED`, error category = exception class name) and returns nothing printable.
  - Option 2 skips the report (AC-6.8).
  - The loop then shows the menu again.
- **Rationale:**
  - The core still never prints (constitution VII / phase 001 R12).
  - Known failures (model, validation, output) keep their specific handling inside the flows. The
    boundary only catches what escaped them.
  - Catching `Exception` rather than `BaseException` leaves `KeyboardInterrupt` for R2.
- **Alternatives:** a boundary inside every flow (duplicated), or crashing (the current behavior).

## R2. End-of-input and Ctrl+C (AC-9.2, AC-9.3)

- **Decision:**
  - `cli.main()` wraps `run()`: `EOFError` → print `GOODBYE`, return 0. `KeyboardInterrupt` →
    print `"Stopped. Nothing further was sent."`, return 130.
  - Inside the flows, `TaskRun` gains `release_reservation()`. `file_claim` and `get_help` catch
    `KeyboardInterrupt`, release any claim number or help reference they reserved, and re-raise.
    `update_claim` reserves nothing, and it writes the claim only in its final atomic save.
- **Rationale:**
  - No traceback, and no half-reserved number left as an empty file (the phase 001 `release`
    semantics).
  - 130 is the conventional exit code for an interrupted program.

## R3. Trace data travels in `TaskResult`, and the CLI renders it (US10)

- **Decision:**
  - `TaskResult` gains `trace: list[TraceEntry] = []`, where `TraceEntry(step: str, values:
    dict[str, str])`.
  - Each flow appends entries built **only** from contract fields: enum values, dates, field
    names, counts, and file names. Model-written prose (opening lines, summaries, rationales) and
    narrative text never enter a trace.
  - `TaskRun.fail()` adds a `failed` entry with the step and error category.
  - `reporting.render_trace(entries)` formats the block from `docs/user-experience.md` §10. If
    `find_pii` matches the rendered block, it returns `"  (trace withheld: privacy check)"`
    (FR-305).
  - `cli.run()` prints it after the reply only when `--trace` is set (FR-306).
- **Rationale:**
  - Trace data is plain data returned with the result, so it's testable without a terminal.
  - The core still doesn't print, and nothing is written to disk (clarify Q2).
- **Alternatives:** a callback like `on_progress` (harder to assert on), or logging-based tracing
  (writes to disk; rejected in clarify).

### Trace content per flow

| Flow | Entries (keys) |
|---|---|
| File a claim | `intake` (pii_removed, manual_review) → `assessment` (incident, injury, missing, coverage_lines) → `risk` (sentiment, indicators, risk, teams, follow_up_by) → `saved` (claim, status, report) |
| Update | `intake` → `assessment` (added, corrected, pending, contact_change) → `risk` (as above) → `saved` |
| Get help | `intake` → `triage` (categories, sentiment, flagged) → `routing` (teams with dates, or "no team routed") → `saved` (reference, report) |
| Any failure | `failed` (step, error_category) |

## R4. Adversarial suite: data-driven, reusing real flows (US11)

- **Decision:**
  - `tests/integration/test_adversarial.py` holds a list of scenario records: input text, scripted
    model answers, and the expected routing and status from `docs/customer-scenarios.md`.
  - One parametrized test per story criterion runs each scenario through `file_claim`,
    `update_claim`, or `get_help` in `workdirs`.
  - A shared helper `assert_customer_safe(result, workdirs, secrets)` checks the guarantees
    together:
    - no secret value in any file or the reply
    - no placeholder pattern in the reply
    - no forbidden decision term in the reply
    - every event-log line is structured
  - The 5,000 and 5,001-character cases run through the CLI, since that's where the limit lives.
  - A live set, `tests/fixtures/narratives/adversarial_cases.json` (≥ 12), runs whole flows with
    the real model under `-m live -k adversarial`.
- **Rationale:** readable (one table of scenarios), exhaustive in combination, and it reuses the
  catalog so expectations stay in one place.

## R5. Contact-change history detail (AC-11.4)

- **Decision:** in `update_claim`, the detail is the changed field names, or
  `"contact change requested"` when only a contact change was requested. It's one line and is
  covered by a unit-level integration test.

## R6. Sample outputs (US12, clarify Q4)

- **Decision:**
  - Samples are captured by running the real CLI with the live model in a scratch folder, reusing
    the walkthrough approach from phases 001 and 002. Each captured reply and its report are
    copied into `docs/samples/<scenario>.md`, with sections `## Customer reply` and
    `## Staff report`.
  - Samples: filing (S01 routine, S10 escalation, S22 mixed), update (E04 and E07, the pending
    change), help (E08 routed, E10 redirect), and one privacy review, which is produced
    deterministically with a scripted leak (reviewed and labeled as such).
  - `tests/unit/test_docs.py` checks that every sample is PII-free and has both sections. For
    reports, it also checks the decision notice.
  - The capture tooling isn't committed; it's a one-time documentation step, recorded in the
    quickstart.
- **Rationale:** honest, realistic output, with the guarantees still enforced by a test.

## R7. README and architecture checks (AC-12.1–AC-12.3)

- **Decision:** `tests/unit/test_docs.py` also checks that:
  - every relative Markdown link in `README.md` and `docs/architecture.md` resolves
  - every `claim-support --flag` shown in the README is a real `argparse` option
  - the architecture doc contains a Mermaid block naming each real module:
    `cli`, `orchestration`, `existing_claims`, `agents/intake|assessment|risk|summary`, `rules`,
    `pii`, `reporting`, `storage`
- **Beyond automation:** AC-12.1 (a fresh-clone walkthrough) and AC-12.3 (the diagram's visual
  correctness) are named quickstart steps (SC-306).

## R8. Mermaid diagram shape (clarify Q3)

- **Decision:**
  - `docs/architecture.md` has two diagrams:
    - a **flowchart** of CLI → flows → agents (with modes) → rules and privacy guard → storage and
      event log
    - a **sequence diagram** of "File a new claim" showing contract types on each arrow
  - The README embeds a smaller flowchart and links to the full document.
- **Rationale:** the flowchart answers "what are the parts"; the sequence diagram answers "how
  do the agents communicate", which is the project's core structured-communication theme.
