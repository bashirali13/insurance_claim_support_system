# Data Model: Hardening and Release (003)

This phase makes small, backward-compatible additions to the phase 001 and 002 contracts
(`Contract`: frozen, `extra="forbid"`).

## Enum changes

| Enum | Change |
|---|---|
| `ProcessingStatus` | **+ `FAILED_UNEXPECTED`** (constitution v1.1.0) |

## New and changed models

### **`TraceEntry`** (new)
| Field | Type | Rule |
|---|---|---|
| `step` | `str` | one of `intake`, `assessment`, `risk`, `triage`, `routing`, `saved`, `failed` |
| `values` | `dict[str, str]` | built only from enum values, dates, field names, counts, and file names; never free text |

### `TaskResult` (phase 001)
Gains **`trace: list[TraceEntry] = []`**. The CLI prints it only with `--trace`; it's never stored.

## Customer-facing constants (CLI)

| Name | Text |
|---|---|
| `UNEXPECTED_MESSAGE` | `Something went wrong on our side. Please try again later.` |
| `INTERRUPTED_MESSAGE` | `Stopped. Nothing further was sent.` |
| exit codes | end-of-input → 0; Ctrl+C → 130; missing config → 1 (phase 001) |

## History detail (AC-11.4)

For a contact-change-only update, `HistoryEntry.detail` = `"contact change requested"`.

## Trace block format (rendered by `reporting.render_trace`)

```text
  ┌ trace ─ intake ───────────────────────────────
  │ pii_removed: PHONE, PERSON   manual_review: no
  ├ trace ─ assessment ───────────────────────────
  │ incident: COLLISION  injury: YES  missing: POLICE_REPORT
  │ coverage_lines: COLLISION, UM_UIM, PIP_MEDPAY
  ├ trace ─ risk ─────────────────────────────────
  │ sentiment: CONCERNED  indicators: INJURY_REPORTED, HIT_AND_RUN_NO_POLICE_REPORT
  │ risk: HIGH  teams: CLAIMS_ADJUSTER  follow_up_by: 2026-09-25
  └ trace ─ saved ────────────────────────────────
    claim: CLM-2026-0007  status: ESCALATED  report: CLM-2026-0007_20260924T101500.md
```

The format renders each entry's `values` as `key: value` pairs, wrapped at 100 characters. Keys
appear in insertion order, and empty values render as `-`.
