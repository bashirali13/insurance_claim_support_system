# 02 — Coverage Baseline, UX Walkthrough, and Phase Model

**Date:** 2026-09-24
**Phase:** 000-project-foundation (final planning before phase 001)

## Objective

Base the system on what car insurers actually offer, agree on the end-to-end customer experience
before any implementation, and simplify the git workflow.

## Key Prompts (condensed)

1. *"Rather than just UM/UIM, research total coverage: what all car insurance providers offer as a
   baseline for what this system can do."*
2. *"Not a fan of the branch system. Outline, constitution, etc. shouldn't be separate branches.
   Branches only for big phases."*
3. *"Before implementation, talk through the end product from the user's perspective: all user
   functionality, how the system responds, and what happens behind the scenes in the terminal."*
4. *"Limit this to claim support. Explain the agents, their workflow, the teams they represent, and
   how they communicate. You merge PRs, but run phase completion by me. Trace mode at the end.
   Stretch goal: simple localhost UI. Keep the response-time promise but base it in reality."*

## Claude's Key Recommendations

- **Six core coverages as the vocabulary:** liability (BI/PD), collision, comprehensive, UM/UIM,
  PIP, MedPay.
- **Keep incident types separate from coverage lines:** the model extracts facts, and
  deterministic code maps facts to *coverage lines to review*. Liability and UM/UIM stop being
  claim types. A hit-and-run is a `COLLISION` with the UM/UIM line flagged.
- **One branch per phase:** `000-project-foundation`, `001-file-a-claim`,
  `002-existing-claim-support`, `003-hardening-and-release`.
- **UX walkthrough doc** (`docs/user-experience.md`) with terminal mockups, a behind-the-scenes
  table per task, error states, and a trace mode.
- **Realistic response times:** instant acknowledgment (regulators allow 10–15 days per the NAIC
  model), with first human contact in 1–3 business days by urgency. Code computes real dates that
  skip weekends.
- **Stretch web UI:** only viable if the core never prints, so the terminal and web become thin
  adapters over the same orchestrator.

## Decisions Accepted

| Topic | Decision |
|---|---|
| Scope | **Claim support only.** Rentals, towing, repair booking, billing, and policy changes are out of scope and get a polite redirect |
| Coverage | Six core coverages as "lines to review"; add-on facts (drivable, total loss) are recorded only |
| Menu option 4 | "Get help with my claim": complaint, delay, claim question, speak to an adjuster, contact change |
| Teams | Claims Adjuster, Customer Relations, Policy Services, Privacy Review, Special Review (internal) |
| Promises | Injury or urgent: 1 business day; standard: 2; complaints: 2; contact change: 3; privacy review: 3 |
| Branches | Phase-only; the three earlier branches were consolidated into `000-project-foundation` (never pushed, no history lost) |
| PR merges | Claude merges phase PRs after presenting a phase-completion check **and** getting the user's confirmation |
| Trace mode | Built at the end of implementation (phase 003) unless debugging needs it earlier |
| Stretch goal | `004-local-web-ui` on localhost, reusing the orchestrator unchanged |
| Company | Northstar Auto Insurance (fictional) |
| Sample claims | About 6 fictional, sanitized seeded claims, also used as test fixtures |
| Input | Multi-line; an empty line finishes the input |

## Pushbacks and Clarifications

- The user pushed back on per-artifact branches as fragmented. The model changed to phase-only
  branches, and the constitution and CLAUDE.md were updated.
- The user limited scope after the research showed that insurer apps also handle rentals, towing,
  and more. Those were dropped, along with the "Claims Services" team proposed for them.
- A vague "within 1 business day" was replaced by urgency-based, regulation-aware promises with
  computed dates.

## Deferred or Rejected Scope

- **Deferred:** trace mode (phase 003); local web UI (stretch); holiday-aware business days.
- **Rejected:** service requests (rental, towing, repair shop, appraisal); add-on coverage lines.

## Next

1. The user authenticates the `gh` CLI and restarts Claude Code, so the `/speckit-*` commands
   register.
2. Push `000-project-foundation`, open its PR, run the phase-completion check with the user, and
   merge.
3. `/speckit-specify` for **001-file-a-claim**.
