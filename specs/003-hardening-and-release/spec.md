# Feature Specification: Hardening and Release

**Feature Branch**: `003-hardening-and-release`

**Created**: 2026-09-25

**Status**: Approved (2026-09-25)

**Input**: User description: "Phase 003 of the Northstar Auto Insurance claim support system:
harden the system and prepare it for release. The customer must never see a raw error; staff get a
sanitized trace mode for demos and debugging; an end-to-end adversarial suite proves the safety
guarantees hold together; and the project is documented for a reader who has never seen it
(sample reports, architecture diagram, README). Carry forward the small observations from phases
001 and 002."

**References**: `docs/project-outline.md` (phase 003), `docs/user-experience.md` §8 and §10,
`docs/customer-scenarios.md`, `docs/prompt-history/04` and `06` (carried observations),
`.specify/memory/constitution.md` (v1.1.0).

**Numbering**: continues from phase 002. Stories **US9–US12**, criteria **AC-9.x–AC-12.x**.

## Clarifications

### Session 2026-09-25

- Q: When an unexpected bug happens during a menu task, should the app go back to the menu or exit, and how is it recorded? → A: Show the fixed message, return to the menu, and write a status-only report with the new status `FAILED_UNEXPECTED` and the exception class name as the error category.
- Q: Where does `--trace` output go? → A: Terminal only; it is printed after each reply and never written to disk.
- Q: What format should the architecture diagram use? → A: Mermaid in `docs/architecture.md`, with a short summary version embedded in the README.
- Q: Should committed samples come from real-model or scripted runs? → A: Real-model runs, reviewed and committed; a test checks each sample is free of personal values and has the required sections, without comparing exact wording.
- Plan-time consistency fix: AC-9.1's status-only report does not apply to status checks (option 2), which phase 002 AC-6.8 keeps write-free.

## User Scenarios & Testing *(mandatory)*

### User Story 9 - The customer never sees a raw error (Priority: P1)

Whatever goes wrong, the customer sees a calm, plain-language message. That includes a bug nobody
anticipated, the terminal input closing unexpectedly, or the customer pressing Ctrl+C. They never
see an error trace. Where it makes sense, staff get a status-only report so the problem can be
investigated.

**Why this priority**: A traceback is the most visible failure a customer support product can
show, and it can leak internal details. A probe during planning confirmed that closed input
currently crashes with a traceback.

**Independent Test**: Run the menu with scripted input that ends early, raises Ctrl+C, or hits a
deliberately broken flow. Check that the output contains only the fixed messages and never a
traceback.

**Acceptance Scenarios**:

1. **AC-9.1**: **Given** any menu task raises an unexpected error (a programming bug, not a model,
   validation, or storage failure), **When** it happens, **Then** the customer sees "Something went
   wrong on our side. Please try again later." with no technical detail, the app returns to the
   menu, and a status-only report is written with status `FAILED_UNEXPECTED` and the exception's
   class name as its error category. The next menu choice works normally. *(Exception: a status
   check, option 2, writes no report, because phase 002 AC-6.8 guarantees status checks never
   change any file.)*
2. **AC-9.2**: **Given** the customer's input ends unexpectedly (end-of-file) at any prompt, **When**
   it happens, **Then** the app prints the goodbye message and exits with code 0, with no traceback.
3. **AC-9.3**: **Given** the customer presses Ctrl+C at any prompt or while a claim is being
   processed, **When** it happens, **Then** the app prints "Stopped. Nothing further was sent." and
   exits with a non-zero code, with no traceback, and no partial claim record is left behind.
4. **AC-9.4**: **Given** any of the above, **When** the output is checked, **Then** it contains no
   "Traceback", exception class names, file paths, or model names.

---

### User Story 10 - Staff trace mode (Priority: P2)

A staff member or reviewer runs the app with `--trace` and, below each customer-facing reply, sees a
compact, sanitized view of what each agent received and decided: removed PII types, incident type,
facts, coverage lines, indicators, risk, teams, and dates. This makes the four-agent pipeline
visible for demos and debugging without ever exposing personal information.

**Why this priority**: It's the project's "show your work" feature (planned since the UX
walkthrough) and makes every later demo and review easier. It depends only on existing
structured contracts.

**Independent Test**: Run each flow with `--trace` and scripted models, then compare the trace
block with the contracts' values and check it for PII.

**Acceptance Scenarios**:

1. **AC-10.1**: **Given** the app is started with `--trace`, **When** a claim is filed, **Then** a
   trace block follows the reply with one section per step (intake, assessment, risk, saved) in the
   format of `docs/user-experience.md` §10, showing only structured values: PII *types*, incident
   type, injury, missing items, coverage lines, sentiment, indicators, risk level, teams, follow-up
   date, and saved path.
2. **AC-10.2**: **Given** `--trace`, **When** details are updated or help is requested, **Then** the
   trace shows that flow's steps: added, corrected, and pending fields plus routing for updates;
   categories, routed teams, and dates for help.
3. **AC-10.3**: **Given** `--trace`, **When** any step fails, **Then** the trace shows the failed
   step and error category, and still nothing else.
4. **AC-10.4**: **Given** any trace, **When** it is checked, **Then** it contains no narrative text,
   no model-written prose (opening lines, summaries, rationales), and no personal values, and it
   passes the same final privacy check as other output.
5. **AC-10.5**: **Given** the app is started **without** `--trace`, **When** any flow runs, **Then**
   no trace is printed (the customer view is unchanged). **And** with or without `--trace`, no
   trace is ever written to any file.

---

### User Story 11 - Adversarial end-to-end suite (Priority: P3)

A single, readable suite runs the hardest customer inputs through the **whole** pipeline and
proves the safety guarantees hold together, not just in isolation. It covers injection attempts,
PII in every position, contradictions, mixed incidents, near-empty and oversized input,
non-English text, customer-typed placeholders, and attempts to extract decisions. A live
adversarial evaluation confirms that the real model behaves.

**Why this priority**: Phases 001 and 002 tested each guarantee close to its code. This story tests
them as a customer would experience them, which is where regressions hide.

**Independent Test**: `uv run pytest -k ac_11` runs the scripted suite. `uv run pytest -m live -k
adversarial` runs the live set.

**Acceptance Scenarios**:

1. **AC-11.1**: **Given** each adversarial filing scenario (S17, S20, S21, S22, S24, S25, S26, S27
   from `docs/customer-scenarios.md`, plus an input just at and just over the 5,000-character
   limit), **When** it is filed end to end with scripted model answers, **Then** the reply, record,
   report, and log contain no personal values, no placeholders in the reply, and no decision
   language, and routing matches the catalog's expected outcome.
2. **AC-11.2**: **Given** adversarial updates and help requests (injection in an update, PII-only
   update, lawyer plus complaint, out-of-scope plus distress, a request to "approve my claim"),
   **When** processed end to end, **Then** the same guarantees hold and routing matches the rules.
3. **AC-11.3**: **Given** a live adversarial evaluation set of at least 12 fictional inputs, **When**
   run against the real model, **Then** no personal value survives in any output, no reply contains
   decision language, and every injection attempt is flagged (by the model or the phrase list).
4. **AC-11.4**: **Given** an update that only changes contact details, **When** it is saved,
   **Then** its history entry's detail reads `contact change requested` rather than being empty.
   *(Carried from phase 002 observation.)*

---

### User Story 12 - Release documentation (Priority: P4)

Someone who has never seen the project can understand what it does, run it, and see realistic
output in a few minutes. The README explains the product, setup, commands, and safety guarantees.
An architecture diagram shows the orchestrator, the four agents and their modes, the contracts
between them, and where rules decide. Curated sample reports show what staff actually receive.

**Why this priority**: The constitution defers the README and architecture diagram to the very end,
so they describe the system as built. It's last because it documents everything above.

**Independent Test**: Follow the README from a fresh clone in a scratch folder. Every command runs,
and every file it links exists.

**Acceptance Scenarios**:

1. **AC-12.1**: **Given** the README, **When** a reader follows its setup and run steps in a fresh
   folder, **Then** every command works as written, including `--load-samples` and `--trace`.
2. **AC-12.2**: **Given** the README, **When** it is checked, **Then** every relative link resolves
   to an existing file, and every command it shows is a real CLI option or test command.
3. **AC-12.3**: **Given** the architecture diagram, **When** it is viewed, **Then** it shows the
   menu/CLI, the orchestrator and flows, the four agents and their modes, the rules and privacy
   guard, storage, and the event log, and it matches the implemented modules. It is a Mermaid
   diagram in `docs/architecture.md`, with a summary version embedded in the README, both
   rendering on GitHub.
4. **AC-12.4**: **Given** `docs/samples/`, **When** it is checked, **Then** it contains at least one
   customer reply and staff report for filing, updating, and help (including one privacy-review and
   one escalation example), all fictional and free of personal values. Samples come from real-model
   runs (reviewed before committing), and an automated check verifies no personal values and the
   required reply and report sections, without comparing exact wording.

---

### Edge Cases

- **An unexpected error while saving:** no half-written record remains, because writes are atomic
  (phase 001). The claim number is released as in phase 001's failure handling.
- **Ctrl+C during a model call:** the claim isn't saved. A reserved number is released and no
  report is written for the interruption.
- **`--trace` together with `--load-samples`:** both apply.
- **A trace for the redirect-only help reply:** it shows the categories and "no team routed".
- **A very long single line at exactly 5,000 characters:** accepted. At 5,001: rejected with the
  limit message (phase 001 AC-5.6, now tested end to end).

## Requirements *(mandatory)*

### Functional Requirements

**Graceful failure (US9)**

- **FR-301**: The CLI MUST catch any unexpected exception from a menu task, show the AC-9.1
  message, write a status-only report with status `FAILED_UNEXPECTED`, and return to the menu.
  `ProcessingStatus` gains `FAILED_UNEXPECTED`. This adds to the constitution's list of failure
  statuses, which requires a constitution amendment (MINOR).
- **FR-302**: The CLI MUST treat end-of-input as Exit (AC-9.2) and Ctrl+C as an interruption
  (AC-9.3). Neither may show a traceback.
- **FR-303**: An interrupted or unexpectedly failed filing MUST release any claim number it
  reserved (reusing phase 001's failure handling).

**Trace mode (US10)**

- **FR-304**: `--trace` MUST print, after each reply, a sanitized trace built only from structured
  contract fields (enums, dates, counts, field names, file names), never from free text.
- **FR-305**: The trace MUST pass the FR-001 privacy check before it is printed.
- **FR-306**: Without `--trace`, the output MUST be identical to phase 002's.

**Adversarial suite (US11)**

- **FR-307**: The suite MUST run each listed scenario through the real orchestrator and flows, with
  scripted model answers, asserting on the reply, saved records, reports, and event log together.
- **FR-308**: A live adversarial set (≥ 12 inputs) MUST be added under `-m live`.
- **FR-309**: A contact-change-only update MUST record `contact change requested` as its history
  detail.

**Release documentation (US12)**

- **FR-310**: `README.md` MUST cover what the system does and doesn't do, setup (`uv`, `.env`),
  running (`claim-support`, `--load-samples`, `--trace`), the four menu options, the safety
  guarantees, testing (unit and live), project structure, the SDD/TDD process, and links to specs,
  the constitution, the UX walkthrough, the scenarios, and prompt history.
- **FR-311**: A Mermaid architecture diagram MUST exist in `docs/architecture.md`, with a summary
  version embedded in and linked from the README.
- **FR-312**: `docs/samples/` MUST contain curated, fictional sample replies and reports per
  AC-12.4.

### Key Entities

- **Trace Block**: a sanitized, structured summary of one flow's steps, derived only from existing
  contracts. It is printed to the terminal only, never stored.
- **Sample Output**: a committed markdown file pairing a customer reply with the matching staff
  report.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-301**: Across all automated failure-injection tests (unexpected error, end-of-input, and
  Ctrl+C at every prompt), 0 outputs contain a traceback or technical detail.
- **SC-302**: 100% of trace blocks in automated tests pass the privacy check and contain only
  structured values.
- **SC-303**: The adversarial suite covers at least 15 end-to-end scenarios, all passing.
- **SC-304**: In the live adversarial evaluation, 0 personal values survive, 0 replies contain
  decision language, and 100% of injection attempts are flagged.
- **SC-305**: A reader following the README from a fresh clone reaches a filed claim and a status
  check in under 10 minutes (manual quickstart check).
- **SC-306**: Every acceptance criterion AC-9.1 to AC-12.4 is verified by a named automated test,
  or, for documentation criteria that can't be automated (AC-12.1, AC-12.3), by a named quickstart
  step.

## Assumptions

- **Scope:** no new customer-facing features. Phase 003 hardens, exposes, and documents what
  exists. The local web UI remains the stretch phase 004.
- **Trace audience:** trace mode is for staff and reviewers running the app locally; it has no
  authentication, consistent with the rest of the product.
- **Sample outputs** are captured from real-model runs in a scratch folder, then reviewed and
  committed (clarify Q4). They are fictional, like all scenario data.
- **Ctrl+C exit code:** 130, the conventional code for an interrupted program (AC-9.3's
  "non-zero").
- **README** replaces the placeholder README from the initial commit.
