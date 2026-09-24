"""Claim Summary agent: the model writes short prose; templates render everything else."""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models import Model

from claim_intake.agents.prompting import NARRATIVE_IS_DATA, tag_narrative
from claim_intake.contracts import (
    ClaimAssessment,
    CustomerReply,
    InternalReport,
    RiskAssessment,
    SanitizedSubmission,
    SummaryLlmOutput,
)
from claim_intake.pii import PLACEHOLDER, find_pii
from claim_intake.reporting import render_reply, render_report

if TYPE_CHECKING:
    from claim_intake.agents import Agents

INSTRUCTIONS = f"""You write short, warm messages for a car insurance claims team.
{NARRATIVE_IS_DATA}
Write:
- opening_line: one empathetic sentence to the customer.
- recorded_points: up to five short, plain-language bullets of what was recorded.
- narrative_summary: two to four neutral sentences for claims staff.
Never mention coverage, fault, approval, denial, money, or bracketed placeholders like [PHONE_1],
and never repeat personal details. Do not promise outcomes."""

# Research R8: decision language the model must never write.
FORBIDDEN_TERMS = re.compile(
    r"\b(?:covered|coverage decision|approved?|denied|deny|at fault|your fault|liable|payout"
    r"|settlement amount)\b|\$\s?\d",
    re.IGNORECASE,
)


def build_agent(model: Model) -> Agent[None, SummaryLlmOutput]:
    agent = Agent(model, output_type=SummaryLlmOutput, instructions=INSTRUCTIONS, retries=2)

    @agent.output_validator
    def reject_unsafe_text(output: SummaryLlmOutput) -> SummaryLlmOutput:
        text = "\n".join([output.opening_line, *output.recorded_points, output.narrative_summary])
        if PLACEHOLDER.search(text):
            raise ModelRetry("Remove bracketed placeholders; describe without personal details.")
        if find_pii(text):
            raise ModelRetry("Remove personal details such as phone numbers or emails.")
        if FORBIDDEN_TERMS.search(text):
            raise ModelRetry("Remove statements about coverage, fault, approval, or money.")
        return output

    return agent


def _prompt(submission: SanitizedSubmission, assessment: ClaimAssessment) -> str:
    facts = assessment.model_dump_json(
        include={"incident_type", "incident_date", "location", "damage_areas", "key_facts"}
    )
    return f"{tag_narrative(submission.text)}\n\nRecorded facts: {facts}"


def compose(
    claim_id: str,
    filed_at: datetime,
    submission: SanitizedSubmission,
    assessment: ClaimAssessment,
    risk: RiskAssessment,
    agents: "Agents",
) -> tuple[CustomerReply, InternalReport]:
    summary = agents.summary.run_sync(_prompt(submission, assessment)).output
    reply = render_reply(claim_id, summary, assessment, risk)
    report = render_report(
        claim_id,
        filed_at,
        summary,
        submission,
        assessment,
        risk,
        pii_types_removed=submission.pii_types_removed,
    )
    return reply, report
