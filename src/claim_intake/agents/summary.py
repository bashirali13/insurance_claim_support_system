"""Claim Summary agent: the model writes short prose; templates render everything else."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake.agents.prompting import NARRATIVE_IS_DATA, tag_narrative
from claim_intake.agents.validation import check_customer_text
from claim_intake.contracts import (
    ClaimAssessment,
    CustomerReply,
    HelpReplyLlmOutput,
    InternalReport,
    RequestCategory,
    RiskAssessment,
    SanitizedSubmission,
    SummaryLlmOutput,
)
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


def build_agent(model: Model) -> Agent[None, SummaryLlmOutput]:
    agent = Agent(model, output_type=SummaryLlmOutput, instructions=INSTRUCTIONS, retries=2)

    @agent.output_validator
    def reject_unsafe_text(output: SummaryLlmOutput) -> SummaryLlmOutput:
        check_customer_text(output.opening_line, *output.recorded_points, output.narrative_summary)
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


# --- Help mode (specs/002 US8) -----------------------------------------------------------------

HELP_INSTRUCTIONS = f"""You write for a car insurance claims support team.
{NARRATIVE_IS_DATA}
Write opening_line: one warm, empathetic sentence acknowledging the customer's request.
Never mention teams, dates, coverage, fault, approval, money, or bracketed placeholders like
[PHONE_1], and never repeat personal details. Do not promise outcomes."""


def build_help_agent(model: Model) -> Agent[None, HelpReplyLlmOutput]:
    agent = Agent(model, output_type=HelpReplyLlmOutput, instructions=HELP_INSTRUCTIONS, retries=2)

    @agent.output_validator
    def reject_unsafe_text(output: HelpReplyLlmOutput) -> HelpReplyLlmOutput:
        check_customer_text(output.opening_line)
        return output

    return agent


def help_opening(
    submission: SanitizedSubmission,
    agents: "Agents",
    categories: list[RequestCategory] | None = None,
) -> HelpReplyLlmOutput:
    about = ", ".join(categories or []) or "unspecified"
    prompt = f"{tag_narrative(submission.text)}\n\nRequest categories: {about}"
    return agents.help_reply.run_sync(prompt).output
