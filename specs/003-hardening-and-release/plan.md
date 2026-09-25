# Implementation Plan: Hardening and Release

**Branch**: `003-hardening-and-release` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-hardening-and-release/spec.md` (approved; 4
clarifications; 1 plan-time consistency fix: AC-9.1 vs AC-6.8). Constitution **v1.1.0**.

## Summary

This phase hardens the product and prepares it for release, with no new customer features:

1. **A CLI error boundary.** An unexpected bug shows a fixed message, writes a `FAILED_UNEXPECTED`
   report (except for status checks), and returns to the menu. End-of-input exits cleanly (0);
   Ctrl+C prints "Stopped…" and exits 130 after flows release any reserved number.
2. **`--trace`.** Flows return sanitized `TraceEntry` lists inside `TaskResult`; the CLI renders
   them only when asked; they're privacy-checked and never stored.
3. **An adversarial end-to-end suite** of at least 15 scripted scenarios with one shared
   guarantees check, plus a live set of at least 12. The contact-change history detail is fixed.
4. **Release documentation.** A README, a Mermaid architecture document, and real-model sample
   outputs, all guarded by doc tests (links, CLI flags, PII, required sections).

## Technical Context

**Language/Version**: Python 3.13 (uv)

**Primary Dependencies**: unchanged. `argparse` handles `--trace`.

**Storage**: unchanged. Traces are never stored; samples are committed in `docs/samples/`.

**Testing**: pytest with scripted models. The CLI tests simulate `EOFError` and
`KeyboardInterrupt` through scripted input. Doc tests parse the Markdown.

**Project Type**: single-project CLI.

**Constraints**:
- the core never prints
- no traceback on any customer path
- trace values come only from structured contract fields

**Scale/Scope**: about 10 source edits, 4 new test modules, and 4 documentation files.

## Constitution Check (v1.1.0)

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Pre | Post-design |
|---|---|---|---|
| I. Spec-Driven | Approved spec; spec changes first | ✅ approved; AC-9.1 fix made spec-first | ✅ |
| II. Test-First | Every behavior from an AC-named test | ✅ | ✅ documentation ACs use named quickstart steps as SC-306 allows; everything else is automated |
| III. Privacy by Construction | Trace, samples, and error reports can't leak PII | ✅ | ✅ trace built from structured fields plus `find_pii` gate; samples PII-checked by a test; unexpected-error reports contain only the class name |
| IV. Typed Contracts | New data is typed and frozen | ✅ | ✅ `TraceEntry` is a `Contract`; `TaskResult.trace` defaults to empty |
| V. Deterministic Safety | No model involvement in new safety logic | ✅ | ✅ error boundary, EOF and Ctrl+C handling, and trace rendering are pure code |
| VI. Human-in-the-Loop | No decision language anywhere new | ✅ | ✅ the adversarial suite asserts it across the full pipeline |
| VII. Simplicity; core never prints | No new frameworks; UI stays thin | ✅ | ✅ the boundary lives in the CLI; `record_unexpected` in the core only writes a report |
| Tech constraints (v1.1.0) | Failure statuses as listed | ✅ `FAILED_UNEXPECTED` added by amendment | ✅ |

**Result: PASS.** Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-hardening-and-release/
├── spec.md, plan.md, research.md (R1–R8), data-model.md, quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source and docs (changes)

```text
src/claim_intake/
├── contracts.py        # + FAILED_UNEXPECTED, TraceEntry; TaskResult.trace
├── orchestration.py    # TaskRun: trace entries, release_reservation(); record_unexpected();
│                       #   file_claim: trace entries + KeyboardInterrupt release
├── existing_claims.py  # update/help trace entries; help KeyboardInterrupt release;
│                       #   contact-change history detail
├── reporting.py        # + render_trace (with privacy gate)
└── cli.py              # error boundary, EOF/Ctrl+C, --trace
tests/
├── unit/test_trace.py              # render_trace format and privacy gate
├── unit/test_docs.py               # README/architecture links, flags, Mermaid modules; samples PII and sections
├── integration/test_resilience.py  # AC-9.x via scripted input and injected failures
├── integration/test_trace_flows.py # AC-10.x per flow
├── integration/test_adversarial.py # AC-11.1, 11.2 (≥ 15 scenarios)
└── live/test_live_eval.py          # + adversarial set (AC-11.3)
docs/
├── architecture.md                 # NEW: Mermaid flowchart + sequence diagram
└── samples/*.md                    # NEW: real-model reply + report pairs
README.md                           # REWRITTEN
```

**Structure Decision**: no new source modules. Each change lands where its responsibility already
lives: rendering in `reporting`, run bookkeeping in `orchestration`, and user interaction in `cli`.

## Implementation Order (for /speckit-tasks)

1. **US9 (P1):**
   - `FAILED_UNEXPECTED`, `record_unexpected`
   - the CLI boundary
   - EOF and Ctrl+C in `main`
   - `release_reservation` plus `KeyboardInterrupt` handling in `file_claim` and `get_help`
2. **US10 (P2):**
   - `TraceEntry`, `TaskResult.trace`
   - `render_trace`
   - trace entries in each flow and on failure
   - `--trace` in the CLI
3. **US11 (P3):**
   - the contact-change history detail
   - the adversarial suite (filing, update, help)
   - the live adversarial set and run
4. **US12 (P4):**
   - doc tests (Red)
   - `docs/architecture.md`
   - `README.md`
   - capture and commit samples
   - quickstart manual steps
5. **Close:** prompt history 08, the phase PR and completion check, then the stretch phase 004
   decision.

## Complexity Tracking

No constitution violations to justify.
