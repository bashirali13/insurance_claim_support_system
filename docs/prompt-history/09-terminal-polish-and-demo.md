# 09: Terminal Polish and the Live Demo Run (Phase 004)

**Branch:** `004-terminal-polish` · **Spec:** `specs/004-terminal-polish/`

## Objective

Wrap up the project. Replace example claim numbers with a format, give the user a demo script
that shows the whole system, run it live, and make replies easier to read in the terminal. The
stretch goal (a local web UI) was dropped by the user.

## Key prompts

- "When we give an example of a claim number, can we not put an actual number?" This led to
  `CLM-YYYY-NNNN` in the prompt and hint (AC-6.3 amended; merged with phase 003). It's saved as
  a standing preference.
- "Is there any expectation of police report number format?" Answer: no. Only whether a report
  was mentioned is recorded, never the number.
- "Give me a doc of samples that I can input and show to someone else." This produced
  `docs/demo-script.md`: seven stories covering every menu option, sentiment, routing, the
  guardrails, and error handling.
- "Run the stories live... Don't want to do stretch goal... once you get the system report back
  it instantly starts another prompt... users' eyes may not instantly go to the response."

## Recommendations and decisions

- **Pause after every reply** (`Press Enter to return to the menu.`). The app stays a loop, but
  the reply stays on screen. Accepted.
- **Show the full banner once**, then a short `=== Main menu ===` header. Accepted.
- **Frame every reply** with a title (`Your claim status`, `Your claim update`,
  `Your help request`). Accepted.
- **Clearing the screen was rejected.** It breaks piped runs and scrollback.
- **A short phase `004-terminal-polish`**, not the web-UI stretch phase. Accepted.
- **Test harness:** the `keyboard` fixture now prints prompts like the real `input()` does, so
  tests can see the pause and the prompt wording.

## Live demo run (2026-09-28, `deepseek/deepseek-v4-flash-0731`)

- All seven stories ran end to end (exit 0, 17 claims, 6 help requests), and they matched the
  script:
  - sentiment added Customer Relations for angry and distressed customers, with the risk level
    unchanged;
  - the lawyer mention moved every follow-up to 1 business day, with Special Review hidden;
  - the injection attempt was escalated quietly;
  - no personal values were shown.
- **Defect found (AC-14.1):** for "Someone smashed my car window and stole my laptop bag.", the
  model wrote `UNKNOWN` for the date and place instead of leaving them empty, so the checklist
  never asked for them. It was fixed deterministically: stated-unknown values count as missing.
  A live re-check then asked for the date, the place, and the police report.
- **Observation, no change:** for Spanish input, the model-written lines came back in Spanish
  while the fixed lines stayed in English. This is acceptable for v1.

## Deferred

- The web UI (dropped).
- Replies fully in the customer's language.
