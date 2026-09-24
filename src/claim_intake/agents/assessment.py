"""Claim Assessment agent: the model classifies and extracts facts; rules add the rest."""

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake import rules
from claim_intake.agents.prompting import NARRATIVE_IS_DATA, tag_narrative
from claim_intake.contracts import AssessmentLlmOutput, ClaimAssessment, SanitizedSubmission

INSTRUCTIONS = f"""You are a claims intake analyst for a car insurance company.
{NARRATIVE_IS_DATA}
Placeholders like [PHONE_1] or [PERSON_1] stand for removed personal details; keep them as-is.

Classify the story into exactly one incident type:
- COLLISION: hitting another vehicle, person, or object, or a rollover (including hit-and-run)
- THEFT, VANDALISM, WEATHER (hail, flood, wind, falling tree), FIRE, GLASS, ANIMAL_STRIKE
- UNKNOWN: not enough information to tell what happened
- MIXED: two or more unrelated incidents in one story

Set um_uim_subtype only when another driver fled (HIT_AND_RUN), had no insurance (UNINSURED),
had their insurer deny it (COVERAGE_DENIED), or had limits too low (UNDERINSURED).

Extract only facts that are stated. Use UNKNOWN when something is not stated; never guess.
customer_side_injured covers the customer and their passengers; others_injured covers anyone
outside the customer's car. Give incident_date and location as the customer wrote them.
key_facts: at most 6 short, neutral items.
For each pair of statements that conflict, quote both and set about_injury when the conflict is
about whether someone was hurt.

Never state or imply fault, coverage, approval, denial, or a claim amount."""


def build_agent(model: Model) -> Agent[None, AssessmentLlmOutput]:
    return Agent(model, output_type=AssessmentLlmOutput, instructions=INSTRUCTIONS, retries=2)


def assess(submission: SanitizedSubmission, agents) -> ClaimAssessment:
    facts = agents.assessment.run_sync(tag_narrative(submission.text)).output
    return ClaimAssessment(
        **facts.model_dump(),
        injury_present=rules.injury_present(facts),
        missing_information=rules.missing_information(facts),
        coverage_lines=rules.coverage_lines(facts),
    )
