# Quickstart: Validate Hardening and Release (003)

## 1. Deterministic suite

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pytest --collect-only -q | grep -oE "test_ac_(9|10|11|12)_[0-9]+" | sort -u   # SC-306
```

**Expected:** all green, and every AC-9.x, AC-10.x, AC-11.x, and AC-12.2/12.4 appears.

## 2. Live checks (optional)

```bash
uv run pytest -m live -k adversarial -s    # SC-304 / AC-11.3
```

## 3. Named manual steps (SC-306)

| Step | Covers | Do | Expect |
|---|---|---|---|
| Q-12.1 | AC-12.1, SC-305 | In an empty folder: clone, `uv sync`, create `.env`, then follow the README to `--load-samples`, file S01, and check its status | every command works as written; under 10 minutes |
| Q-12.3 | AC-12.3 | View `README.md` and `docs/architecture.md` on GitHub | both Mermaid diagrams render and match the modules in `src/claim_intake/` |
| Q-9 | AC-9.2, 9.3 | `printf '2\n' \| uv run claim-support`; then start the app and press Ctrl+C mid-filing | goodbye and exit 0; "Stopped…" and exit 130; no traceback; no empty claim file |
| Q-10 | AC-10.x | `uv run claim-support --load-samples --trace` → file S10, update 0005, get help | trace blocks after each reply, with no narrative or personal values |

## 4. Capturing samples (one-time documentation step, research R6)

Run the real CLI with the live model in a scratch folder for the scenarios in research R6. Copy each
reply and its report into `docs/samples/<scenario>.md`, review them, then run
`uv run pytest -k ac_12_4`.
