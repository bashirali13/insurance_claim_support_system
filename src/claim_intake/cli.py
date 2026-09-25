"""Terminal interface (contracts/cli.md). The only module that reads input or prints."""

import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep library output out of the customer view

from dotenv import load_dotenv  # noqa: E402

from claim_intake.agents import create_agents  # noqa: E402
from claim_intake.config import ConfigError, build_model, load_settings  # noqa: E402
from claim_intake.orchestration import Deps, file_claim  # noqa: E402
from claim_intake.storage import ClaimStore, EventLog, ReportWriter  # noqa: E402

MAX_NARRATIVE_CHARS = 5000
RULE = "=" * 50
MENU = f"""{RULE}
 Northstar Auto Insurance: Claim Support
{RULE}
 Your information is protected. Personal details
 like phone numbers and addresses are removed
 before your claim is processed.

 1. File a new claim
 2. Check my claim status
 3. Add or correct details on my claim
 4. Get help with my claim
 5. Exit
"""
FILING_PROMPT = """
Tell us what happened, in your own words. Include when and where it
happened, what was damaged, and whether anyone was hurt.
Press Enter on an empty line when you're done."""
EMPTY_INPUT = "Please describe what happened, then press Enter on an empty line."
TOO_LONG = "That's longer than we can accept here (limit 5,000 characters). Please shorten it."
COMING_SOON = "This option is coming soon."
INVALID_CHOICE = "Please choose a number from 1 to 5."
GOODBYE = "Thank you for contacting Northstar Auto Insurance. Goodbye."
PROGRESS_WIDTH = 42


def print_progress(step: int, label: str) -> None:
    dots = "." * (PROGRESS_WIDTH - len(label))
    print(f"  [{step}/4] {label} {dots} done")


def read_narrative() -> str:
    """Read lines until an empty one; re-prompt until the text is non-empty and short enough."""
    while True:
        print(FILING_PROMPT)
        lines = []
        while (line := input("> ")).strip():
            lines.append(line)
        text = "\n".join(lines).strip()
        if not text:
            print(EMPTY_INPUT)
        elif len(text) > MAX_NARRATIVE_CHARS:
            print(TOO_LONG)
        else:
            return text


def run(deps: Deps) -> int:
    while True:
        print(MENU)
        choice = input("Choose an option (1-5): ").strip()
        if choice == "1":
            print()
            result = file_claim(read_narrative(), deps, on_progress=print_progress)
            print()
            print(result.customer_message)
            print()
        elif choice in {"2", "3", "4"}:
            print(COMING_SOON)
        elif choice == "5":
            print(GOODBYE)
            return 0
        else:
            print(INVALID_CHOICE)


def build_deps(root: Path) -> Deps:
    settings = load_settings(os.environ)
    return Deps(
        agents=create_agents(build_model(settings)),
        store=ClaimStore(root),
        reports=ReportWriter(root),
        events=EventLog(root),
        now=datetime.now,
    )


def main() -> int:
    load_dotenv()
    try:
        deps = build_deps(Path.cwd())
    except ConfigError as problem:
        print(problem)
        return 1
    return run(deps)
