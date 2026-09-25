"""Menu options 2-4 for claims that already exist (specs/002, contracts/agents.md)."""

from datetime import date

from claim_intake.reporting import render_status
from claim_intake.storage import ClaimStore


def check_status(claim_id: str, store: ClaimStore, today: date) -> str:
    """Option 2: rendered from the saved record only. No model call, no writes (AC-6.8)."""
    return render_status(store.load(claim_id), today)
