# Contract: Terminal Interface — Hardening (003)

This extends `specs/001-file-a-claim/contracts/cli.md` and `specs/002-existing-claim-support/contracts/cli.md`.

## Launch

```text
uv run claim-support [--load-samples] [--trace]
```

## Failure handling at the terminal (US9)

| Situation | Customer sees | Then | Written |
|---|---|---|---|
| Unexpected error in options 1, 3, 4 | `Something went wrong on our side. Please try again later.` | menu again | status-only report, `FAILED_UNEXPECTED` |
| Unexpected error in option 2 | same message | menu again | nothing (AC-6.8) |
| End of input at any prompt | `Thank you for contacting Northstar Auto Insurance. Goodbye.` | exit 0 | nothing new |
| Ctrl+C at any prompt or during processing | `Stopped. Nothing further was sent.` | exit 130 | reserved numbers released; no report |

No path prints `Traceback`, an exception class name, a file path, or a model name.

## Trace mode (US10)

With `--trace`, the block from `../data-model.md` is printed after each reply of options 1, 3, and
4 (including failure and redirect-only replies). Option 2 prints no trace. Without `--trace`, output
is unchanged from phase 002.
