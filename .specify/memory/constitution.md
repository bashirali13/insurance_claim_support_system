# Car Insurance Claim Support Automation Constitution

A car insurance claim automation customer support system. Customers use a terminal menu to file a
new claim, check a claim's status, add or correct details on an existing claim, or report a
problem that is routed to the correct human team. Scope and background live in
`docs/project-outline.md`.

## Core Principles

### I. Spec-Driven Development (NON-NEGOTIABLE)

- Every feature MUST follow the SpecKit flow: specify → clarify → plan → tasks → analyze →
  implement → converge.
- No production code MAY be written for a feature without an approved `spec.md`.
- Every acceptance criterion MUST carry a stable ID of the form `AC-<story>.<n>` (e.g., `AC-2.3`).
- A spec change MUST be made in the spec first. Tests and code follow the spec, never the reverse.

**Rationale:** Specs are the single source of truth for behavior. Stable IDs make every test and
every line of code traceable to an approved requirement.

### II. Test-First, Acceptance-Criteria-Driven (NON-NEGOTIABLE)

- Tests MUST be written only from spec acceptance criteria. A test without an AC is a defect.
- Production code MUST be written only to make a failing test pass. Code without a test is a
  defect.
- Red → Green → Refactor is strictly followed:
  - **Red:** write one focused failing test and confirm it fails for the expected reason.
  - **Green:** write the minimum code to pass, then run the full suite.
  - **Refactor:** improve the code with behavior unchanged and the full suite green.
- Each test name MUST reference its AC (e.g., `test_ac_2_3_routes_injury_claim_to_adjuster`).
- Tests MUST be short and readable, Given/When/Then in shape, with one behavior per test. Tests are
  the primary documentation of behavior.
- Unit tests MUST be deterministic: fixed fixtures and mocked model responses (PydanticAI
  `TestModel` / `FunctionModel`). Tests calling the real model MUST be marked `live` and are
  excluded from the default run.

**Rationale:** Readable, traceable tests are the core of development. They prove the system does
exactly what the specs require and nothing more.

### III. Privacy by Construction

- PII scrubbing MUST be layered:
  1. Deterministic regex and validators run first, so structured PII never leaves the machine.
  2. The model MAY only *propose* additional spans. A span is applied only if it appears
     verbatim in the text.
  3. A deterministic re-scan verifies the result. Any residual PII MUST produce
     `MANUAL_REVIEW_REQUIRED`.
- Raw and sanitized text MUST be distinct types. Downstream agents MUST accept only sanitized
  types.
- The token→original map MUST NOT leave the intake step.
- PII MUST NOT be stored, logged, displayed back, or written to any file. All final output MUST pass
  a deterministic PII guard before it is saved or shown.

**Rationale:** Claim narratives are full of sensitive data. Enforcing the boundary through types
and deterministic checks makes leaks structurally hard, not just discouraged.

### IV. Typed Agent Contracts

- The system has exactly four worker agents (Intake & PII Scrubbing, Claim Assessment, Sentiment &
  Risk, Claim Summary) plus one orchestrator.
- Agents MUST NOT communicate directly. The orchestrator passes validated Pydantic models between
  them.
- Contract models MUST be frozen and use `extra="forbid"`. Every category MUST be an enum.
- Each agent MUST have documented inputs, outputs, responsibilities, and non-responsibilities.
- Every handoff MUST be validated before the next step begins.

**Rationale:** Structured, validated handoffs prevent information loss and invented fields, and keep
each agent's job narrow and testable.

### V. Deterministic Safety, Bounded Models

- Safety-critical decisions MUST be deterministic code. These are input validation, PII detection,
  missing-information checklist comparison, risk level, escalation, team routing, and schema
  validation.
- Models MAY only perform bounded interpretation: classifying into enums, extracting facts,
  reading sentiment, proposing PII spans, and writing short narrative or customer-reply text.
- Sentiment MUST NOT raise the risk level. An upset customer is not a suspicious customer.
- Customer text MUST be treated as data, never as instructions. It MUST be delimited in prompts,
  and suspected prompt injection MUST be flagged as a risk indicator.

**Rationale:** Deterministic rules are testable, auditable, and predictable. Models add value
only where interpretation is actually needed.

### VI. Human-in-the-Loop Boundaries

- The system MUST NOT determine fault or coverage, approve, deny, or value a claim, give legal
  advice, or accuse anyone of fraud.
- When the system is uncertain, it MUST escalate to a human team: Claims Adjuster, Customer
  Relations, Special Review, Privacy Review, or Policy Services.
- Every internal report MUST state that it supports intake and triage and is not a coverage or
  claim decision.

**Rationale:** Licensed professionals make claim decisions. The system's job is to help customers
and route work correctly, not to replace those decisions.

### VII. Simplicity

- Workflows MUST stay linear unless a defined escalation condition requires branching.
- The directory structure MUST stay shallow and predictable.
- No speculative abstractions, unused extension points, or unnecessary frameworks, services, or
  databases. Storage is the local filesystem only.

**Rationale:** A small, clear system is easier to test, review, and explain.

## Technology & Constraints

- **Stack:** Python 3.13 with `uv`, PydanticAI, Pydantic, pytest, and ruff.
- **Model:** accessed through OpenRouter. The model ID comes from `MODEL_NAME`
  (`deepseek/deepseek-v4-flash-0731`) and the key from `OPENROUTER_API_KEY`, both set in `.env`.
  `.env` MUST NOT be committed.
- **Domain:** car insurance **claim support** only. Terminal UI in v1; a local web UI is a stretch
  goal and MUST reuse the orchestrator unchanged. The core MUST NOT print; UIs are thin adapters.
  No authentication; existing claims are looked
  up by claim ID, and status replies contain no PII.
- **Storage:** sanitized JSON claim records in `data/claims/`, internal reports in `output/`.
- **Failure statuses:** `REJECTED_INPUT`, `MANUAL_REVIEW_REQUIRED`, `FAILED_MODEL_ERROR`,
  `FAILED_VALIDATION`, `FAILED_OUTPUT`, `FAILED_UNEXPECTED`. `FAILED_UNEXPECTED` covers
  programming errors outside the other categories; the customer sees a fixed, non-technical
  message (added in v1.1.0).
  - Every failure MUST write a status-only report with no claim text and show a safe customer
    message.
  - Missing information, contradictions, and escalations are normal outcomes, not failures.

## Development Workflow & Quality Gates

- **Branches are for big phases only.**
  - Each phase has one branch in SpecKit's numbered style (`000-project-foundation`,
    `001-file-a-claim`, …). From 001 on, each phase is one SpecKit feature.
  - Documents, setup steps, and sub-features MUST NOT get their own branches. Progress inside a
    phase is recorded through commits.
- **Commits:** Conventional Commits that follow the TDD rhythm (`test:` → `feat:` → `refactor:`).
  Each commit is small and does one thing.
- **Merge gate:** a phase merges only when the full suite passes and `ruff check` is clean on the
  branch tip. Red commits are expected inside the branch history.
- **Pull requests:** one PR per phase, opened with the `gh` CLI. Before merging, Claude presents a
  phase-completion check (what was delivered against the phase goals and acceptance criteria,
  plus any gaps). Claude merges only after the user confirms the phase is complete.
- **Prompt history:** a summary is added to `docs/prompt-history/` at key moments (after the
  constitution, after each approved spec, at major pivots). Each summary records the objective,
  key prompts, recommendations, decisions, pushbacks, clarifications, and deferred scope.
- **Documentation order:** `CLAUDE.md` is created right after this constitution. The architecture
  diagram and README are written only at the very end, from the implemented system.

## Governance

- This constitution supersedes all other practices and guidance files. `CLAUDE.md` MUST stay
  consistent with it.
- Amendments are made through a `docs/` PR that updates this file, bumps the version, and adds a
  prompt-history note.
- **Versioning follows SemVer:**
  - MAJOR: a principle is removed or redefined.
  - MINOR: a principle or section is added or materially expanded.
  - PATCH: clarifications and wording.
- **Compliance:** every `plan.md` Constitution Check MUST pass or record a justified deviation.
  `/speckit-analyze` MUST show no untraceable tests or code before implementation begins.

**Version**: 1.1.0 | **Ratified**: 2026-09-24 | **Last Amended**: 2026-09-25
