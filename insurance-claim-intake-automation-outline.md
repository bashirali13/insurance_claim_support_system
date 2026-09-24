# Insurance Claim Intake Automation

## Project Summary

A specialized insurance claim intake system focused on First Notice of Loss (FNOL) processing.

The system accepts a raw claim submission, coordinates specialized AI agents, scrubs personally identifiable information (PII), classifies the claim, assesses sentiment and risk, and produces a standardized markdown claim report.

The scope is intentionally limited to first-pass intake and triage. It does not attempt to adjudicate claims, approve payments, interpret policy coverage, or replace licensed claims professionals.

## Goal

Create an AI claims intake coordinator capable of:

- Processing insurance claim submissions
- Removing sensitive customer information
- Classifying claim types
- Extracting essential claim facts
- Identifying missing or contradictory information
- Performing sentiment analysis
- Identifying predefined risk indicators
- Recommending human escalation when appropriate
- Generating standardized claim summaries
- Saving a complete markdown report to disk

## Initial Claim Scope

- Auto collision
- Property damage
- Vehicle theft
- Weather-related damage
- Liability-related loss

## Guiding Principles

- Keep the project simple, focused, and easy to navigate.
- Use four worker agents plus one orchestrator.
- Keep the workflow linear unless a defined escalation condition requires branching.
- Give every agent explicit inputs, outputs, responsibilities, and non-responsibilities.
- Use Pydantic models at every agent boundary to prevent information loss.
- Prefer deterministic rules for safety-critical checks such as PII detection and schema validation.
- Use models only for bounded interpretation tasks.
- Implement only behavior required by approved specifications and failing tests.
- Do not introduce unnecessary frameworks, services, databases, or abstractions.

## Agent Architecture

The real project team roles map directly to the software agents. The orchestrator coordinates the workflow but does not perform specialist decisions.

### Orchestrator

**Background:** Claims Operations Manager

**Responsibilities:**

- Execute the approved workflow
- Pass validated Pydantic objects between agents
- Maintain workflow state
- Track processing status and failures
- Stop or redirect processing when validation fails
- Save the final markdown artifact to the requested output path

**Non-responsibilities:**

- Interpret claim facts
- Scrub PII
- Classify claim type
- Assess sentiment or risk
- Write report content

### Intake and PII Scrubbing Agent

**Background:** Claims Intake Specialist

**Responsibilities:**

- Normalize raw claim submissions
- Detect supported PII patterns
- Replace PII with stable redaction tokens
- Extract basic intake entities
- Return sanitized content for downstream processing
- Request manual review when safe sanitization cannot be confirmed

**Non-responsibilities:**

- Classify the claim
- Assess sentiment or risk
- Recommend escalation
- Generate the final report

### Claim Assessment Agent

**Background:** Claims Adjuster

**Responsibilities:**

- Determine the supported claim type
- Extract incident, damage, and injury facts
- Identify missing information
- Identify contradictory statements
- Return a structured claim assessment

**Non-responsibilities:**

- Handle raw PII
- Determine customer sentiment
- Make fraud conclusions
- Interpret policy coverage
- Approve or deny claims
- Generate the final report

### Sentiment and Risk Agent

**Background:** Fraud and Customer Experience Analyst

**Responsibilities:**

- Classify customer sentiment
- Identify predefined risk indicators
- Assign a bounded risk level
- Recommend human escalation
- Provide a concise rationale grounded in claim facts

**Non-responsibilities:**

- Determine claim type
- Handle raw PII
- Make claim approval or denial decisions
- Interpret policy coverage
- Make legal conclusions
- Produce the final report

### Claim Summary Agent

**Background:** Senior Claims Coordinator

**Responsibilities:**

- Combine validated outputs from the other agents
- Generate the standardized markdown report
- Distinguish known, missing, contradictory, and flagged information
- Confirm PII scrubbing status
- Avoid reintroducing scrubbed information

**Non-responsibilities:**

- Change upstream classifications
- Perform new claim or risk analysis
- Approve, deny, or value the claim
- Persist data outside the report artifact

## Core Contracts

Contract names and fields are provisional until the SpecKit requirements and design phases are approved. Every agent output must be Pydantic-validated before the next workflow step begins.

### IntakeResult

```python
class IntakeResult(BaseModel):
    sanitized_claim: str
    pii_types_removed: list[str]
    extracted_entities: list[str]
    requires_manual_review: bool
```

### ClaimAssessment

```python
class ClaimAssessment(BaseModel):
    claim_type: ClaimType
    damage_types: list[DamageType]
    injury_present: bool | None
    key_facts: list[str]
    missing_information: list[str]
    contradictions: list[str]
```

### RiskAssessment

```python
class RiskAssessment(BaseModel):
    sentiment: Sentiment
    risk_indicators: list[RiskIndicator]
    risk_level: RiskLevel
    escalation_required: bool
    rationale: str
```

### ClaimReport

```python
class ClaimReport(BaseModel):
    claim_id: str
    processing_status: ProcessingStatus
    markdown_report: str
    output_path: str
```

## Core Workflow

1. The user submits a claim through the terminal.
2. The orchestrator sends the raw input only to the Intake and PII Scrubbing Agent.
3. The intake output is validated with Pydantic.
4. The Claim Assessment Agent receives the sanitized claim and extracts bounded claim facts.
5. The assessment output is validated with Pydantic.
6. The Sentiment and Risk Agent receives the sanitized claim and structured assessment.
7. The risk output is validated with Pydantic.
8. The Claim Summary Agent receives only validated outputs and creates the markdown report.
9. The orchestrator saves the report and displays its location and final processing status.

```text
Claim Submission
        |
        v
Intake and PII Scrubbing
        |
        v
Claim Assessment
        |
        v
Sentiment and Risk
        |
        v
Claim Summary
        |
        v
output/claim_report.md
```

## Core Functionality

- Accept one claim narrative through a terminal UI
- Scrub supported PII before downstream model calls
- Classify the claim using controlled categories
- Extract structured incident, damage, and injury facts
- Identify missing and contradictory information
- Analyze customer sentiment
- Identify predefined risk indicators
- Recommend whether human escalation is required
- Generate a standardized markdown claim report
- Save the report to the local filesystem
- Validate every agent handoff
- Return a safe status when validation or model execution fails

## Explicitly Out of Scope

- Policy coverage determination
- Claim approval or denial
- Settlement calculation or payment
- Legal advice or legal conclusions
- Autonomous fraud accusations
- External web search or scraping
- External databases or production insurance integrations
- User authentication
- Web UI
- Persistent customer profiles

## Technology Stack

- **Language:** Python
- **SDD:** SpecKit
- **Agent framework:** PydanticAI
- **Validation:** Pydantic
- **Agent model:** DeepSeek Flash V4 0731 through OpenRouter
- **Testing:** pytest
- **Interface:** Simple terminal UI
- **Storage:** Local filesystem only

## SDD and Delivery Sequence

1. Analyze and narrow the business problem.
2. Create the initial SpecKit planning artifacts.
3. Define functional and non-functional requirements.
4. Define acceptance criteria and success conditions.
5. Define agent responsibilities, non-responsibilities, and contracts.
6. Define the workflow, failure behavior, and test strategy.
7. Create the project constitution after planning and analysis but before implementation.
8. Create `CLAUDE.md` after the constitution is approved.
9. Implement vertical slices using Red, Green, Refactor.
10. Record important prompts and decision rationale in a concise prompt-history artifact.
11. At the end, create the architecture diagram from the implemented system.
12. At the end, create the README from the implemented system.

## TDD Strategy

Development follows Red, Green, Refactor. Each vertical slice starts with a failing test tied to an approved requirement and acceptance criterion.

### Red

- Write one focused failing test.
- Use fixed fixtures and mocked model responses for deterministic unit tests.
- Test contracts, orchestration decisions, error behavior, and artifact content.
- Confirm that the test fails for the expected reason.

### Green

- Implement only the minimum behavior needed to pass the test.
- Avoid speculative abstractions and unused extension points.
- Run the focused test and then the complete suite.

### Refactor

- Improve naming, prompts, contract boundaries, and duplication.
- Preserve observable behavior.
- Run the full test suite after each change.

## Initial Happy-Path Tests

- Redacts supported PII while preserving the usable claim narrative.
- Classifies a clear auto-collision claim.
- Classifies a clear property-damage claim.
- Extracts damage and injury facts correctly.
- Returns low risk when no configured indicators exist.
- Recommends escalation when a configured escalation condition exists.
- Generates a markdown report containing every required section.
- Writes the report to the expected output directory.

## Initial Adversarial Tests

- Multiple PII types appear in one narrative.
- A claim contains prompt injection or instructions directed at an agent.
- A claim contains contradictory injury statements.
- A claim lacks date, location, or loss details.
- A model output violates its Pydantic schema.
- An agent returns an unsupported category.
- The summary attempts to reintroduce original PII.
- An agent call fails or times out.
- A claim contains only whitespace.
- A claim is extremely long.
- A claim mixes unrelated incidents.
- Sanitization cannot be confirmed safely.

## Terminal UI

```text
================================================
 Insurance Claim Intake Automation
================================================

Paste claim:
>

[1/4] Intake and PII Scrubbing
[2/4] Claim Assessment
[3/4] Sentiment and Risk
[4/4] Claim Summary

Report saved: output/claim_report.md
```

The terminal UI should remain lightweight. It should show the current workflow step, final status, and output path without exposing hidden reasoning or unnecessary model details.

## Markdown Claim Report

The generated report should include:

- Processing status
- Locally generated claim identifier
- Sanitized claim summary
- Claim classification
- Extracted incident facts
- Damage and injury facts
- Missing information
- Contradictory information
- Customer sentiment
- Risk indicators
- Risk level
- Escalation recommendation
- PII scrubbing confirmation
- A notice that the output supports intake and triage but is not a coverage or claim decision

## Suggested Directory Structure

```text
insurance-claim-automation/
├── specs/
├── src/
│   ├── agents/
│   ├── contracts/
│   ├── orchestration/
│   ├── reporting/
│   └── cli.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── output/
├── docs/
│   └── prompt-history.md
├── CLAUDE.md
├── README.md
└── pyproject.toml
```

The final structure may change during SpecKit planning, but it should remain shallow, predictable, and easy to navigate.

## Required Artifacts

- SpecKit SDD artifacts
- Project constitution
- `CLAUDE.md`
- Unit tests covering happy and adversarial paths
- Integration tests for the end-to-end workflow
- Sample markdown claim reports
- Prompt-history summary showing important reasoning and decisions
- Architecture diagram created after implementation
- README created after implementation

## Prompt-History Artifact

The prompt-history document should summarize only the prompts and decisions that materially influenced the project.

For each important interaction, record:

- The objective
- The important prompt or condensed prompt
- Claude's key recommendation
- The accepted decision
- The rationale
- Any scope that was rejected or deferred

Do not export every conversational message or hidden reasoning. Keep the artifact concise and useful for project review.
