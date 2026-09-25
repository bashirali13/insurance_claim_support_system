"""Safety checks for any customer-facing text a model writes (research R8, specs/002 FR-216)."""

import re

from pydantic_ai import ModelRetry

from claim_intake.pii import PLACEHOLDER, find_pii

# Decision language the model must never write.
FORBIDDEN_TERMS = re.compile(
    r"\b(?:covered|coverage decision|approved?|denied|deny|at fault|your fault|liable|payout"
    r"|settlement amount)\b|\$\s?\d",
    re.IGNORECASE,
)


def check_customer_text(*texts: str) -> None:
    """Raise ModelRetry so the model rewrites text with placeholders, PII, or decisions."""
    text = "\n".join(texts)
    if PLACEHOLDER.search(text):
        raise ModelRetry("Remove bracketed placeholders; describe without personal details.")
    if find_pii(text):
        raise ModelRetry("Remove personal details such as phone numbers or emails.")
    if FORBIDDEN_TERMS.search(text):
        raise ModelRetry("Remove statements about coverage, fault, approval, or money.")
