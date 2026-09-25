---
description: "Task list for 002-existing-claim-support"
---

# Tasks: Existing-Claim Support

**Input**: Design documents from `specs/002-existing-claim-support/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: **Required** by the constitution (Principles I–II).
- Every test is named `test_ac_<story>_<n>_<behavior>`. This phase uses stories 6–8; phase 001's
  names are reused only where a phase 001 test must change.
- Each test task is committed **Red** (`test:`, failing for the expected reason) before its Green
  (`feat:`) task. Refactor tasks are committed as `refactor:`.

**Reuse**: phase 001's `tests/conftest.py` helpers (`structured_model`, `failing_model`,
`capture_model`, `fixed_now`, `workdirs`) and `tests/builders.py`. New builders are added there
when a test needs them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US6 / US7 / US8

---

## Phase 1: Setup

- [X] T001 Add `data/claims/` and `data/help/` to `.gitignore` (FR-204a). This is configuration,
  verified by quickstart §2 (`git check-ignore`), so no unit test is needed.

---

## Phase 2: Foundational (event log `task`, FR-218)

- [X] T002 Red: in `tests/integration/test_file_claim.py`:
  - update `test_ac_5_13_event_log_lines_have_only_allowed_fields` so the allowed keys include
    `task` (FR-218 extends AC-5.13)
  - add `test_ac_5_13_filing_event_lines_have_task_file_claim`
- [X] T003 Green:
  - add `MenuTask` (`FILE_CLAIM, UPDATE_DETAILS, GET_HELP`) and `EventLogEntry.task: MenuTask` to
    `src/claim_intake/contracts.py`
  - add a `task` attribute to `orchestration._Run` (default `FILE_CLAIM` for `file_claim`),
    written on every event line

**Checkpoint**: all 174 phase 001 tests plus the new one are green.

---

## Phase 3: User Story 6 — Check status and sample claims (P1) 🎯 MVP

**Goal**: option 2 shows a claim's status from its saved record with no model call. Six sample
claims can be loaded.

**Independent Test**: load the samples into `workdirs`, then render or check each claim. No model
is involved.

### Tests for User Story 6 (write first; they must fail)

- [X] T004 [P] [US6] Write `tests/unit/test_status.py`:
  - `test_ac_6_2_claim_number_is_trimmed_and_uppercased`
  - `test_ac_6_3_malformed_claim_numbers_are_rejected` (parametrized: `clm 2026 5`,
    `CLM-26-5`, `CLM-2026-00051`)
  - `test_ac_6_1_status_block_for_hit_and_run_sample` (expects the exact block in contracts/cli.md
    option 2, including "Waiting for an adjuster to confirm" when a `PendingChange` exists)
  - `test_ac_6_5_status_wording_*` (parametrized over all five statuses)
  - `test_ac_6_6_privacy_review_claim_shows_no_incident_or_facts`
  - `test_ac_6_7_no_follow_up_promise_when_date_passed_or_closed`
  - `test_ac_6_1_phase_001_record_without_new_fields_still_loads`
- [X] T005 [P] [US6] Write `tests/unit/test_samples.py`:
  - `test_ac_6_9_six_samples_are_valid_claim_records_covering_every_status`
  - `test_ac_6_9_samples_contain_no_personal_information` (`find_pii` on each file is empty)
  - `test_ac_6_9_loading_copies_missing_samples_without_overwriting`
  - `test_ac_6_9_next_claim_after_loading_is_0007`
- [X] T006 [P] [US6] In `tests/integration/test_cli.py`:
  - **replace** `test_ac_5_1_options_2_to_4_say_coming_soon` with
    `test_ac_5_1_options_3_and_4_say_coming_soon` (option 2 now works, FR-220; options 3 and 4
    are replaced in T016/T021 and T028/T034)
  - add `test_ac_6_1_option_2_prints_status_for_sample_claim`
  - add `test_ac_6_3_malformed_number_hint_then_empty_returns_to_menu` (also asserts that no
    report or event-log line is written, FR-219)
  - add `test_ac_6_4_unknown_claim_number_message`
  - add `test_ac_6_8_status_check_calls_no_model_and_writes_nothing` (deps built with
    `failing_model`; the directory snapshot before and after is identical)
  - add `test_ac_6_9_load_samples_flag_reports_count_then_shows_menu`

### Implementation for User Story 6

- [X] T007 [US6] In `src/claim_intake/contracts.py`:
  - `ClaimStatus` + `UNDER_REVIEW`, `CLOSED`; `Team` + `POLICY_SERVICES`
  - `HistoryEntry.event` + `"DETAILS_UPDATED"`, `"HELP_REQUESTED"`, and
    `detail: str | None = None`
  - `PendingChange` (field limited to the five sensitive fields)
  - `ClaimRecord.pending_changes: list[PendingChange] = []`

  In `src/claim_intake/rules.py`: `normalize_claim_number(text) -> str | None`.
- [X] T008 [US6] Create `data/samples/CLM-2026-000{1..6}.json` per contracts/files.md (all
  fictional, sanitized, filed Sep 14–23, 2026; `0005` has the police report missing and time
  "yesterday around 6pm"), and add `storage.load_samples(root) -> list[str]`.
- [X] T009 [US6] In `src/claim_intake/reporting.py`:
  - `render_status(record, today) -> str`
  - the status, incident-type, history-event, and field wording tables from data-model.md
- [X] T010 [US6] Create `src/claim_intake/existing_claims.py` with
  `check_status(claim_id, store, today)`. In `src/claim_intake/cli.py`:
  - a claim-number prompt helper (options 2 and 3 behavior)
  - option 2
  - an `argparse` `--load-samples` flag printing `Loaded N sample claims.`
- [X] T011 [US6] Refactor pass (`reporting.py`, `cli.py`), keeping the suite green.

**Checkpoint**: `uv run pytest -k ac_6` green; `uv run claim-support --load-samples` → option 2
works.

---

## Phase 4: User Story 7 — Add or correct details (P2)

**Goal**: option 3 applies routine changes, holds sensitive corrections, routes contact changes,
recomputes routing, and records history, with no personal values stored.

**Independent Test**: sample claim + `structured_model` answers for intake, update, and risk →
check the reply, the saved record, and the history.

### Tests for User Story 7 (write first; they must fail)

- [ ] T012 [P] [US7] Write `tests/unit/test_update_rules.py` (pure `rules.diff_facts`,
  `status_after_update`, and follow-up combination):
  - `test_ac_7_1_police_report_unknown_to_yes_is_added`
  - `test_ac_7_1_new_damage_items_are_added_and_list_never_shrinks`
  - `test_ac_7_2_changed_incident_time_is_a_corrected_change_and_applied`
  - `test_ac_7_2_diff_rules_for_every_field_kind` (parametrized over every row of the research R2
    table, including `location`, `vehicle_drivable`, `other_property_damaged`, `um_uim_subtype`,
    and value → unknown; SC-202)
  - `test_ac_7_4_injury_yes_to_no_is_sensitive_and_saved_value_kept`
  - `test_ac_7_4_incident_type_change_is_sensitive`
  - `test_ac_7_4_injury_unknown_to_yes_is_added_and_applied_immediately`
  - `test_ac_7_6_identical_facts_produce_empty_changes`
  - `test_ac_7_5_status_after_update_priority_*` (parametrized: ESCALATED stays; HIGH →
    ESCALATED; UNDER_REVIEW stays; missing → AWAITING_INFORMATION; else SUBMITTED)
  - `test_ac_7_5_claim_follow_up_date_is_earliest_promise`
- [ ] T013 [P] [US7] Append to `tests/unit/test_assessment.py`:
  - `test_ac_7_11_update_prompt_tags_text_and_sends_saved_facts_outside_tags`
  - `test_ac_7_1_update_returns_model_facts_and_contact_flag`
- [ ] T014 [P] [US7] Append to `tests/unit/test_reporting.py`:
  - `test_ac_7_1_update_reply_lists_added_items_in_customer_wording`
  - `test_ac_7_2_update_reply_shows_old_to_new_for_corrections`
  - `test_ac_7_3_update_reply_contact_change_line_with_three_day_date`
  - `test_ac_7_4_update_reply_pending_line_names_field_and_one_day_date`
  - `test_ac_7_8_update_report_sections_and_notice`
  - `test_ac_7_9_status_only_report_names_update_task`
- [ ] T015 [P] [US7] Write `tests/integration/test_update_claim.py` (samples loaded into
  `workdirs`, `fixed_now`):
  - `test_ac_7_1_police_report_added_updates_record_missing_list_and_history` (the history
    `detail` has field names only)
  - `test_ac_7_2_time_correction_is_saved`
  - `test_ac_7_3_contact_change_routes_policy_services_and_stores_no_value` (555-908-1200 in no
    file)
  - `test_ac_7_4_sensitive_correction_is_pending_and_original_kept` (then `check_status` shows
    "Waiting for an adjuster to confirm")
  - `test_ac_7_5_routing_recomputed_teams_replaced_escalation_kept`
  - `test_ac_7_6_no_change_update_writes_nothing`
  - `test_ac_7_8_update_writes_report_and_event_lines_with_update_task`
  - `test_ac_7_9_model_failure_leaves_claim_unchanged_with_safe_message`
  - `test_ac_7_10_residual_pii_opens_privacy_review_without_applying_update` (teams = existing +
    `PRIVACY_REVIEW`, follow-up +3 business days, facts unchanged)
- [ ] T016 [P] [US7] In `tests/integration/test_cli.py`:
  - add `test_ac_7_7_closed_claim_update_is_refused_without_asking_for_text`
  - add `test_ac_7_12_privacy_review_claim_update_is_refused_*` (future date → "by <date>";
    past date → "soon")
  - add `test_ac_7_1_option_3_flow_prints_update_reply`
  - rename T006's test to `test_ac_5_1_option_4_says_coming_soon`

### Implementation for User Story 7

- [ ] T017 [US7] In contracts: `UpdateLlmOutput`, `FieldChange`, `FactChanges`. In
  `src/claim_intake/rules.py`:
  - `diff_facts(saved, updated)` (research R2 table; sensitive = a correction to the five fields)
  - `status_after_update(current, level, missing)`
  - `update_follow_ups(...)` returning the promises and the earliest date
- [ ] T018 [US7] In `src/claim_intake/agents/assessment.py`: the update-mode agent and
  `update(sanitized, saved_assessment, agents)` (saved facts labeled outside the tags; instructions
  per contracts/agents.md). Register `assessment_update` in `create_agents`.
- [ ] T019 [US7] In `src/claim_intake/reporting.py`: `render_update_reply`,
  `render_update_report`, and a task-wording parameter for `render_status_only_report` (phase
  001's calls pass "File a new claim").
- [ ] T020 [US7] In `src/claim_intake/existing_claims.py`: `update_claim(claim_id, raw_text, deps,
  on_progress)` per contracts/agents.md (normal, no-change, privacy, and failure paths; `_Run`
  with task `UPDATE_DETAILS`).
- [ ] T021 [US7] In `src/claim_intake/cli.py`: option 3 (closed and privacy-review refusals, text
  prompt, progress, reply).
- [ ] T022 [US7] Refactor pass (`rules.py`, `existing_claims.py`), keeping the suite green.

**Checkpoint**: `uv run pytest -k "ac_6 or ac_7"` green.

---

## Phase 5: User Story 8 — Get help (P3)

**Goal**: option 4 categorizes requests, routes them with dates and a reference, redirects
out-of-scope requests, and links a verified claim.

**Independent Test**: `structured_model` answers for intake, triage, and help reply → check the
routing, the help record, the reply, and the claim history.

### Tests for User Story 8 (write first; they must fail)

- [ ] T023 [P] [US8] Write `tests/unit/test_help_rules.py` (pure `rules.help_routing`):
  - `test_ac_8_1_service_delay_routes_customer_relations_two_days`
  - `test_ac_8_2_routing_table_*` (parametrized over every FR-213 row)
  - `test_ac_8_3_two_requests_each_team_once_fewest_days`
  - `test_ac_8_4_out_of_scope_only_routes_nobody`
  - `test_ac_8_5_file_a_claim_routes_nobody`
  - `test_ac_8_7_legal_or_injection_adds_special_review_and_adjuster_all_one_day` (includes the
    phrase-list case with no model flag)
  - `test_ac_8_8_distressed_or_angry_adds_customer_relations`
- [ ] T024 [P] [US8] Append to `tests/unit/test_risk.py`:
  - `test_ac_8_10_triage_prompt_tags_request_and_marks_it_as_data`
  - `test_ac_8_2_triage_rejects_more_than_three_categories_then_fails`

  Append to `tests/unit/test_summary.py`:
  - `test_ac_8_1_help_opening_with_decision_words_or_pii_is_retried_then_fails`
  - `test_ac_8_1_clean_help_opening_passes`
- [ ] T025 [P] [US8] Append to `tests/unit/test_storage.py`:
  - `test_ac_8_1_help_references_sequential_and_unique_across_restarts`
  - `test_ac_8_9_help_record_round_trips`
- [ ] T026 [P] [US8] Append to `tests/unit/test_reporting.py`:
  - `test_ac_8_1_help_reply_lists_team_dates_and_reference`
  - `test_ac_8_4_redirect_only_reply_has_no_reference`
  - `test_ac_8_5_file_a_claim_line_points_to_option_1`
  - `test_ac_8_7_help_reply_never_mentions_special_review`
  - `test_ac_8_9_help_report_sections_and_notice`
  - `test_ac_8_8_distressed_out_of_scope_reply_has_redirect_and_team`
- [ ] T027 [P] [US8] Write `tests/integration/test_get_help.py`:
  - `test_ac_8_1_service_delay_end_to_end_saves_record_report_reference`
  - `test_ac_8_3_complaint_and_speak_to_adjuster_route_both_teams`
  - `test_ac_8_4_out_of_scope_writes_no_record_or_reference`
  - `test_ac_8_6_linked_claim_gains_help_history_and_is_otherwise_unchanged`
  - `test_ac_8_7_lawyer_mention_routes_adjuster_next_day_without_naming_special_review`
  - `test_ac_8_9_no_personal_values_anywhere_and_event_lines_have_help_task`
  - `test_ac_8_12_residual_pii_opens_minimal_privacy_help_record`
  - `test_ac_8_13_model_failure_creates_no_record_and_leaves_claim_unchanged`
- [ ] T028 [P] [US8] In `tests/integration/test_cli.py`:
  - **remove** `test_ac_5_1_option_4_says_coming_soon` (FR-220 complete)
  - add `test_ac_8_11_enter_continues_without_claim_number`
  - add `test_ac_8_11_unknown_or_malformed_number_hint_with_skip_option`
  - add `test_ac_8_1_option_4_flow_prints_help_reply`

### Implementation for User Story 8

- [ ] T029 [US8] In contracts: `RequestCategory`, `HelpTriageLlmOutput` ("categories 1–3",
  "rationale 1–300"), `HelpReplyLlmOutput`, `TeamPromise`, and `HelpRecord` (help_id
  `^HELP-\d{4}-\d{4}$`; sentiment and categories empty only for privacy review). In rules:
  `help_routing(triage, text)`.
- [ ] T030 [US8] Create `src/claim_intake/agents/validation.py` (move phase 001's summary
  validator here and reuse it). Add the help-triage agent and `triage()` in
  `agents/risk.py`, and the help-reply agent and `help_opening()` in `agents/summary.py`. Register
  both in `create_agents`.
- [ ] T031 [US8] In `src/claim_intake/storage.py`: extract `NumberedFiles(dir, prefix)` from
  `ClaimStore` (phase 001 storage tests stay green) and add `HelpStore` (`data/help/`, `HELP`).
- [ ] T032 [US8] In `src/claim_intake/reporting.py`: `render_help_reply` and
  `render_help_report`.
- [ ] T033 [US8] In `src/claim_intake/existing_claims.py`: `get_help(claim_id, raw_text, deps,
  on_progress)` (routed, redirect-only, privacy, failure, and claim-linking paths; `_Run` with
  task `GET_HELP`).
- [ ] T034 [US8] In `src/claim_intake/cli.py`: option 4 with the optional claim-number prompt.
  This removes the last "coming soon".
- [ ] T035 [US8] Refactor pass (`existing_claims.py`, `cli.py`, agents), keeping the suite green.

**Checkpoint**: full `uv run pytest` green; every AC-6.x, AC-7.x, AC-8.x has a named test.

---

## Phase 6: Live Evaluation & Polish

- [ ] T036 [P] Create the fictional fixtures `tests/fixtures/narratives/update_cases.json` (≥ 12:
  saved facts + update text + expected changed fields; seeded from E04–E07) and `help_cases.json`
  (≥ 14: text + expected categories; seeded from E08–E12, with ≥ 2 per category).
- [ ] T037 Add to `tests/live/test_live_eval.py`: SC-203 (update-mode accuracy ≥ 90%) and SC-204
  (triage accuracy ≥ 90%), then run them against OpenRouter. Record the results and any prompt
  adjustments, using prompt examples that never come from fixtures.
- [ ] T038 [P] Update `docs/customer-scenarios.md` E01–E12 to the sample claim numbers, and update
  `docs/user-experience.md` §5–7 if any wording changed.
- [ ] T039 Run the `specs/002-existing-claim-support/quickstart.md` validation:
  - SC-206 AC coverage
  - the gitignore check
  - the manual walkthrough in a scratch folder
  - SC-201: time a status check
- [ ] T040 Run the final `uv run ruff format .`, `uv run ruff check .`, and full `uv run pytest`.
- [ ] T041 Write `docs/prompt-history/06-implementation-002.md`, push the branch, open the phase PR
  with `gh`, and present the phase-completion check before merging.

---

## Dependencies & Execution Order

- **Setup → Foundational → US6 → US7 → US8 → Polish.**
  - US7 needs US6's claim lookup, samples, and `PendingChange`.
  - US8 needs US6's lookup (for claim linking) and reuses US7's status-only report wording.
- Each story's tests build their inputs directly (samples, builders, scripted models), so each
  story is independently testable.

### Parallel Opportunities

| Story | Parallel test tasks |
|---|---|
| US6 | T004 ∥ T005 ∥ T006 |
| US7 | T012 ∥ T013 ∥ T014 ∥ T015 ∥ T016 |
| US8 | T023 ∥ T024 ∥ T025 ∥ T026 ∥ T027 ∥ T028 |
| Polish | T036 ∥ T038 |

Implementation tasks within a story are sequential (they share `contracts.py`, `rules.py`, and
`cli.py`).

---

## Implementation Strategy

**MVP = US6.** Status checks plus sample claims are deterministic and demoable on their own. Each
later story ends at a green checkpoint, and the live evaluation proves SC-203 and SC-204 before
the phase PR.

---

## AC → Task Traceability

| AC | Test task(s) | AC | Test task(s) | AC | Test task(s) |
|---|---|---|---|---|---|
| 6.1 | T004, T006 | 7.1 | T012–T016 | 8.1 | T023–T028 |
| 6.2 | T004 | 7.2 | T012, T014, T015 | 8.2 | T023, T024 |
| 6.3 | T004, T006 | 7.3 | T014, T015 | 8.3 | T023, T027 |
| 6.4 | T006 | 7.4 | T012, T014, T015 | 8.4 | T023, T026, T027 |
| 6.5 | T004 | 7.5 | T012, T015 | 8.5 | T023, T026 |
| 6.6 | T004 | 7.6 | T012, T015 | 8.6 | T027 |
| 6.7 | T004 | 7.7 | T016 | 8.7 | T023, T026, T027 |
| 6.8 | T006 | 7.8 | T014, T015 | 8.8 | T023 |
| 6.9 | T005, T006 | 7.9 | T014, T015 | 8.9 | T025–T027 |
| 5.13 (FR-218) | T002 | 7.10 | T015 | 8.10 | T024 |
| | | 7.11 | T013 | 8.11 | T028 |
| | | 7.12 | T016 | 8.12 | T027 |
| | | | | 8.13 | T027 |
