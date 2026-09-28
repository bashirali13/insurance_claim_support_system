# Feature Specification: Terminal Polish

**Feature Branch**: `004-terminal-polish` · **Created**: 2026-09-28 · **Status**: Approved

**Input**: "Once you get the system report back after you enter stuff as a user it also instantly
starts another prompt... it can be a lot of text at once and users' eyes may not instantly go to
the response."

## Problem

After every task, the app reprints the 11-line banner, the privacy note, and the menu right away.
The customer's reply scrolls up and the eye lands on the menu. Only the new-claim reply is framed,
so status, update, and help replies blend into the text around them.

## User Story 13: The reply stays in focus (P1)

A customer finishes a task and reads the reply at their own pace. It stands out from the menu,
and the menu comes back only when they're ready.

### Acceptance Scenarios

1. **AC-13.1**: **Given** any reply is shown (options 1, 3, 4, a found claim for option 2, or the
   unexpected-error message), **When** it finishes printing, **Then** the app shows
   `Press Enter to return to the menu.` and waits. Anything typed there is ignored. End of input
   exits as usual (exit 0), and Ctrl+C stops as usual (exit 130). Returning to the menu without a
   reply (an empty claim number, or an invalid menu choice) doesn't pause.
2. **AC-13.2**: **Given** the app starts, **When** the menu is first shown, **Then** the full
   banner and privacy note appear once. Every later menu is the short form: a `Main menu` rule
   line and the five options.
3. **AC-13.3**: **Given** a status, update, or help reply, **When** it is shown, **Then** it is
   framed like the new-claim reply: a dashed rule, a title line (`Your claim status`,
   `Your claim update`, or `Your help request`), a dashed rule, the reply, and a closing rule.
   Replies that are already framed (a completed new claim) aren't framed twice. Other filing
   outcomes (privacy review, failures) use the title `Your claim`.

## Requirements

- **FR-401**: The pause, short menu, and frames live only in the CLI. Reply wording from the
  flows and `reporting.py` doesn't change.
- **FR-402**: With `--trace`, the trace prints inside the pause, after the framed reply.

## Success Criteria

- **SC-401**: After any task, the last lines on screen are the framed reply (and the trace, if
  on) followed by the pause prompt.
- **SC-402**: The full suite stays green and ruff stays clean.

## Out of Scope

Clearing the screen (it breaks piped runs and scrollback), colors, and the web UI.
