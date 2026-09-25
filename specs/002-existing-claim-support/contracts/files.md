# Contract: Files (002)

This extends `specs/001-file-a-claim/contracts/files.md`. Everything written still passes the
FR-001 privacy guard first.

| Path | In git? | Written by | Content |
|---|---|---|---|
| `data/samples/CLM-2026-000{1..6}.json` | **yes** | hand-authored | `ClaimRecord` (fictional, sanitized) |
| `data/claims/*.json` | **no** (FR-204a) | filing, updates, `--load-samples`, help linking | `ClaimRecord` |
| `data/help/HELP-YYYY-NNNN.json` | **no** (FR-204a) | Get help | `HelpRecord` |
| `output/*.md` | no | all flows | reports |
| `logs/events.log` | no | filing, updates, help | JSON Lines, now with `task` |

## Sample claims (research R7)

| Claim | Scenario | Status | Notes |
|---|---|---|---|
| CLM-2026-0001 | S01 rear-end | `UNDER_REVIEW` | nothing missing |
| CLM-2026-0002 | S04 theft | `AWAITING_INFORMATION` | police report missing |
| CLM-2026-0003 | S06 hail | `SUBMITTED` | |
| CLM-2026-0004 | S08 windshield | `CLOSED` | |
| CLM-2026-0005 | S10 hit-and-run with injury | `ESCALATED` | police report missing; time "yesterday around 6pm"; used by E04–E07 |
| CLM-2026-0006 | privacy review | `ESCALATED` | `assessment: null`, team `PRIVACY_REVIEW` |

All are filed between Sep 14 and Sep 23, 2026, and contain no personal values.

## Update report: `output/<claim_id>_<timestamp>.md`

It uses phase 001's header, with `Task: Add or correct details`, then these sections:
`## Added`, `## Corrected`, `## Pending Adjuster Confirmation`, `## Contact Change`,
`## Missing Information`, `## Sentiment and Risk`, `## Routing and Follow-up`, `## Privacy`,
followed by the decision notice. Empty sections read `None recorded.`

## Help report: `output/<HELP-id>_<timestamp>.md`

Header with `Task: Get help with my claim` and `Claim: <claim_id or None recorded.>`, then:
`## Request` (protected text), `## Categories`, `## Sentiment`, `## Routing and Follow-up`,
`## Privacy`, followed by the notice.

## Event log line (FR-218)

```json
{"ts":"…","claim_id":"CLM-2026-0005","task":"UPDATE_DETAILS","step":"ASSESSMENT","outcome":"COMPLETED","duration_ms":2140,"error_category":null}
```

For Get help, `claim_id` holds the linked claim number if there is one, otherwise the help
reference once it's issued.
