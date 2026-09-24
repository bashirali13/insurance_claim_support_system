# 01 — Kickoff, Scope, and Constitution

**Date:** 2026-09-24
**Phase:** Planning → constitution v1.0.0 and `CLAUDE.md`
**Branches:** `docs/project-outline`, `chore/project-setup`, `docs/constitution`

## Objective

Turn the initial FNOL intake outline into a clear, simple plan: structured agent-to-agent
communication, PII scrubbing, sentiment analysis, a clean git branching strategy, project tooling,
and a ratified constitution.

## Key Prompts (condensed)

1. *"Read the outline. What's the clearest way to approach this project? Give ideas for each point.
   Keep it simple, with a clean workflow and structured agent-to-agent communication (PII scrubbing,
   sentiment analysis). Use git with feature and sub-feature branches."*
2. *"Adopt SpecKit `001-` naming alongside `spec/` etc. Install SpecKit, Python, and so on."* Also:
   what counts as a failure, and when should the constitution be written.
3. *"Big focus on SDD. Tests only from acceptance criteria; code only from tests. Keep prompt
   history in docs. Clarify it's a car insurance claim automation customer support system, with
   filing claims and helping with existing claims as key functionality. What else can I clarify?"*
4. Answers to the clarifying questions (below), plus: *"Include uninsured/underinsured motorists.
   Research how insurers handle it."*

## Claude's Key Recommendations

- **Make the PII boundary part of the types:** separate raw and sanitized types. Downstream agents
  accept only the sanitized type, so a leak fails at type-check or test time.
- **Frozen contracts with enums:** `frozen=True`, `extra="forbid"`, and `StrEnum` for every
  category. Add `UNKNOWN` and `MIXED` claim types so the model isn't forced into a wrong class.
- **Layered PII:** deterministic regex and validators first, then model-proposed spans (applied only
  if verbatim), then a deterministic re-scan. This also keeps structured PII from ever reaching the
  third-party model.
- **Deterministic risk:** the model picks indicators from a fixed list; code computes risk level,
  escalation, and team routing.
- **Keep sentiment separate from risk:** an upset customer is not a suspicious one.
- **Template-rendered reports:** the model writes only the narrative paragraph, which reduces
  PII-reintroduction risk.
- **Walking skeleton early:** stub agents wired end-to-end before any real agent is built.
- **Git:** sub-branches use a hyphen suffix, because git refs can't hold both `feat/x` and
  `feat/x/y`. Conventional Commits follow the TDD rhythm.

## Decisions Accepted

| Topic | Decision | Rationale |
|---|---|---|
| Domain | Car insurance **customer support** system, not just FNOL intake | User's clarified product vision |
| Tasks (v1) | File new claim; check status; add or correct details; report a problem | Common support tasks; problems route to the correct team |
| Routing | Menu selects the task; free text inside each task | Removes misrouting while letting the model adapt to the customer's own words |
| Interaction | One-shot per task; missing details listed as "What we still need from you" | Simple v1; multi-turn deferred |
| User | The customer; staff read internal reports | Customer-facing reply plus internal markdown report |
| PII | Layered deterministic + agent-assisted approach | Meets a standard baseline while staying agentic |
| Storage | Sanitized JSON per claim in `data/claims/`; never store PII | Contact changes are redacted and routed to Policy Services |
| Lookup | Claim ID only, no authentication | Status replies contain no PII |
| Claim types | Collision, theft, vandalism, weather, glass, animal strike, liability, **UM/UIM**, unknown, mixed | Mirrors common US insurer categories; home insurance dropped |
| UM/UIM | Sub-types: uninsured, hit-and-run, coverage denied, underinsured; police report tracked; escalate on injury, a hit-and-run without a police report, or a pending settlement offer | Based on regulator and insurer consumer guidance; no fault or coverage decisions |
| Failures | Six categories; every failure writes a status-only report with no claim text | Audit trail without PII risk |
| Constitution | Written now (SpecKit order), versioned, amended as needed | Plans are checked against it from the start |
| Tooling | Python 3.13 + uv, SpecKit 1.0.6 (Claude integration, PowerShell scripts), PydanticAI, pytest, ruff | Matches the stack in the outline |
| Model | `deepseek/deepseek-v4-flash-0731` via OpenRouter (`OPENROUTER_API_KEY`, `MODEL_NAME`) | User's existing key and model |
| Git | SpecKit `NNN-` branches plus typed prefixes; PRs via `gh`; Claude merges docs/chore PRs, the user merges spec/feature PRs | User preference |
| Identity | Keep the repo-local `Ali <bashir.a.ali@accenture.com>` | User choice |

## Pushbacks and Clarifications

- **Constitution timing:** the outline placed it after planning, but SpecKit expects it first.
  Resolved: write it early and keep it versioned.
- **PII sent to the model:** Claude flagged that the intake model call itself would send raw PII to
  a third party. Resolved by the regex-first layer.
- **Router agent vs. menu:** Claude offered an intent-router agent. The user chose a menu with free
  text, which keeps four agents plus one orchestrator.
- **Contact updates vs. never storing PII:** resolved by redacting the value and routing it to a
  human (Policy Services).

## Deferred or Rejected Scope

- **Deferred:** multi-turn follow-up conversations; an intent-router agent; payments, rental or
  repair scheduling, cancellations, policy changes.
- **Rejected:** home/property insurance; authentication; storing PII in any form.

## Next

`/speckit-specify` for **001-pii-scrubbing**, then 002-file-new-claim through 006-hardening, in
the order listed in the outline.
