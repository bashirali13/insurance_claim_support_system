---
description: "Task list for 003-hardening-and-release"
---

# Tasks: Hardening and Release

**Input**: Design documents from `specs/003-hardening-and-release/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: **Required** (constitution I–II). Test names are `test_ac_<story>_<n>_<behavior>`, with
stories 9–12.
- **New behavior** (US9, US10, AC-11.4, US12 doc checks) follows Red → Green → Refactor.
- **Verification tests** (AC-11.1, 11.2, 11.3) check guarantees that already exist, so they are
  expected to pass on the first run. They add no production code. **If one fails, that's a real
  bug**, fixed with its own Red → Green commit pair and noted in prompt history 08.
- **Documentation ACs that can't be automated** (AC-12.1, and AC-12.3's visual check) are named
  quickstart steps (SC-306).

**Reuse**: `tests/conftest.py` (`structured_model`, `failing_model`, `capture_model`, `fixed_now`,
`workdirs`), `tests/builders.py`, and the CLI test fixtures in `tests/integration/test_cli.py`
(`keyboard`, `sample_deps`, `snapshot`).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup / Phase 2: Foundational

None required. The branch, tooling, and all contracts from phases 001 and 002 are in place.
Constitution v1.1.0 (`FAILED_UNEXPECTED`) is already committed.

---

## Phase 3: User Story 9 — The customer never sees a raw error (P1) 🎯 MVP

**Goal**: an unexpected bug shows a fixed message and returns to the menu; end-of-input exits 0;
Ctrl+C exits 130; no traceback on any path; no reserved number is left behind.

**Independent Test**: scripted input that ends early or raises `KeyboardInterrupt`, and flows
monkeypatched to raise.

### Tests (write first; they must fail)

- [X] T001 [US9] Write `tests/integration/test_resilience.py`:
  - `test_ac_9_1_unexpected_error_in_filing_shows_message_reports_and_returns_to_menu`
    (`cli.file_claim` monkeypatched to raise `ZeroDivisionError`; expects "Something went wrong on
    our side. Please try again later.", the menu shown again, and a report containing
    `FAILED_UNEXPECTED` and `ZeroDivisionError`)
  - `test_ac_9_1_unexpected_error_in_update_and_help_also_reported` (parametrized: options 3 and
    4)
  - `test_ac_9_1_unexpected_error_in_status_check_writes_nothing` (option 2; snapshot unchanged,
    per AC-6.8)
  - `test_ac_9_2_end_of_input_at_any_prompt_says_goodbye_and_exits_0` (parametrized: at the menu,
    at a claim-number prompt, mid-narrative)
  - `test_ac_9_3_ctrl_c_at_a_prompt_prints_stopped_and_exits_130` (parametrized: the same three
    prompts as AC-9.2)
  - `test_ac_9_3_ctrl_c_during_filing_leaves_no_claim_file` (the summary model raises
    `KeyboardInterrupt`; `data/claims/` has no new file)
  - `test_ac_9_3_ctrl_c_during_help_releases_the_reference` (`data/help/` is empty)
  - `test_ac_9_1_unexpected_error_after_reservation_leaves_no_claim_file` (a bug raised after the
    claim number is reserved; `data/claims/` has no new file; FR-303)
  - `test_ac_9_1_unexpected_error_after_reference_leaves_no_help_record` (the same for a help
    reference)
  - `test_ac_9_4_no_failure_output_contains_technical_detail` (parametrized over all of the above;
    no "Traceback", exception class names, paths, or "deepseek"/"openrouter")

### Implementation

- [X] T002 [US9] In `src/claim_intake/contracts.py`, add `ProcessingStatus.FAILED_UNEXPECTED`. In
  `src/claim_intake/orchestration.py`, add `record_unexpected(deps, task: MenuTask, exc)`, which
  writes a status-only report (claim `None`, failed step `None`, error category = the exception
  class name, task wording) and never prints.
- [X] T003 [US9] In `src/claim_intake/orchestration.py`, add `TaskRun.release_reservation()`.
  `file_claim` releases on **any** exception that escapes it (`except BaseException: release;
  raise`), whether an unexpected bug or Ctrl+C (FR-303). In `src/claim_intake/existing_claims.py`,
  `get_help` does the same for a reserved help reference.
- [X] T004 [US9] In `src/claim_intake/cli.py`:
  - a per-task `try/except Exception` boundary in `run()` (options 1, 3, and 4 call
    `record_unexpected`; option 2 writes nothing)
  - `safe_run(deps)`, which maps `EOFError` → goodbye, 0 and `KeyboardInterrupt` → "Stopped.
    Nothing further was sent.", 130
  - `main()` calls `safe_run`
- [X] T005 [US9] Refactor pass, keeping the suite green.

**Checkpoint**: `uv run pytest -k ac_9` green. `printf '2\n' | uv run claim-support` exits 0 with no
traceback.

---

## Phase 4: User Story 10 — Staff trace mode (P2)

**Goal**: `--trace` prints a sanitized block after each reply of options 1, 3, and 4, built only
from structured contract fields, never stored.

**Independent Test**: flows with scripted models return `TaskResult.trace`; `render_trace` is
tested as pure formatting; the CLI prints it only with the flag.

### Tests (write first; they must fail)

- [X] T006 [P] [US10] Write `tests/unit/test_trace.py`:
  - `test_ac_10_1_render_trace_matches_block_format` (the exact block from data-model.md)
  - `test_ac_10_3_failed_entry_shows_step_and_error_category`
  - `test_ac_10_4_trace_is_withheld_when_privacy_check_fails`
- [X] T007 [P] [US10] Write `tests/integration/test_trace_flows.py`:
  - `test_ac_10_1_filing_trace_has_intake_assessment_risk_saved` (values for S10:
    `PERSON, PHONE`, `COLLISION`, `HIGH`, `2026-09-25`, …)
  - `test_ac_10_2_update_trace_lists_added_corrected_pending_fields`
  - `test_ac_10_2_help_trace_lists_categories_and_teams` and
    `test_ac_10_2_redirect_only_help_trace_says_no_team_routed`
  - `test_ac_10_3_failure_trace_has_failed_step_and_category` (parametrized: filing, update,
    help)
  - `test_ac_10_4_trace_has_no_narrative_prose_or_personal_values` (parametrized over the flows;
    narrative words, the model opening line, the rationale, and secret values are all absent)
- [X] T008 [P] [US10] Append to `tests/integration/test_cli.py`:
  - `test_ac_10_1_trace_flag_prints_block_after_reply`
  - `test_ac_10_5_no_trace_printed_without_flag`
  - `test_ac_10_5_trace_is_never_written_to_disk` (no file under `workdirs` contains
    `"trace ─"`)

### Implementation

- [X] T009 [US10] In `src/claim_intake/contracts.py`, add `TraceEntry` (`step` one of `intake,
  assessment, risk, triage, routing, saved, failed`; `values: dict[str, str]`) and
  `TaskResult.trace: list[TraceEntry] = []`.
- [X] T010 [US10] In `src/claim_intake/reporting.py`, add `render_trace(entries) -> str` (format in
  data-model.md; returns `"  (trace withheld: privacy check)"` if `find_pii` matches).
- [X] T011 [US10] In `src/claim_intake/orchestration.py`: `TaskRun.trace` entries; `file_claim`
  appends intake, assessment, risk, and saved entries; `fail()` and the privacy path append a
  `failed` or `saved` entry; results carry `trace`.
- [X] T012 [US10] In `src/claim_intake/existing_claims.py`, add update and help entries (research R3
  table), including "no team routed".
- [X] T013 [US10] In `src/claim_intake/cli.py`, add the `--trace` flag and print
  `render_trace(result.trace)` after replies of options 1, 3, and 4.
- [X] T014 [US10] Refactor pass, keeping the suite green.

**Checkpoint**: `uv run pytest -k ac_10` green.

---

## Phase 5: User Story 11 — Adversarial end-to-end suite (P3)

**Goal**: the safety guarantees hold together across whole flows, for scripted and real models.
The contact-change history detail is fixed.

### Tests

- [X] T015 [P] [US11] Red: append
  `test_ac_11_4_contact_only_update_records_contact_change_requested` to
  `tests/integration/test_update_claim.py`.
- [X] T016 [P] [US11] Verification: write `tests/integration/test_adversarial.py` with the shared
  helper `assert_customer_safe(result, workdirs, secrets)` (no secret in any file or the reply, no
  placeholder in the reply, no forbidden decision term in the reply, every event-log line
  structured), plus:
  - `test_ac_11_1_filing_scenario_is_customer_safe_and_routed_*`, parametrized over S17, S18, S19,
    S20, S21, S22, S24, S25, S26, S27 with the expected routing and status from the catalog
  - `test_ac_11_1_input_at_5000_chars_is_accepted_and_5001_rejected` (via the CLI)
  - `test_ac_11_2_update_and_help_scenario_is_customer_safe_*`, parametrized over: injection in an
    update, a PII-only update, lawyer plus complaint, out-of-scope plus distress, "approve my
    claim" in help

  That's 16 scenarios in total (SC-303 requires at least 15).

### Implementation

- [X] T017 [US11] In `src/claim_intake/existing_claims.py`, set the history detail to
  `"contact change requested"` for a contact-only update (Green for T015).
- [X] T018 [P] [US11] Create `tests/fixtures/narratives/adversarial_cases.json` (≥ 12 fictional
  inputs covering injection, PII in every position, decision-extraction attempts, contradictions,
  and non-English text, each with `secrets` and an `injection` flag).
- [X] T019 [US11] Add `test_ac_11_3_live_adversarial_set_is_customer_safe` to
  `tests/live/test_live_eval.py`, then run it against OpenRouter and record the results (SC-304).
  *Result (2026-09-25, `deepseek/deepseek-v4-flash-0731`): 13/13 cases customer-safe. No leaked
  secrets, no decision language, and all 5 injection cases were flagged (219 s total).*

**Checkpoint**: `uv run pytest -k ac_11` green; the live set passes.

---

## Phase 6: User Story 12 — Release documentation (P4)

**Goal**: a reader can understand, run, and see real output from the project.

### Tests (write first; they must fail)

- [X] T020 [US12] Write `tests/unit/test_docs.py`:
  - `test_ac_12_2_readme_relative_links_resolve`
  - `test_ac_12_2_readme_cli_flags_are_real_options` (every `claim-support --x` in the README is
    an `argparse` option)
  - `test_ac_12_3_architecture_mermaid_names_every_module` (`cli, orchestration,
    existing_claims, intake, assessment, risk, summary, rules, pii, reporting, storage`)
  - `test_ac_12_4_samples_cover_filing_update_help_privacy_and_escalation`
  - `test_ac_12_4_samples_have_reply_and_report_sections_and_notice`
  - `test_ac_12_4_samples_contain_no_personal_values`
  - `test_ac_12_4_scripted_privacy_sample_is_labeled` (the privacy-review sample contains the
    visible "scripted run" note)

### Implementation

- [X] T021 [US12] Write `docs/architecture.md`: a Mermaid flowchart (CLI → flows → four agents
  with modes → rules and privacy guard → storage and event log) and a Mermaid sequence diagram of
  "File a new claim" with the contract types on each arrow.
- [X] T022 [US12] Rewrite `README.md` per FR-310: what it does and doesn't do, setup, run
  (including `--load-samples` and `--trace`), the menu options, safety guarantees, testing,
  structure, the SDD/TDD process, and links. Embed a summary Mermaid diagram.
- [X] T023 [US12] Capture samples with the real model in a scratch folder (research R6: S01, S10,
  S22, E04, E07, E08, E10), review them, and commit them to `docs/samples/*.md` with
  `## Customer reply` and `## Staff report` sections. Produce the privacy-review example with a
  scripted run and label it (AC-12.4).
  *Done 2026-09-25: 7 samples in `docs/samples/` (6 real-model, 1 labeled scripted). E10 has no
  sample file: an out-of-scope request writes no record or report by design (FR-214), so there's
  no staff report to pair with its reply.*
- [X] T024 [US12] Run quickstart steps Q-9, Q-10, and Q-12.1 (fresh clone); record the results.
  Q-12.3 needs the pushed branch, so it runs in T027.
  *Done 2026-09-25: a fresh clone ran `uv sync`, `--load-samples --trace`, and a status check
  (exit 0); piped EOF exits 0 (Q-9). Ctrl+C and trace blocks (Q-9, Q-10) are covered by the
  automated AC-9.x and AC-10.x tests, and the real-model capture run exercised every flow.*

**Checkpoint**: `uv run pytest -k ac_12` green; the quickstart steps pass.

---

## Phase 7: Polish & Close

- [X] T025 [P] Update `docs/user-experience.md` §10 (trace built, terminal-only) and `CLAUDE.md`
  Commands (`--load-samples`, `--trace`).
- [X] T026 Run the final `uv run ruff format .`, `uv run ruff check .`, full `uv run pytest`, and
  the SC-306 AC coverage check.
- [X] T027 Write `docs/prompt-history/08-implementation-003.md`, push, run quickstart Q-12.3
  (Mermaid renders on GitHub), open the phase PR with `gh`, present the phase-completion check,
  and ask about the stretch phase 004 (local web UI).

---

## Dependencies & Execution Order

- **US9 → US10 → US11 → US12 → Polish.**
  - US10's `fail()` trace entries build on US9's failure handling.
  - US11 verifies everything built so far.
  - US12 documents the finished system, so it goes last (constitution: README and diagram at the
    very end).
- Within a story: tests → implementation → refactor.

### Parallel Opportunities

| Story | Parallel |
|---|---|
| US10 | T006 ∥ T007 ∥ T008 |
| US11 | T015 ∥ T016 ∥ T018 |
| Polish | T025 alongside T024 |

## Implementation Strategy

**MVP = US9**: no customer ever sees a traceback. Each later story ends at a green checkpoint.

## AC → Task Traceability

| AC | Tasks | AC | Tasks |
|---|---|---|---|
| 9.1–9.4 | T001 (tests); T002–T004 | 11.1, 11.2 | T016 (verification) |
| 10.1 | T006, T007, T008 | 11.3 | T018, T019 (live) |
| 10.2 | T007 | 11.4 | T015 → T017 |
| 10.3 | T006, T007 | 12.1 | T024 (quickstart Q-12.1) |
| 10.4 | T006, T007 | 12.2 | T020 |
| 10.5 | T008 | 12.3 | T020 (modules) + T027 (Q-12.3 visual) |
| | | 12.4 | T020, T023 |
