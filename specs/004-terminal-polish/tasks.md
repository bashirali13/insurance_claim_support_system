# Tasks: Terminal Polish

All work is in `src/claim_intake/cli.py` and `tests/integration/test_cli.py`. Red → Green per AC.

- [X] T001 [US13] Red: tests for AC-13.1 (pause after every reply type; no pause without a reply;
  EOF and Ctrl+C at the pause), AC-13.2 (banner once, short menu after), and AC-13.3 (frames and
  titles; the new-claim reply isn't double-framed). Update existing scripts and banner counts.
- [X] T002 [US13] Green: `pause()`, `BANNER` + `SHORT_MENU`, and `framed(title, text)` in the CLI.
- [X] T003 Update `docs/user-experience.md` (§3 to §7 screens) and `specs/002-existing-claim-support/contracts/cli.md`.
- [ ] T004 Final ruff and pytest, a real terminal check, prompt history 09, PR, and the
  phase-completion check.
