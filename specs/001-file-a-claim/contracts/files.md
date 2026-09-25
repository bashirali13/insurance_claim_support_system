# Contract: Files Written (001)

Every file passes the FR-001 privacy guard before it is written. All paths are relative to the
repository root.

## Claim record: `data/claims/<CLM-YYYY-NNNN>.json`

`ClaimRecord.model_dump_json(indent=2)`. Example (fictional, protected):

```json
{
  "claim_id": "CLM-2026-0007",
  "status": "ESCALATED",
  "filed_at": "2026-09-24T10:15:00",
  "assessment": {
    "incident_type": "COLLISION",
    "um_uim_subtype": "HIT_AND_RUN",
    "incident_date": "yesterday around 6pm",
    "location": "Main St",
    "damage_areas": ["rear bumper"],
    "customer_side_injured": "YES",
    "others_injured": "NO",
    "other_party_involved": "YES",
    "other_property_damaged": "NO",
    "vehicle_drivable": "UNKNOWN",
    "police_report_mentioned": "UNKNOWN",
    "key_facts": ["Rear-ended at a red light", "Other driver left the scene"],
    "contradictions": [],
    "injury_present": "YES",
    "missing_information": ["POLICE_REPORT"],
    "coverage_lines": ["COLLISION", "UM_UIM", "PIP_MEDPAY"]
  },
  "teams": ["CLAIMS_ADJUSTER"],
  "follow_up_date": "2026-09-25",
  "history": [{"at": "2026-09-24T10:15:00", "event": "FILED"}]
}
```

In this example the risk is HIGH, because `INJURY_REPORTED` + `HIT_AND_RUN_NO_POLICE_REPORT` are
two indicators, so the status is `ESCALATED`.

**Privacy-review record:** `assessment` is `null`, `teams` is `["PRIVACY_REVIEW"]`, and history is
`[{"event": "PRIVACY_REVIEW_OPENED"}]`.

## Internal report: `output/<claim_id>_<YYYYMMDDTHHMMSS>.md`

Sections, always in this order (FR-024):

```markdown
# Claim Intake Report — <claim_id>
- **Processing status:** COMPLETED
- **Task:** File a new claim
- **Filed:** <timestamp>

## Summary
## Incident
## Facts
## Coverage Lines to Review
## Missing Information
## Contradictions
## Sentiment and Risk
## Routing and Follow-up
## Privacy
---
> Supports intake and triage only. Not a coverage, fault, or claim decision.
```

Empty lists render as `None recorded.`

**Status-only report** (every failure, and privacy review): the title, processing status, claim ID
(or `UNFILED`), failed step, error category, and the notice. It contains no narrative or facts.
For failures before a claim number exists, the file name is `output/UNFILED_<timestamp>.md`.

## Event log: `logs/events.log`

JSON Lines, append-only, one line per pipeline step:

```json
{"ts":"2026-09-24T10:15:02","claim_id":null,"step":"INTAKE","outcome":"COMPLETED","duration_ms":1840,"error_category":null}
```

`claim_id` is `null` until a number is issued. `error_category` is an exception class name only
(e.g., `"ModelHTTPError"`).
