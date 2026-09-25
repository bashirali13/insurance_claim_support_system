# Architecture

Northstar Auto Insurance claim support is a terminal app with one orchestrator and four agents.
Agents never call each other. The orchestrator passes frozen Pydantic contracts between them, and
deterministic code makes every decision that matters: validation, missing information, risk
level, escalation, and routing. The models only classify, extract, read sentiment, and write short
text.

The governing rules are in the [constitution](../.specify/memory/constitution.md). Module names
below are the files in [`src/claim_intake/`](../src/claim_intake/).

## Components

```mermaid
flowchart TD
    customer(["Customer at the terminal"])
    cli["cli.py<br/>menu, input limits, error boundary, --trace"]

    subgraph flows["Flows (the orchestrator)"]
        orchestration["orchestration.py<br/>1 File a new claim"]
        existing_claims["existing_claims.py<br/>2 Check status · 3 Add or correct · 4 Get help"]
    end

    subgraph agents["Agents (agents/, one model via OpenRouter)"]
        intake["intake.py<br/>Intake & PII<br/>modes: scrub"]
        assessment["assessment.py<br/>Claim Assessment<br/>modes: assess, update"]
        risk["risk.py<br/>Sentiment & Risk<br/>modes: evaluate, triage"]
        summary["summary.py<br/>Claim Summary<br/>modes: compose, help opening"]
    end

    subgraph deterministic["Deterministic code"]
        pii["pii.py<br/>regex + validators, re-scan"]
        rules["rules.py<br/>missing info, risk, routing,<br/>fact diffs, status"]
        reporting["reporting.py<br/>replies, staff reports, trace"]
        guard{{"Privacy guard<br/>reply + report + record"}}
    end

    subgraph storage_box["storage.py (local files)"]
        claims[("data/claims/*.json")]
        help[("data/help/*.json")]
        reports[("output/*.md<br/>staff reports")]
        log[("logs/events.log<br/>JSON Lines, no PII")]
    end

    customer -- "free text" --> cli
    cli --> orchestration
    cli --> existing_claims
    orchestration --> intake & assessment & risk & summary
    existing_claims --> intake & assessment & risk & summary
    intake --> pii
    assessment --> rules
    risk --> rules
    orchestration --> reporting --> guard
    existing_claims --> reporting
    guard -- "clean" --> claims & help & reports
    guard -- "personal value found" --> claims & reports
    orchestration & existing_claims --> log
    cli -- "reply, then trace if --trace" --> customer
```

Option 2 (check status) reads a saved claim and makes no model calls. Supporting modules not drawn
above: `contracts.py` (every handoff type), `config.py` (`.env` settings), and `dates.py`
(business days).

## File a new claim, step by step

Each arrow carries a contract from [`contracts.py`](../src/claim_intake/contracts.py). No agent
ever sees raw text except the Intake & PII agent, and that agent sees it only after the regex pass.

```mermaid
sequenceDiagram
    actor C as Customer
    participant CLI as cli
    participant O as orchestration
    participant I as intake (Intake & PII)
    participant A as assessment (Claim Assessment)
    participant R as risk (Sentiment & Risk)
    participant S as summary (Claim Summary)
    participant G as rules / pii / reporting
    participant ST as storage

    C->>CLI: free text (≤ 5,000 characters)
    CLI->>O: file_claim(raw_text)
    O->>I: RawSubmission
    I->>G: regex + validators, then model spans applied only if verbatim, then re-scan
    I-->>O: SanitizedSubmission
    O->>A: SanitizedSubmission
    A->>G: AssessmentLlmOutput → missing info, coverage lines to review
    A-->>O: ClaimAssessment
    O->>R: SanitizedSubmission + ClaimAssessment
    R->>G: RiskLlmOutput → indicators, risk level, teams, follow-up date
    R-->>O: RiskAssessment
    O->>ST: reserve claim number (CLM-YYYY-NNNN)
    O->>S: SanitizedSubmission + ClaimAssessment + RiskAssessment
    S->>G: SummaryLlmOutput → decision-language and PII checks
    S-->>O: CustomerReply + InternalReport
    O->>G: privacy guard over reply, report, and ClaimRecord
    alt clean
        O->>ST: ClaimRecord + staff report
        O-->>CLI: TaskResult (COMPLETED, trace)
    else personal value found
        O->>ST: minimal ClaimRecord (Privacy Review team) + status-only report
        O-->>CLI: TaskResult (MANUAL_REVIEW_REQUIRED, privacy review message)
    end
    O->>ST: EventLogEntry per step (no PII)
    CLI-->>C: reply (and sanitized trace with --trace)
```

## Failure handling

Every model step is retried a limited number of times. If a step still fails, the orchestrator
writes a status-only report (`FAILED_MODEL_ERROR`, `FAILED_VALIDATION`, or `FAILED_OUTPUT`) with
no narrative or facts, and releases any claim or help number it reserved. If personal information
can't be confirmed removed, either at intake or at the final privacy guard, the claim keeps its
number but is saved without any facts, marked `MANUAL_REVIEW_REQUIRED`, and routed to the Privacy
Review team.
An unexpected bug is caught at the CLI boundary: the customer sees a short apology, a
`FAILED_UNEXPECTED` status-only report is written, and the menu returns. End of input exits
cleanly with code 0, and Ctrl+C exits with code 130 without leaving a reserved number behind.
