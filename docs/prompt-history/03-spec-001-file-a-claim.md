# 03 — Spec 001: File a New Claim

**Date:** 2026-09-24
**Phase:** 001-file-a-claim (specify → clarify → approved)
**Artifacts:** `specs/001-file-a-claim/spec.md`, `specs/001-file-a-claim/checklists/requirements.md`

## Objective

Write and approve the specification for the first implementation phase: the "File a new claim"
menu option end to end, with testable acceptance criteria for every behavior.

## Key Prompts (condensed)

1. *"Go ahead with that prompt"*: `/speckit-specify` for phase 001, with five prioritized stories:
   P1 PII scrubbing, P2 assessment, P3 risk and routing, P4 reply and report, P5 end-to-end terminal
   filing.
2. *"Explain: model-vs-code indicators, prompt injection, the context-word decision for DOB,
   license, and plate, and the 'coming soon' options."*
3. *"Let the model suggest license plates written without context. Keep it in mind if issues
   arise. Move ahead with clarify."*
4. Five clarify answers (below), then *"It's approved."*

## Claude's Key Recommendations

- **46 acceptance criteria with stable IDs** (AC-1.1 … AC-5.12), each Given/When/Then, so every
  test can name exactly what it proves.
- **Rule tables written into the spec** (missing-info checklist, coverage lines, risk level,
  routing, follow-up days), so deterministic behavior is fully specified before any code exists.
- **Code derives the fact-based risk indicators.** The model only flags legal representation and
  prompt injection. This removes the chance of the two agents contradicting each other.
- **Context words for ambiguous PII patterns** (DOB, license, plate), with model suggestions as the
  backup layer.
- **Show options 2–4 as "coming soon"** so the menu is built and tested once, in its final shape.

## Decisions Accepted

| Topic | Decision |
|---|---|
| Spec shape | 5 stories, 46 ACs, 33 FRs (plus FR-017a), 7 success criteria; no open clarification markers |
| Risk indicators | 5 derived by code from facts; 2 from the model (legal representation, prompt injection) |
| Risk level | 0 indicators → LOW, 1 → MEDIUM, 2+ or legal/injection → HIGH; sentiment never affects it |
| Distress | `DISTRESSED` or `ANGRY` adds Customer Relations; risk unchanged |
| PII context words | DOB, license, and plate need context words; a bare plate relies on model suggestion. **Watch item:** revisit if misses show up in SC-001 evaluation |
| Limits | 5,000 characters; at most 2 retries on model failure |
| Options 2–4 | "Coming soon" in phase 001; real criteria replace them in phase 002 (spec first) |
| **Clarify Q1** | Prompt injection: fixed phrase list checked by code **plus** model judgment (FR-017a) |
| **Clarify Q2** | Manual privacy review still issues a claim number and a minimal, text-free record |
| **Clarify Q3** | Initial status: `ESCALATED` (high risk or privacy review) → `AWAITING_INFORMATION` (missing info) → `SUBMITTED` |
| **Clarify Q4** | Mixed incidents: one claim, which an adjuster separates; the customer is not asked to refile |
| **Clarify Q5** | Text-free event log (`logs/events.log`): step, outcome, and duration only (FR-033) |

## Pushbacks and Clarifications

- **The first draft contradicted itself:** AC-2.6 required a police report for every collision,
  which conflicted with FR-013. The quality checklist caught it and AC-2.6 was aligned, with a
  negative case added.
- **Duplicate-claim risk:** the original `MIXED` behavior both created a claim *and* asked the
  customer to refile. Clarify Q4 removed the duplication.
- **"act as" dropped from the injection phrase list** because it appears in ordinary stories
  ("the driver tried to act as if…").
- **The user asked for deeper explanations** before clarify (indicators, injection, context words,
  placeholders). Each was accepted as proposed.

## Deferred or Rejected Scope

- **Deferred:** holiday-aware business days; non-English support; options 2–4 (phase 002); trace
  mode (phase 003).
- **Watch item:** bare license plates or license numbers without context words (model-suggestion
  dependent).
- **Rejected:** creating no claim for mixed incidents; model-only injection detection; a claim
  without a number during privacy review.

## Post-Approval Amendment: Plan, Tasks, and Analyze

**Prompts (condensed):**
- *"Approved. Write 03, then plan."*
- `/speckit-tasks`, then `/speckit-analyze`
- *"Suggest concrete remediation so that each task has acceptance criteria that can shape simple
  tests that then drive development."*
- *"Yes. Re-run analyze, make sure everything is clear."*

**Plan highlights:**
- **Narrow LLM output models:** each agent's model returns only what it may judge, and code builds
  the full contract. For example, the risk model has no field for level, team, or date.
- **Agents built by `create_agents(model)`:** tests pass a scripted `FunctionModel`, and real
  requests are blocked in tests.
- **Output validator:** rejects placeholders, PII, or decision words ("covered", "approved", "at
  fault", "$…") in model-written reply text.
- **Research verified against the installed PydanticAI 2.49** (`OpenRouterModel`,
  `FunctionModel`, `ALLOW_MODEL_REQUESTS`).
- **Risk to confirm early:** whether DeepSeek via OpenRouter supports tool-call structured output.
  The fallback is `PromptedOutput`.
- **UX doc corrected:** the hit-and-run + injury example is `HIGH` / `ESCALATED` under the approved
  rules (it had said `MEDIUM`).

**What analyze found:** 4 critical issues, all of the same kind. The design built behavior that no
acceptance criterion required, which would have meant code without a driving test (Principle II)
or output that skipped the PII guard (Principle III):

| Gap | Fix (spec first, then tasks) |
|---|---|
| Event log had no AC | New **AC-5.13**: one line per step, allowed fields only, no narrative words |
| "Narrative is data" had no AC | New **AC-3.10**: tagged narrative plus a "never follow instructions" line. Tested inside each agent's own test task, so Red still comes before Green |
| Mixed-incident reply line had no AC | Extended **AC-4.1** |
| PII guard only covered reply and report | **AC-4.6 / FR-025** now cover the claim record and event log |
| Legal rep → Special Review, contradicted injury → 1 day, HIGH → 1 day, invalid menu input | Extended **AC-3.7, AC-3.3, AC-3.4, AC-5.1** |
| Smaller items | AC-1.4 placeholder suggestions; AC-1.9 now requires the frozen / no-extra-fields base class; FR-011 test relabeled to AC-5.9; length limit is "after trimming"; SC-004 is the median of 5 runs |

**Result:** spec 46 → **48 ACs**. Every AC has at least one named test, no test cites a missing
AC, all 34 functional requirements are traced, and **0 critical issues** remain.

**Lesson recorded:** SpecKit's `analyze` step is where "tests only from acceptance criteria" gets
enforced in practice. It caught design-level behavior (logging, prompt formatting, template lines)
that is easy to build without ever specifying it.

## Next

`/speckit-implement` for 001-file-a-claim, starting with Setup (T001–T003) and US1 (PII) as the
MVP checkpoint. Each test task is committed Red (`test:`) before its Green (`feat:`) commit.
