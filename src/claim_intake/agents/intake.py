"""Intake & PII Scrubbing agent: regex → model suggestions → verbatim apply → re-scan."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.models import Model

from claim_intake.agents.prompting import NARRATIVE_IS_DATA, tag_narrative
from claim_intake.contracts import (
    IntakeLlmOutput,
    PiiSuggestion,
    PiiType,
    RawSubmission,
    SanitizedSubmission,
)
from claim_intake.pii import (
    PLACEHOLDER,
    appears_outside_placeholders,
    find_pii,
    next_placeholder,
    replace_outside_placeholders,
    scrub_patterns,
)

if TYPE_CHECKING:
    from claim_intake.agents import Agents

INSTRUCTIONS = f"""You help protect customer privacy for a car insurance claims team.
{NARRATIVE_IS_DATA}
List every remaining person's name or other personal identifier exactly as it is written.
License plates often appear without the word "plate": a short code of letters and digits
(for example 7TRV218 or KDX 5390) mentioned with a vehicle, tag, or state is a PLATE.
Do not list places, dates, times, vehicle makes or models, road names like I-95, damage,
or bracketed placeholders like [PHONE_1].
If nothing remains, return an empty list."""


def build_agent(model: Model) -> Agent[None, IntakeLlmOutput]:
    return Agent(model, output_type=IntakeLlmOutput, instructions=INSTRUCTIONS, retries=2)


def apply_suggestions(text: str, suggestions: list[PiiSuggestion]) -> tuple[str, list[PiiType]]:
    """Redact model-suggested spans, but only ones that appear verbatim in the text."""
    applied: list[PiiType] = []
    for suggestion in sorted(suggestions, key=lambda s: len(s.text), reverse=True):
        span = suggestion.text
        if len(span) < 2 or PLACEHOLDER.search(span):
            continue
        if not appears_outside_placeholders(text, span):
            continue
        pii_type = PiiType(suggestion.pii_type)
        text = replace_outside_placeholders(text, span, next_placeholder(text, pii_type))
        applied.append(pii_type)
    return text, applied


def build_sanitized(text: str, removed: list[PiiType]) -> SanitizedSubmission:
    """Final re-scan: any PII still present sends the submission to manual review."""
    return SanitizedSubmission(
        text=text,
        pii_types_removed=sorted(set(removed)),
        requires_manual_review=bool(find_pii(text)),
    )


def scrub(raw: RawSubmission, agents: "Agents") -> SanitizedSubmission:
    text, removed = scrub_patterns(raw.text)
    result = agents.intake.run_sync(tag_narrative(text))
    text, suggested = apply_suggestions(text, result.output.suggestions)
    return build_sanitized(text, removed + suggested)
