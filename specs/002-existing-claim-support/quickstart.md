# Quickstart: Validate Existing-Claim Support (002)

See `contracts/` for the exact texts and formats. Prerequisites are the same as phase 001.

## 1. Deterministic suite

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

**Expected:** all green, including phase 001's tests (with AC-5.13 now expecting `task`). Every
AC-6.1 … AC-8.13 (including AC-7.12) appears in a test name (SC-206):

```bash
uv run pytest --collect-only -q | grep -oE "test_ac_[678]_[0-9]+" | sort -u
```

## 2. Runtime data stays out of git (FR-204a)

```bash
git check-ignore data/claims/x.json data/help/x.json   # both paths printed
git check-ignore data/samples/CLM-2026-0001.json        # prints nothing (committed)
```

## 3. Live model checks (optional)

```bash
uv run pytest -m live -s
```

**Expected:**
- phase 001 checks still pass
- SC-203: update mode ≥ 90% on `update_cases.json`
- SC-204: help triage ≥ 90% on `help_cases.json`
- SC-205: no personal values anywhere

## 4. Manual walkthrough (in a scratch folder)

```bash
uv run claim-support --load-samples
```

| Step | Expect |
|---|---|
| Option 2 → `clm-2026-0005` | the status block for the hit-and-run; police report still needed; next step dated |
| Option 2 → `CLM-2026-0006` | privacy-review block: no incident type or facts |
| Option 2 → `CLM-2026-9999` | "We couldn't find that claim number…" |
| Option 3 → `CLM-2026-0005` → "The police report number is 26-44817. It was actually around 7pm." | Added: police report; Corrected: when it happened; the police report drops off the still-needed list |
| Option 3 → `CLM-2026-0005` → "Actually nobody was hurt." | an adjuster confirms by the next business day; option 2 then shows "Waiting for an adjuster to confirm: injuries to you or your passengers" |
| Option 3 → `CLM-2026-0005` → "My new phone number is 555-908-1200." | Policy Services by +3 business days; the number appears in no file |
| Option 3 → `CLM-2026-0004` | the closed-claim message; no text requested |
| Option 4 → Enter → "Nobody called me back in a week, I'm frustrated." | Customer Relations; a `HELP-…` reference |
| Option 4 → Enter → "Can I get a rental car?" | the redirect only; no reference |
| Option 4 → `CLM-2026-0005` → "My lawyer will contact you." | a claims adjuster by the next business day (Special Review never shown); claim history gains HELP_REQUESTED |

After the walkthrough, confirm `logs/events.log` has `task` on every line and no status-check
lines.
