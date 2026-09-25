# Research: Existing-Claim Support (002)

This phase builds on phase 001's verified stack: PydanticAI 2.49 with `OpenRouterModel`,
`FunctionModel` in tests, and live-proven tool-call structured output with DeepSeek (see
`specs/001-file-a-claim/research.md` R1–R14). Every decision below reuses those patterns; no new
dependencies are needed.

---

## R1. Agent modes without a fifth agent

- **Decision:** add three new `Agent` *instances* that keep the constitution's four roles:

  | Role (constitution) | Existing instance | New instance (this phase) | Output type |
  |---|---|---|---|
  | Claim Assessment | `assessment` | `assessment_update` | `UpdateLlmOutput` |
  | Sentiment & Risk | `risk` | `help_triage` | `HelpTriageLlmOutput` |
  | Claim Summary | `summary` | `help_reply` | `HelpReplyLlmOutput` |

  All are registered in `create_agents(model)` so tests still swap one model.
- **Rationale:** different instructions and output types per task keep each model output narrow
  (phase 001 R3). Roles and responsibilities are unchanged.
- **Alternatives:** a single agent with a mode flag in the prompt (the output types would widen and
  become optional, weakening validation); a new "Help agent" (breaks the four-agent rule).

## R2. Deciding what an update changed: code, not the model (FR-207)

- **Decision:** the update model returns the **full updated facts** (`AssessmentLlmOutput`) plus
  `contact_change_requested`. The pure function `rules.diff_facts(saved, updated) -> FactChanges`
  compares them field by field:

  | Field kind | Added | Corrected |
  |---|---|---|
  | `str \| None` (date, location) | `None` → value | value → different value, or value → `None` |
  | `TriState` | `UNKNOWN` → `YES`/`NO` | `YES` ↔ `NO`, or known → `UNKNOWN` |
  | `incident_type` | `UNKNOWN` → a specific type | one specific type → another |
  | `um_uim_subtype` | `None` → subtype | subtype → different subtype or `None` |
  | `damage_areas` | each new item | removed items are ignored (never shrink the list) |
  | `key_facts`, `contradictions` | not diffed for the customer; new items appended (key facts capped at 6, newest kept) | — |

- **Sensitive = a *correction* to a sensitive field.** The sensitive fields are `incident_type`,
  `um_uim_subtype`, `customer_side_injured`, `others_injured`, and `other_party_involved`.
  **Additions** to those fields apply immediately. For example, a newly reported injury
  (`UNKNOWN` → `YES`) raises urgency right away rather than waiting for confirmation; holding it
  back would slow help for an injured customer. This is how AC-7.4's "changes a sensitive fact"
  is read: *changing* a known fact, which is what the spec's example ("actually nobody was hurt")
  does.
- **Applying:** non-sensitive changes and all additions go into the saved facts. Sensitive
  corrections become `PendingChange`s, and the saved value stays.
- **Rationale:** deterministic, fully unit-testable (SC-202), and the model can't misreport what it
  changed. The diff is also the source of the reply's "Added" and "Corrected" lines.
- **Alternatives:** having the model list its own changes (unverifiable, and it drifts from the
  facts it returns).

## R3. Routing and status after an update (FR-208 to FR-210)

- **Decision:** `update_claim` re-runs phase 001's rules on the *applied* facts:
  `injury_present`, `missing_information`, `coverage_lines`, and `indicators`. The last of these
  uses a fresh `RiskLlmOutput` from the existing `risk` agent on the update text (sentiment, legal
  and injection flags). The results then combine as follows:
  - **Teams** = `rules.teams(...)` **replaced** (clarify Q5), plus `CLAIMS_ADJUSTER` if any change
    is pending, plus `POLICY_SERVICES` if a contact change was requested.
  - **Follow-up:** each promise gets its own date (routing: 1 or 2 days; pending: 1; contact: 3).
    The claim's single `follow_up_date` is the **earliest** of them. The reply shows each promise
    on its own line.
  - **Status:** `rules.status_after_update(current, level, missing)` implements FR-208's priority.
- **Rationale:** it reuses tested rules unchanged, and one function per decision keeps the tests
  small.

## R4. Help triage and routing (FR-212 to FR-215)

- **Decision:** `HelpTriageLlmOutput` = `sentiment`, `categories` (1–3 `RequestCategory`),
  `legal_representation_mentioned`, `possible_prompt_injection`, and `rationale` (≤ 300 chars).
  `rules.help_routing(triage, text)` returns a list of `TeamPromise(team, business_days)`:
  - It follows FR-213's table, with injection detection = model flag **or** the phase 001 phrase
    list.
  - Teams are deduplicated, keeping the smallest number of days.
  - When legal representation or injection is present, every routed team's promise becomes 1 day.
- **Out of scope and file-a-claim:** these categories route no team. If routing is empty, no
  reference number and no record are created, and the reply is the redirect or option-1 line. The
  exception is distress (`DISTRESSED`/`ANGRY`), which always routes Customer Relations.

## R5. Reference numbers for help requests

- **Decision:** generalize phase 001's claim-number reservation into
  `NumberedFiles(dir, prefix)`, used by both `ClaimStore` (`CLM`) and the new `HelpStore`
  (`HELP`, in `data/help/`). It works the same way: scan, then exclusive create, so numbers are
  unique across restarts.
- **Rationale:** one proven mechanism, now shared (a refactor under green tests).

## R6. Customer-facing text in this phase

- **Status replies and update replies are 100% templates**, with no model call. That makes them
  cheaper, instant, and fully deterministic.
- **Help replies** use one model-written `opening_line` (the `help_reply` instance), checked by the
  **same validator** as phase 001's summary (placeholders, PII, decision words). The validator is
  factored into `agents/validation.py` and shared. The rest of the help reply is a template.

## R7. Sample claims and runtime data (FR-204, FR-204a)

- **Decision:**
  - Six `ClaimRecord` JSON files live in `data/samples/`. They're hand-written, fictional,
    validated by the `ClaimRecord` model in a test, and derived from customer-scenario catalog
    entries:
    - `0001` S01 rear-end, `UNDER_REVIEW`
    - `0002` S04 theft, `AWAITING_INFORMATION`
    - `0003` S06 hail, `SUBMITTED`
    - `0004` S08 glass, `CLOSED`
    - `0005` S10 hit-and-run with injury, `ESCALATED`, police report missing
    - `0006` privacy review, `ESCALATED`, no assessment
  - `storage.load_samples(root) -> list[str]` copies only missing files.
  - `cli.main()` accepts `--load-samples` (via `argparse`, standard library).
  - `.gitignore` gains `data/claims/` and `data/help/`.
- **Rationale:** explicit, idempotent, and never touches real claims (clarify Q3).

## R8. Claim records from phase 001 stay readable

- **Decision:**
  - New `ClaimRecord` fields have defaults: `pending_changes: list[PendingChange] = []`.
  - `HistoryEntry` gains an optional `detail: str | None = None` (changed field names or a help
    reference) and new event literals.
  - Phase 001 records therefore load unchanged.
- **Rationale:** backward compatibility without a migration step.

## R9. Event log `task` field (FR-218)

- **Decision:**
  - `EventLogEntry.task: MenuTask` (`FILE_CLAIM`, `UPDATE_DETAILS`, `GET_HELP`), set by each flow.
  - Status checks don't log (AC-6.8).
  - Phase 001's `test_ac_5_13_event_log_lines_have_only_allowed_fields` is updated **test-first**
    to include `task` (FR-218 amends AC-5.13's field list).

## R10. Where the new flows live

- **Decision:** new module `src/claim_intake/existing_claims.py` with `check_status`,
  `update_claim`, and `get_help`. It reuses `orchestration._Run` for event logging, step failure
  mapping, retries, and status-only reports. `_Run` gains a `task` attribute, and the status-only
  report takes the task wording.
- **Rationale:** it keeps `orchestration.py` focused on filing, avoids duplicating the
  failure-handling machinery, and follows the plan's flat-module style.
- **Alternatives:** growing `orchestration.py` to around 500 lines (harder to read), or copying
  `_Run` (duplication).

## R11. Evaluation sets for the new model steps (SC-203, SC-204)

- **Decision:**
  - `tests/fixtures/narratives/update_cases.json`: ≥ 12 cases, each a saved-claim fixture plus
    update text plus the expected changed fields.
  - `help_cases.json`: ≥ 14 cases with the expected categories.
  - Both are seeded from catalog E04–E12 with variants, and run under `-m live`.
