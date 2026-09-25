"""Terminal interface (contracts/cli.md). The only module that reads input or prints."""

import argparse
import os
import sys
from datetime import datetime
from functools import partial
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep library output out of the customer view

from dotenv import load_dotenv  # noqa: E402

from claim_intake.agents import create_agents  # noqa: E402
from claim_intake.config import ConfigError, build_model, load_settings  # noqa: E402
from claim_intake.contracts import ClaimStatus, MenuTask  # noqa: E402
from claim_intake.existing_claims import check_status, get_help, update_claim  # noqa: E402
from claim_intake.orchestration import Deps, file_claim, record_unexpected  # noqa: E402
from claim_intake.reporting import format_follow_up, render_trace  # noqa: E402
from claim_intake.rules import normalize_claim_number  # noqa: E402
from claim_intake.storage import ClaimStore, EventLog, ReportWriter, load_samples  # noqa: E402

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
UPDATE_PROMPT = """
What would you like to add or correct?
Press Enter on an empty line when you're done."""
CLOSED_CLAIM = (
    "This claim is closed. If you need help with it, choose option 4 (Get help with my claim)."
)
EMPTY_INPUT = "Please describe what happened, then press Enter on an empty line."
TOO_LONG = "That's longer than we can accept here (limit 5,000 characters). Please shorten it."
INVALID_CHOICE = "Please choose a number from 1 to 5."
GOODBYE = "Thank you for contacting Northstar Auto Insurance. Goodbye."
UNEXPECTED_MESSAGE = "Something went wrong on our side. Please try again later."
INTERRUPTED_MESSAGE = "Stopped. Nothing further was sent."
INTERRUPTED_EXIT_CODE = 130  # conventional exit code for an interrupted program
CLAIM_NUMBER_PROMPT = "Enter your claim number (format CLM-YYYY-NNNN): "
OPTIONAL_CLAIM_NUMBER_PROMPT = "Enter your claim number (or press Enter if you don't have one): "
SKIP_HINT = "Press Enter to continue without one."
HELP_PROMPT = """
How can we help?
Press Enter on an empty line when you're done."""
BAD_CLAIM_NUMBER = "Claim numbers look like CLM-YYYY-NNNN. Please try again."
UNKNOWN_CLAIM = "We couldn't find that claim number. Please check it and try again."
PROGRESS_WIDTH = 42


def show_result(result, trace: bool) -> None:
    """Print the reply; with --trace, the sanitized staff trace follows (US10)."""
    print(result.customer_message)
    if trace and result.trace:
        print()
        print(render_trace(result.trace))


def print_progress(step: int, label: str, total: int = 4) -> None:
    dots = "." * (PROGRESS_WIDTH - len(label))
    print(f"  [{step}/{total}] {label} {dots} done")


def read_narrative(prompt: str = FILING_PROMPT) -> str:
    """Read lines until an empty one; re-prompt until the text is non-empty and short enough."""
    while True:
        print(prompt)
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


def ask_claim_number(deps: Deps, optional: bool = False) -> str | None:
    """Re-prompt until a claim number that exists is entered; an empty entry returns None.

    Optional (Get help): the hints also say Enter skips the claim number (AC-8.11).
    """
    while True:
        entry = input(OPTIONAL_CLAIM_NUMBER_PROMPT if optional else CLAIM_NUMBER_PROMPT)
        if not entry.strip():
            return None
        claim_id = normalize_claim_number(entry)
        if claim_id is None:
            print(BAD_CLAIM_NUMBER)
        elif not deps.store.exists(claim_id):
            print(UNKNOWN_CLAIM)
        else:
            return claim_id
        if optional:
            print(SKIP_HINT)


def privacy_hold_message(follow_up, today) -> str:
    when = f"by {format_follow_up(follow_up)}" if follow_up >= today else "soon"
    return (
        f"This claim is with a specialist for a privacy review. They'll contact you {when}, "
        "and you can share any updates with them then."
    )


def add_or_correct(deps: Deps, claim_id: str, trace: bool = False) -> None:
    """Option 3: refuse closed and privacy-review claims before asking for any text."""
    record = deps.store.load(claim_id)
    if record.status == ClaimStatus.CLOSED:
        print(CLOSED_CLAIM)
        return
    if record.assessment is None:
        print(privacy_hold_message(record.follow_up_date, deps.now().date()))
        return
    print()
    text = read_narrative(UPDATE_PROMPT)
    result = update_claim(claim_id, text, deps, on_progress=partial(print_progress, total=3))
    print()
    show_result(result, trace)
    print()


def get_help_with_claim(deps: Deps, trace: bool = False) -> None:
    """Option 4: the claim number is optional; only a real one is linked."""
    claim_id = ask_claim_number(deps, optional=True)
    print()
    text = read_narrative(HELP_PROMPT)
    result = get_help(claim_id, text, deps, on_progress=partial(print_progress, total=3))
    print()
    show_result(result, trace)
    print()


def file_new_claim(deps: Deps, trace: bool = False) -> None:
    """Option 1."""
    print()
    result = file_claim(read_narrative(), deps, on_progress=print_progress)
    print()
    show_result(result, trace)
    print()


def show_status(deps: Deps, trace: bool = False) -> None:
    """Option 2."""
    if claim_id := ask_claim_number(deps):
        print()
        print(check_status(claim_id, deps.store, deps.now().date()))
        print()


def update_details(deps: Deps, trace: bool = False) -> None:
    """Option 3."""
    if claim_id := ask_claim_number(deps):
        add_or_correct(deps, claim_id, trace)


# Menu choice → (action, task recorded on an unexpected error; None = write nothing, AC-6.8).
MENU_ACTIONS = {
    "1": (file_new_claim, MenuTask.FILE_CLAIM),
    "2": (show_status, None),
    "3": (update_details, MenuTask.UPDATE_DETAILS),
    "4": (get_help_with_claim, MenuTask.GET_HELP),
}


def attempt(deps: Deps, action, task: MenuTask | None, trace: bool = False) -> None:
    """Last-resort boundary (FR-301): a bug shows a fixed message and the menu comes back."""
    try:
        action(deps, trace)
    except EOFError:
        raise  # the terminal closed: handled by safe_run as Exit
    except Exception as exc:
        print(UNEXPECTED_MESSAGE)
        if task is not None:
            try:
                record_unexpected(deps, task, exc)
            except Exception:
                pass  # reporting must never turn a handled bug into a crash


def run(deps: Deps, trace: bool = False) -> int:
    while True:
        print(MENU)
        choice = input("Choose an option (1-5): ").strip()
        if choice in MENU_ACTIONS:
            attempt(deps, *MENU_ACTIONS[choice], trace=trace)
        elif choice == "5":
            print(GOODBYE)
            return 0
        else:
            print(INVALID_CHOICE)


def safe_run(deps: Deps, trace: bool = False) -> int:
    """End of input exits cleanly (AC-9.2); Ctrl+C stops without a traceback (AC-9.3)."""
    try:
        return run(deps, trace)
    except EOFError:
        print()
        print(GOODBYE)
        return 0
    except KeyboardInterrupt:
        print()
        print(INTERRUPTED_MESSAGE)
        return INTERRUPTED_EXIT_CODE


def build_deps(root: Path) -> Deps:
    settings = load_settings(os.environ)
    return Deps(
        agents=create_agents(build_model(settings)),
        store=ClaimStore(root),
        reports=ReportWriter(root),
        events=EventLog(root),
        now=datetime.now,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claim-support")
    parser.add_argument(
        "--load-samples", action="store_true", help="copy sample claims into data/claims/"
    )
    parser.add_argument(
        "--trace", action="store_true", help="show a sanitized staff trace after each reply"
    )
    args = parser.parse_args(argv)
    # A console that can't show a character (e.g. the trace's box lines) shows "?" instead of
    # crashing; the customer view stays plain text either way.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    load_dotenv()
    try:
        deps = build_deps(Path.cwd())
    except ConfigError as problem:
        print(problem)
        return 1
    if args.load_samples:
        print(f"Loaded {len(load_samples(Path.cwd()))} sample claims.")
    return safe_run(deps, args.trace)
