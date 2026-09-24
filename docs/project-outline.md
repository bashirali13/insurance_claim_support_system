# Car Insurance Claim Support Automation

## Project Summary

A **car insurance claim automation customer support system**. Customers use a simple terminal menu to **file a new claim** (First Notice of Loss, FNOL) or **get help with an existing claim**: checking its status, adding or correcting details, or reporting a problem that needs a human team.

Behind the menu, an orchestrator coordinates four specialized AI agents. They scrub personally identifiable information (PII), classify and assess the claim, analyze customer sentiment and risk, route escalations to the correct team, and produce two outputs: a short **customer-facing reply** and a standardized **internal markdown report** for claims staff.

The scope is intentionally limited to intake, customer support, and triage. The system does not adjudicate claims, determine fault, interpret policy coverage, approve payments, or replace licensed claims professionals.

## Goal

Create an AI car insurance claim support coordinator capable of:

- Filing new car insurance claims from a free-text description
- Looking up the status of an existing claim by claim ID
- Adding or correcting details on an existing claim
- Receiving customer problems or complaints and routing them to the correct team
- Removing sensitive customer information before it is stored or sent downstream
- Classifying claim types and extracting essential claim facts
- Identifying missing or contradictory information, including contradictions with earlier submissions
- Performing customer sentiment analysis
- Identifying predefined risk indicators and recommending human escalation
- Replying to the customer in plain language
- Saving a sanitized claim record and an internal markdown report to disk

## Users and Interaction Model

- **Primary user:** the customer (policyholder or claimant), typing into the terminal.
- **Secondary audience:** claims staff, who read the internal markdown reports.
- **Interaction:** a **menu** selects the task, so requests are never misrouted. Within each task the customer describes things **in their own words**, and the agents adapt to that free text.
- **One-shot per task (v1):** each submission gets one response. When details are missing, the reply lists them under "What we still need from you" and does not start a back-and-forth conversation.
- **When uncertain, escalate:** if the system can't safely handle a request, it routes it to a human team and doesn't guess.

## Menu Tasks (v1)

| # | Task | Customer provides | System does |
|---|------|-------------------|-------------|
| 1 | File a new claim | Free-text description of what happened | Full pipeline; creates a new claim record and ID |
| 2 | Check claim status | Claim ID | Deterministic lookup; plain-language status reply with no model call required |
| 3 | Add or correct details | Claim ID + free text | Scrubs, assesses the update against the existing record, flags new contradictions, appends to claim history |
| 4 | Get help with my claim | Claim ID (optional) + free text | Scrubs, categorizes the claim-related request (complaint, delay, claim question, talk to an adjuster, contact change), routes each part to the correct team with a follow-up date |

**Claim support only.** Out of scope: payments, billing, policy changes, rentals, towing, repair-shop booking, claim cancellation, and multi-turn conversations. Out-of-scope requests get a polite reply that points to the right channel.

The full customer-facing walkthrough, with terminal mockups and what happens behind the scenes, is in [`docs/user-experience.md`](user-experience.md).

## Coverage Baseline and Incident Types (Car Only)

The system's vocabulary is based on the coverages most US auto insurers offer:

- **Six core coverages:** liability (bodily injury and property damage), collision, comprehensive, uninsured/underinsured motorist, personal injury protection (PIP), and medical payments (MedPay).
- **Add-ons** (rental, towing, gap) are out of scope. Their underlying facts (vehicle drivable, possible total loss) are still recorded for the adjuster.

The details are in `docs/user-experience.md` §1.

- **The model extracts facts.** Deterministic code maps those facts to **coverage lines to review** (e.g., "other driver fled" → UM/UIM; "passenger hurt" → PIP/MedPay; "hit a fence" → liability property damage).
- **The system has no policy data** and never says whether something is covered.

**Incident types** (what happened):
- **Collision:** with another vehicle or an object, or a rollover
- **Theft:** whole vehicle or parts or contents
- **Vandalism**
- **Weather:** hail, flood, wind, falling tree
- **Fire**
- **Glass**
- **Animal strike**
- **Unknown:** not enough information to classify
- **Mixed:** multiple unrelated incidents; one claim is created and an adjuster separates them

Liability and UM/UIM are **coverage lines triggered by facts about other parties**, not incident types. For example, a hit-and-run is a `COLLISION` with the UM/UIM line triggered.

### Uninsured / Underinsured Motorist (UM/UIM)

Researched from insurer and regulator consumer guidance (sources below). UM/UIM claims are filed under the customer's **own** policy when the at-fault driver can't pay:

- **Uninsured:** the other driver has no insurance.
- **Hit-and-run / unknown driver:** the other driver or vehicle can't be identified.
- **Coverage denied:** the other driver's insurer has denied their coverage.
- **Underinsured:** the other driver's liability limits are too low to cover the damages.

Coverage splits into **bodily injury (UMBI/UIMBI)** and **property damage (UMPD/UIMPD)**. That split maps to our `injury_present` fact and the damage facts.

Intake-relevant facts to collect (flagged as missing when absent):

- Which sub-type applies (uninsured, hit-and-run, denied, underinsured)
- Whether a **police report** was filed and the report number (most insurers require prompt police reporting, and hit-and-run claims especially depend on it)
- The other driver's identity and insurer, if known
- For underinsured claims: whether the other driver's insurer has already offered a settlement

The system must **not** decide fault or coverage. Rules vary by state: some require the other driver to be 100% at fault, and some states' UMPD excludes hit-and-run. The system records these facts and routes the claim. UM/UIM claims with injuries, a missing police report on a hit-and-run, or a pending settlement offer from the other insurer are escalated to a human adjuster.

Sources: [Maryland Insurance Administration: What You Need to Know About Uninsured Motorist Claims](https://insurance.maryland.gov/Consumer/Documents/publications/ConsumerAdvisory-What-You-Need-To-Know-About-Uninsured-Motorist-Claims.pdf), [Progressive: UM/UIM](https://www.progressive.com/answers/uninsured-motorist-insurance/), [GEICO: UM/UIM](https://www.geico.com/information/aboutinsurance/auto/uninsured-underinsured-motorist/), [Allstate: UM/UIM](https://www.allstate.com/resources/car-insurance/uninsured-motorist-coverage).

## Guiding Principles

- Keep the project simple, focused, and easy to navigate.
- Use four worker agents plus one orchestrator.
- Keep each workflow linear unless a defined escalation condition requires branching.
- Give every agent explicit inputs, outputs, responsibilities, and non-responsibilities.
- Use Pydantic models at every agent boundary to prevent information loss.
- Enforce the PII boundary with types: downstream agents accept only sanitized types.
- Prefer deterministic rules for safety-critical checks such as PII detection, risk level, escalation, and schema validation.
- Use models only for bounded interpretation tasks.
- Follow spec-driven development: acceptance criteria → tests → code. Implement only behavior required by approved specifications and failing tests.
- Do not introduce unnecessary frameworks, services, databases, or abstractions.

## Agent Architecture

The real project team roles map directly to the software agents. The orchestrator coordinates the workflow but does not make specialist decisions.

| Task | Intake & PII | Assessment | Sentiment & Risk | Summary |
|------|:---:|:---:|:---:|:---:|
| File a new claim | ✓ | ✓ | ✓ | ✓ |
| Check claim status | — | — | — | template only |
| Add or correct details | ✓ | ✓ (update mode) | ✓ | ✓ |
| Get help with my claim | ✓ | — | ✓ (request categories) | ✓ |

### Orchestrator

**Background:** Claims Operations Manager

**Responsibilities:**

- Present the menu and run the workflow for the selected task
- Validate input before any model call (empty, whitespace-only, over the length cap)
- Pass validated Pydantic objects between agents
- Maintain workflow state, processing status, and failures
- Stop or redirect processing when validation fails
- Load and save sanitized claim records
- Save the internal report and display the customer reply

**Non-responsibilities:** interpret claim facts, scrub PII, classify, assess sentiment or risk, write report content.

### Intake and PII Scrubbing Agent

**Background:** Claims Intake Specialist

**Responsibilities:**

- Normalize raw submissions
- Scrub PII using the **layered approach** (below)
- Replace PII with stable redaction tokens
- Extract basic intake facts (date, location, vehicles, parties mentioned)
- Return sanitized content for downstream processing
- Request manual review when safe sanitization can't be confirmed

**Non-responsibilities:** classify the claim, assess sentiment or risk, recommend escalation, generate the report.

#### Layered PII Scrubbing

1. **Deterministic first:** regex plus validators detect structured PII: SSN, payment card numbers (Luhn-checked), email, phone, date of birth, driver's license number, VIN, license plate, policy number, and street address. This is the non-negotiable baseline, and structured PII **never leaves the machine**.
2. **Agent-assisted second:** the model reviews the pre-redacted text and *proposes* additional spans, such as names or informal location descriptions. It never rewrites the text.
3. **Code applies:** a proposed span is redacted only if it appears verbatim in the text.
4. **Verify:** detectors re-run on the sanitized output. Any residual hit sets `requires_manual_review` and routes the request to privacy review.

Tokens are stable within a submission (`[PERSON_1]`, `[PHONE_1]`). The token→original map stays inside the intake step and is never passed downstream, stored, or written to disk.

### Claim Assessment Agent

**Background:** Claims Adjuster

**Responsibilities:**

- Determine the supported claim type
- Extract incident, damage, and injury facts
- Identify missing information against a per-claim-type checklist (the checklist comparison is deterministic)
- Identify contradictory statements, quoting both statements
- **Update mode:** compare new details against the existing claim record, separating new facts, corrections, and new contradictions

**Non-responsibilities:** handle raw PII, determine sentiment, make fraud conclusions, determine fault, interpret coverage, approve or deny claims, generate the report.

### Sentiment and Risk Agent

**Background:** Fraud and Customer Experience Analyst

**Responsibilities:**

- Classify customer sentiment
- Select predefined risk indicators from a fixed list
- For problem reports: categorize the issue so it can be routed
- Provide a concise rationale grounded in claim facts

Risk level, escalation, and the target team are **computed deterministically** from the selected indicators and categories. They are not left to the model.

**Sentiment is kept separate from risk.** An upset customer is not a suspicious customer. Distress can trigger a customer-care escalation but never raises the risk level.

**Non-responsibilities:** determine claim type, handle raw PII, approve or deny, interpret coverage, make legal conclusions, produce the report.

### Claim Summary Agent

**Background:** Senior Claims Coordinator

**Responsibilities:**

- Combine validated outputs from the other agents
- Render the internal markdown report from a **template** using the structured data; the model writes only the short narrative summary paragraph
- Write the plain-language customer reply, including next steps and "What we still need from you"
- Distinguish known, missing, contradictory, and flagged information
- Confirm PII scrubbing status and never reintroduce scrubbed information (a final detector pass guards this)

**Non-responsibilities:** change upstream classifications, perform new analysis, approve, deny, or value the claim.

## Escalation and Routing

Routing is deterministic, based on indicators and categories:

| Team | Receives |
|------|----------|
| Claims Adjuster | Injury claims, UM/UIM escalations, contradictions, mixed incidents |
| Customer Relations | Complaints, service delays, customer distress |
| Special Review | Configured risk indicators (never labeled as fraud) |
| Privacy Review | PII that couldn't be safely confirmed as scrubbed |
| Policy Services | Contact-information change requests (the value is redacted; a human completes the update) |

Every routed request gets a realistic follow-up date computed by code (1–3 business days by urgency, weekends skipped). See `docs/user-experience.md` §2.

## Core Contracts (Provisional)

Final names and fields are set in SpecKit specs and plans. All contracts use `frozen=True, extra="forbid"`, and every category is a `StrEnum`.

```python
class RawSubmission(BaseModel):  # orchestrator + intake agent only
    task: MenuTask
    text: str
    claim_id: str | None


class SanitizedSubmission(BaseModel):  # the only text type downstream agents accept
    task: MenuTask
    text: str
    claim_id: str | None
    pii_types_removed: list[PiiType]
    requires_manual_review: bool


class ClaimAssessment(BaseModel):
    incident_type: IncidentType
    um_uim_subtype: UmUimSubtype | None
    damage_types: list[DamageType]
    injury_present: bool | None
    other_party_involved: bool | None
    vehicle_drivable: bool | None
    key_facts: list[str]
    missing_information: list[str]  # computed by per-incident checklist
    contradictions: list[str]
    coverage_lines_to_review: list[CoverageLine]  # computed by rules from facts


class RiskAssessment(BaseModel):
    sentiment: Sentiment
    risk_indicators: list[RiskIndicator]
    request_categories: list[RequestCategory]  # "Get help" task only
    risk_level: RiskLevel  # computed by rules
    escalation_teams: list[EscalationTeam]  # computed by rules
    rationale: str


class ClaimRecord(BaseModel):  # persisted as sanitized JSON only
    claim_id: str
    status: ClaimStatus
    incident_type: IncidentType
    history: list[ClaimHistoryEntry]


class TaskResult(BaseModel):
    processing_status: ProcessingStatus
    customer_reply: str
    report_path: str | None
```

## Failure Behavior

| Category | Examples | Status |
|----------|----------|--------|
| Config | Missing API key or model name | Fail fast at startup |
| Input | Empty, whitespace-only, over length cap, unknown claim ID | `REJECTED_INPUT` (no model call) |
| Safety | Residual PII after scrubbing; PII detected in final output | `MANUAL_REVIEW_REQUIRED` |
| Model | Timeout, rate limit, network or auth error (after 1–2 retries) | `FAILED_MODEL_ERROR` |
| Validation | Schema violation or unsupported category (after retries) | `FAILED_VALIDATION` |
| Output | Report or record can't be written | `FAILED_OUTPUT` |

Every failure writes a **status-only report** (claim ID, status, failed step, error category, and no claim text) and shows the customer a safe, polite message. Missing information, contradictions, and escalations are **normal outcomes**, not failures.

## Explicitly Out of Scope

- Home, property, or non-auto insurance
- Fault determination, coverage determination, claim approval or denial
- Settlement calculation or payment
- Legal advice or conclusions
- Autonomous fraud accusations
- External web search, external databases, production insurance integrations
- User authentication (claim ID lookup only; status replies contain no PII)
- Web UI in v1 (a local web UI is a **stretch goal** after phase 003)
- Storing PII of any kind

## Technology Stack

- **Language:** Python 3.13, managed with `uv`
- **SDD:** SpecKit (Claude Code integration)
- **Agent framework:** PydanticAI
- **Validation:** Pydantic
- **Model:** `deepseek/deepseek-v4-flash-0731` through OpenRouter (configured via `OPENROUTER_API_KEY` and `MODEL_NAME` in `.env`)
- **Testing:** pytest (tests that hit the real model are marked `live` and excluded by default)
- **Interface:** simple terminal menu
- **Storage:** local filesystem only: sanitized claim records in `data/claims/`, reports in `output/`

## Development Phases

Branches exist **only for big phases**, one branch and one PR each. Inside a phase, progress is
recorded through well-described commits. Each phase from 001 onward is one SpecKit feature whose
user stories are ordered by priority.

| Phase branch | Contents |
|---|---|
| **000-project-foundation** | Outline, tooling, constitution, CLAUDE.md, UX walkthrough, prompt history |
| **001-file-a-claim** | Menu shell; contracts; orchestrator; layered PII scrubbing; assessment with coverage-line rules; sentiment and risk with routing; summary reply and report; sanitized claim record. Stories, in order: P1 PII scrubbing → P2 claim assessment → P3 risk and routing → P4 customer reply and report → P5 end-to-end "File a new claim" |
| **002-existing-claim-support** | Seeded sample claims; Check status; Add or correct details (update mode, history, contact-change routing); Get help (request categories, multi-team routing) |
| **003-hardening-and-release** | End-to-end adversarial suite, `--trace` staff mode (moved earlier only if debugging needs it), sample reports, architecture diagram, README |
| *Stretch: 004-local-web-ui* | Minimal localhost page with the same four tasks, reusing the orchestrator unchanged (the core never prints; terminal and web are thin adapters) |

## Development Process

- **Spec-driven:** every feature goes through the SpecKit flow: specify → clarify → plan → tasks → analyze → implement → converge.
- **Test-driven:** tests are written **only** from spec acceptance criteria, and code is written **only** to pass tests. Each acceptance criterion has an ID (`AC-2.3`), and each test names the criterion it covers (`test_ac_2_3_…`).
- **Red, Green, Refactor:**
  - **Red:** one focused failing test, using fixed fixtures and mocked model responses; confirm it fails for the expected reason.
  - **Green:** the minimum code to pass; run the focused test, then the full suite.
  - **Refactor:** improve naming, prompts, and boundaries with behavior preserved and the full suite green.
- **Readable tests:** tests are the core of development and must be easy to understand at a glance.

## Initial Happy-Path Tests

- Redacts supported PII while keeping the narrative usable
- Classifies a clear collision claim, and a clear UM/UIM hit-and-run claim
- Extracts damage and injury facts correctly
- Returns low risk when no configured indicators exist
- Routes an injury claim to the Claims Adjuster
- Returns a status reply for a known claim ID
- Appends an update to an existing claim's history
- Routes a complaint to Customer Relations
- Generates a report containing every required section and writes it to the expected directory

## Initial Adversarial Tests

- Multiple PII types in one narrative; PII in an update or complaint
- Prompt injection or instructions directed at an agent
- Contradictory injury statements; an update that contradicts the original claim
- Missing date, location, loss details, or police report (hit-and-run)
- Model output that violates its schema, or an unsupported category
- A summary that tries to reintroduce original PII
- An agent call that fails or times out
- Whitespace-only or extremely long input; an unknown claim ID
- A submission mixing unrelated incidents
- Sanitization that can't be confirmed safely

## Terminal UI

```text
================================================
 Car Insurance Claim Support
================================================
 1. File a new claim
 2. Check claim status
 3. Add or correct details on a claim
 4. Get help with my claim
 5. Exit

Choose an option: 1
Tell us what happened, in your own words:
>

[1/4] Protecting your personal information
[2/4] Reviewing your claim
[3/4] Checking for anything that needs a specialist
[4/4] Preparing your summary

Your claim number is CLM-2026-0001.
What we still need from you:
  - The police report number
Report saved: output/CLM-2026-0001_20260924T1015.md
```

The UI shows progress, the customer reply, and the report location. It never shows hidden reasoning or model internals.

## Internal Markdown Report

- Processing status and claim identifier
- Menu task performed
- Sanitized narrative summary
- Claim classification (and UM/UIM sub-type if applicable)
- Incident, damage, and injury facts
- Missing information and contradictions
- Customer sentiment
- Risk indicators, risk level, escalation team
- PII scrubbing confirmation
- A notice that the output supports intake and triage and is not a coverage or claim decision

## Suggested Directory Structure

```text
├── .specify/                  # SpecKit templates, scripts, constitution
├── specs/NNN-feature/         # spec.md, plan.md, tasks.md per feature
├── src/claim_intake/
│   ├── agents/
│   ├── contracts/
│   ├── orchestration/
│   ├── pii/
│   ├── reporting/
│   ├── storage/
│   └── cli.py
├── tests/{unit,integration,fixtures}/
├── data/claims/               # sanitized claim records (seeded samples)
├── output/                    # generated reports (gitignored)
├── logs/                      # text-free event log (gitignored)
├── docs/
│   ├── prompt-history/        # summaries at key project moments
│   └── samples/               # curated sample reports
├── CLAUDE.md
├── README.md                  # written at the end
└── pyproject.toml
```

## Required Artifacts

- SpecKit artifacts per feature (spec, plan, tasks)
- Project constitution, then `CLAUDE.md`
- Unit and integration tests traceable to acceptance criteria
- Sample customer replies and internal reports
- Prompt history in `docs/prompt-history/`
- Architecture diagram and README (at the very end, from the implemented system)

## Prompt History

`docs/prompt-history/` holds one summary file per key moment (e.g., kickoff and constitution, each approved spec, major pivots). Each entry records:

- The objective
- Important prompts (condensed)
- Claude's key recommendations
- Decisions accepted, with rationale
- Pushbacks and clarifications
- Scope rejected or deferred

It is not a raw transcript dump and does not include hidden reasoning.
