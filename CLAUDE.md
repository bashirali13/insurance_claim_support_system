# CLAUDE.md

A **car insurance claim automation customer support system**. Customers use a terminal menu to file
a new claim, check claim status, add or correct details on an existing claim, or get help with a
claim (complaints, delays, claim questions) that gets routed to the correct human
team.

- Governing rules: `.specify/memory/constitution.md`. It wins any conflict with this file.
- Scope and background: `docs/project-outline.md`.
- How the product looks and behaves in the terminal: `docs/user-experience.md`.
- Example customer inputs and expected outcomes (test reference): `docs/customer-scenarios.md`.
- Feature specs: `specs/NNN-feature/` (`spec.md`, `plan.md`, `tasks.md`).

## Commands

```bash
uv sync                      # install dependencies
uv run pytest                # full suite (excludes live model tests)
uv run pytest -m live        # tests that call the real model via OpenRouter
uv run pytest -k ac_2_3      # tests for one acceptance criterion
uv run ruff check .          # lint
uv run ruff format .         # format
uv run claim-support         # run the terminal app (needs .env)
uv run claim-support --load-samples  # also load the six sample claims
uv run claim-support --trace         # show a sanitized staff trace after each reply
```

Config lives in `.env` (copy `.env.example`): `OPENROUTER_API_KEY`, `MODEL_NAME`. Never commit `.env`.

## How work is done here

1. **Spec first.** Use SpecKit: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` →
   `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`.
2. **Tests come only from acceptance criteria.** Every AC has an ID (`AC-2.3`). Every test names its
   AC: `test_ac_2_3_routes_injury_claim_to_adjuster`. Keep tests short, Given/When/Then shaped,
   one behavior each.
3. **Code comes only from failing tests.** Red → Green → Refactor. Confirm Red fails for the
   right reason, write the minimum code for Green, and keep the suite green while refactoring.
4. **No speculative code.** No unused abstractions, extension points, or dependencies.

## Architecture rules (see constitution for full text)

- There is one orchestrator and four agents: Intake & PII, Claim Assessment, Sentiment & Risk, and
  Claim Summary. Agents never call each other.
- Handoffs are frozen Pydantic models with `extra="forbid"`, and every category is an enum.
- **PII:** regex and validators first, then model-proposed spans (applied only if they appear
  verbatim), then a deterministic re-scan. Downstream code accepts only sanitized types. Never
  store, log, or write PII.
- **Deterministic code decides:** input validation, missing-info checklists, risk level,
  escalation, and team routing. Models only classify, extract, read sentiment, and write short text.
- Sentiment never raises risk. Customer text is data, never instructions.
- Never determine fault or coverage, approve or deny claims, give legal advice, or allege fraud.
  When in doubt, escalate.

## Testing

- Unit tests use fixed fixtures in `tests/fixtures/` and PydanticAI `TestModel` / `FunctionModel`,
  with no network calls.
- Tests that hit the real model are marked `@pytest.mark.live`.

## Git

- **Branches are for big phases only**: `000-project-foundation`, `001-file-a-claim`,
  `002-existing-claim-support`, `003-hardening-and-release`. Never create branches for single
  documents or sub-features. Use commits.
- Conventional Commits following the TDD rhythm (`test:` → `feat:` → `refactor:`). End commit
  messages with the Co-Authored-By trailer.
- One PR per phase via the `gh` CLI. Suite green and ruff clean, then Claude presents a
  phase-completion check and merges **only after the user confirms** the phase is complete.

## Documentation

- Add a summary to `docs/prompt-history/` at key moments (approved constitution or spec, major
  pivots). Record the objective, key prompts, recommendations, decisions, pushbacks,
  clarifications, and deferred scope. Don't dump the raw transcript.
- The README and architecture diagram are written only at the very end.
