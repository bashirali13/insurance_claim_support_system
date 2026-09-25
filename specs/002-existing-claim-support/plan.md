# Implementation Plan: Existing-Claim Support

**Branch**: `002-existing-claim-support` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-existing-claim-support/spec.md` (approved; 5
clarifications; 2 plan-time consistency fixes: FR-218 vs AC-6.8, and new AC-8.12)

## Summary

This phase turns on menu options 2–4, reusing phase 001's pipeline pieces:

- **Check status (US6)** is a pure template over the saved record, with no model call and no
  writes. Six committed sample claims can be loaded with `--load-samples`.
- **Add or correct details (US7)** adds an *update mode* to the Claim Assessment agent. It returns
  the full updated facts; **code** diffs them against the saved facts into added, corrected, and
  sensitive changes. Sensitive changes are held as pending adjuster confirmations. Phase 001's
  rules then recompute everything, with teams replaced and escalation never undone.
- **Get help (US8)** adds a *help mode* to the Sentiment & Risk agent (1–3 request categories). A
  rule table routes each category to teams with dates. Out-of-scope and "how do I file" requests
  get fixed replies with no reference.

Every model step keeps phase 001's safeguards: tagged narrative, narrow output, a validator on
customer-facing model text, the final privacy guard, retries, and safe failure messages.

## Technical Context

**Language/Version**: Python 3.13 (uv)

**Primary Dependencies**: unchanged from phase 001: `pydantic`, `pydantic-ai-slim[openai]`
(OpenRouter), `python-dotenv`; dev `pytest`, `ruff`. `argparse` (standard library) handles
`--load-samples`.

**Storage**: local files:
- `data/samples/` (committed)
- `data/claims/` and `data/help/` (gitignored)
- `output/` and `logs/` (gitignored)

**Testing**: pytest with `FunctionModel`-scripted agents and model requests blocked. The `-m live`
evaluation adds `update_cases.json` and `help_cases.json`.

**Target Platform / Project Type**: local terminal; a single-project CLI over a UI-agnostic core.

**Performance Goals**:
- status check under 1 s with 0 model calls (SC-201)
- update: 3 model calls; help: 3 model calls. Both are fewer than filing's 4.

**Constraints**:
- no PII in any output
- the core never prints
- routing, status, dates, and the diff are rules; the model never decides them

**Scale/Scope**: one customer per session; hundreds of claim and help files.

**Terminology**: "AI assistant" (spec) = the model behind an agent (plan). "Mode" = a separate
agent instance with its own instructions and output type, serving the same constitutional role.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|---|---|---|---|
| I. Spec-Driven | Approved spec with AC IDs; spec changes made first | ✅ approved; plan-time fixes (FR-218, AC-8.12) edited spec-first | ✅ every design element traces to an FR or AC |
| II. Test-First, AC-driven | Tests only from ACs; no code without a test | ✅ | ✅ 33 ACs; AC-5.13 field-list change handled test-first (research R9) |
| III. Privacy by Construction | Layered PII on new text; guard on every output; no values in history or pending changes | ✅ | ✅ update and help text reuse `intake.scrub`; history stores field names only; guard covers claim and help records |
| IV. Typed Agent Contracts | Four agents plus the orchestrator; frozen contracts; enums | ✅ | ✅ new instances are *modes* of the same roles (research R1); all new models are `Contract`s |
| V. Deterministic Safety | Rules own routing, status, dates, and change detection | ✅ | ✅ `diff_facts`, `status_after_update`, `help_routing` are pure rules; sentiment never raises risk |
| VI. Human-in-the-Loop | No fault or coverage statements; escalate when uncertain | ✅ | ✅ sensitive corrections held for an adjuster; `ESCALATED` never de-escalates; Special Review never shown |
| VII. Simplicity | Linear flows; shallow tree; no new frameworks | ✅ | ✅ one new module (`existing_claims.py`), one small validation module; standard-library `argparse` |

**Result: PASS.** Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-existing-claim-support/
├── spec.md, plan.md, research.md (R1–R11), data-model.md, quickstart.md
├── contracts/  cli.md · agents.md · files.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (changes)

```text
src/claim_intake/
├── contracts.py            # + MenuTask, RequestCategory, PendingChange, UpdateLlmOutput, FieldChange,
│                           #   FactChanges, HelpTriageLlmOutput, HelpReplyLlmOutput, TeamPromise, HelpRecord;
│                           #   ClaimStatus/Team/HistoryEntry/ClaimRecord/EventLogEntry extended (defaults keep 001 records valid)
├── rules.py                # + normalize_claim_number, diff_facts, status_after_update, help_routing
├── reporting.py            # + render_status, render_update_reply/report, render_help_reply/report;
│                           #   status-only report takes task wording
├── storage.py              # + NumberedFiles (shared CLM/HELP numbering), HelpStore, load_samples
├── orchestration.py        # _Run gains `task`; file_claim logs FILE_CLAIM
├── existing_claims.py      # NEW: check_status, update_claim, get_help
├── cli.py                  # options 2–4 flows, claim-number prompts, --load-samples
└── agents/
    ├── __init__.py         # + assessment_update, help_triage, help_reply instances
    ├── assessment.py       # + update-mode agent and update()
    ├── risk.py             # + help-mode agent and triage()
    ├── summary.py          # + help-reply agent and help_opening(); uses shared validator
    └── validation.py       # NEW: shared customer-text validator (moved from summary.py)
data/samples/CLM-2026-000{1..6}.json   # NEW, committed
tests/
├── unit/  test_status.py · test_update_rules.py · test_help_rules.py · test_samples.py
│          (+ additions to test_storage.py, test_reporting.py, test_assessment.py, test_risk.py, test_summary.py)
├── integration/  test_update_claim.py · test_get_help.py · (+ test_cli.py options 2–4)
└── live/  test_live_eval.py (+ SC-203, SC-204) · fixtures update_cases.json, help_cases.json
```

**Structure Decision**: this keeps phase 001's flat module layout. The only additions are
`existing_claims.py`, which holds the three new flows and shares `_Run` so failure handling isn't
duplicated, and `agents/validation.py`, which is shared by the summary and help-reply agents.

## Implementation Order (for /speckit-tasks)

Each step is Red → Green → Refactor.

1. **Foundation:**
   - gitignore `data/claims/` and `data/help/`
   - event log `task` (update the AC-5.13 test first)
   - status-only report task wording
   - backward-compatible `ClaimRecord` and `HistoryEntry` extensions
2. **US6 (P1):**
   - `normalize_claim_number`, sample claims and `load_samples`
   - `render_status`, `check_status`
   - CLI option 2 and `--load-samples`
3. **US7 (P2):**
   - `diff_facts`, `status_after_update`, follow-up combination
   - update-mode agent
   - update templates
   - `update_claim` (normal, no-change, privacy, failure)
   - CLI option 3 (closed and privacy-review refusals)
4. **US8 (P3):**
   - `help_routing`, the help-triage and help-reply agents (shared validator)
   - `NumberedFiles`, `HelpStore`
   - help templates
   - `get_help` (routed, redirect-only, privacy, claim linking)
   - CLI option 4
5. **Live and polish:**
   - `update_cases.json` and `help_cases.json`, live SC-203 and SC-204
   - update the scenario catalog's E-numbers to the sample claims
   - quickstart walkthrough, prompt history 06, phase PR

## Complexity Tracking

No constitution violations to justify.
