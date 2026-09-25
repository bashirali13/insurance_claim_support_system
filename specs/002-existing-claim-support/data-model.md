# Data Model: Existing-Claim Support (002)

This phase extends phase 001's contracts (`specs/001-file-a-claim/data-model.md`). Every model is a
`Contract` (frozen, `extra="forbid"`), and every category is a `StrEnum`. **Bold** marks what's
new or changed.

---

## Enum changes

| Enum | Change |
|---|---|
| `ClaimStatus` | **+ `UNDER_REVIEW`, `CLOSED`** (staff-set; only appear via sample data this phase) |
| `Team` | **+ `POLICY_SERVICES`** |
| **`MenuTask`** (new) | `FILE_CLAIM`, `UPDATE_DETAILS`, `GET_HELP` |
| **`RequestCategory`** (new) | `COMPLAINT`, `SERVICE_DELAY`, `CLAIM_QUESTION`, `SPEAK_TO_ADJUSTER`, `CONTACT_CHANGE`, `FILE_A_CLAIM`, `OUT_OF_SCOPE` |

---

## Claim record changes (backward compatible, research R8)

### `HistoryEntry`
| Field | Type | Change |
|---|---|---|
| `at` | `datetime` | |
| `event` | `Literal["FILED", "PRIVACY_REVIEW_OPENED", **"DETAILS_UPDATED"**, **"HELP_REQUESTED"**]` | extended |
| **`detail`** | `str \| None = None` | changed field names (e.g. `"incident_date, police_report_mentioned"`) or a help reference. Never values. |

### **`PendingChange`** (new)
| Field | Type | Rule |
|---|---|---|
| `field` | `Literal["incident_type", "um_uim_subtype", "customer_side_injured", "others_injured", "other_party_involved"]` | sensitive fields only |
| `requested_value` | `str` | sanitized (comes from model output over scrubbed text) |
| `requested_at` | `datetime` | |

### `ClaimRecord`
Phase 001 fields, plus **`pending_changes: list[PendingChange] = []`**.

---

## Update (US7)

### **`UpdateLlmOutput`** (LLM output of `assessment_update`)
| Field | Type |
|---|---|
| `updated` | `AssessmentLlmOutput` (the full facts after applying the customer's update) |
| `contact_change_requested` | `bool` |

### **`FieldChange`**
| Field | Type |
|---|---|
| `field` | `str` (an `AssessmentLlmOutput` field name) |
| `old` | `str \| None` (display value) |
| `new` | `str \| None` |

### **`FactChanges`** (output of `rules.diff_facts`, research R2)
| Field | Type |
|---|---|
| `added` | `list[FieldChange]` |
| `corrected` | `list[FieldChange]` (non-sensitive, applied) |
| `sensitive` | `list[FieldChange]` (held as `PendingChange`) |
| `applied` | `AssessmentLlmOutput` (saved facts with added and non-sensitive corrected changes applied; sensitive fields keep their saved values) |

`FactChanges.is_empty` is true when there is nothing added, corrected, or sensitive (AC-7.6).

### Status after update (FR-208): `rules.status_after_update(current, level, missing)`

1. `CLOSED` → not reachable, because updates are refused before processing (AC-7.7).
2. `ESCALATED` → stays `ESCALATED`.
3. `level == HIGH` → `ESCALATED`.
4. `UNDER_REVIEW` → stays `UNDER_REVIEW`.
5. `missing` non-empty → `AWAITING_INFORMATION`.
6. otherwise → `SUBMITTED`.

### Follow-up after update (research R3)
| Promise | Business days | Customer line |
|---|---|---|
| routing (`rules.follow_up_days`) | 1 or 2 | "A claims adjuster will contact you by …" (+ Customer Relations when routed) |
| each pending change | 1 | "An adjuster will confirm this change with you by …" |
| contact change | 3 | "Our Policy Services team will confirm your new contact details with you by …" |

`ClaimRecord.follow_up_date` = the earliest promise date.

### Field wording for update replies and status (reporting table)
| Field | Customer wording |
|---|---|
| `incident_date` | when it happened |
| `location` | where it happened |
| `damage_areas` | damage |
| `police_report_mentioned` | police report |
| `vehicle_drivable` | whether the car can be driven |
| `other_property_damaged` | damage to other property |
| `incident_type` | what kind of incident it was |
| `um_uim_subtype` | the other driver's insurance situation |
| `customer_side_injured` | injuries to you or your passengers |
| `others_injured` | injuries to other people |
| `other_party_involved` | whether another party was involved |

---

## Help (US8)

### **`HelpTriageLlmOutput`** (LLM output of `help_triage`)
| Field | Type |
|---|---|
| `sentiment` | `Sentiment` |
| `categories` | `list[RequestCategory]` (1–3 items) |
| `legal_representation_mentioned` | `bool` |
| `possible_prompt_injection` | `bool` |
| `rationale` | `str` (1–300 chars) |

### **`HelpReplyLlmOutput`** (LLM output of `help_reply`; shared validator)
| Field | Type |
|---|---|
| `opening_line` | `str` |

### **`TeamPromise`**
| Field | Type |
|---|---|
| `team` | `Team` |
| `business_days` | `int` |
| `follow_up_date` | `date` |

### Help routing (FR-213): `rules.help_routing(triage, text) -> list[TeamPromise without date]`
| Input | Adds |
|---|---|
| `COMPLAINT`, `SERVICE_DELAY` | `CUSTOMER_RELATIONS`, 2 days |
| `CLAIM_QUESTION`, `SPEAK_TO_ADJUSTER` | `CLAIMS_ADJUSTER`, 2 days |
| `CONTACT_CHANGE` | `POLICY_SERVICES`, 3 days |
| `FILE_A_CLAIM`, `OUT_OF_SCOPE` | nothing |
| sentiment `DISTRESSED` / `ANGRY` | `CUSTOMER_RELATIONS`, 2 days |
| legal flag, injection flag, or phrase-list match | `SPECIAL_REVIEW` + `CLAIMS_ADJUSTER`, then **every** promise becomes 1 day |

Teams are deduplicated (keeping the fewest days) and ordered in `Team` declaration order.

### **`HelpRecord`** (`data/help/<HELP-YYYY-NNNN>.json`)
| Field | Type | Rule |
|---|---|---|
| `help_id` | `str` | `^HELP-\d{4}-\d{4}$` |
| `claim_id` | `str \| None` | only a claim that exists (AC-8.11) |
| `filed_at` | `datetime` | |
| `sentiment` | `Sentiment \| None` | `None` only for privacy review (AC-8.12) |
| `categories` | `list[RequestCategory]` | empty only for privacy review |
| `routed` | `list[TeamPromise]` | ≥ 1 (no record when nothing is routed); privacy review → `[PRIVACY_REVIEW, 3 days]` |
| `history` | `list[HistoryEntry]` | `[{event: "HELP_REQUESTED"}]` |

---

## Event log

`EventLogEntry` gains **`task: MenuTask`** (FR-218). Phase 001's filing flow sets `FILE_CLAIM`.

---

## Claim-number handling (FR-201): `rules.normalize_claim_number(text) -> str | None`

The text is trimmed and uppercased. It returns the normalized ID if it matches
`^CLM-\d{4}-\d{4}$`, otherwise `None`. An empty input is handled by the CLI (it returns to the
menu, or skips in Get help).

---

## Status wording (AC-6.5)
| Status | Wording |
|---|---|
| `SUBMITTED` | Received and waiting for review |
| `AWAITING_INFORMATION` | Waiting for information from you |
| `UNDER_REVIEW` | Under review by a claims adjuster |
| `ESCALATED` | With a specialist team for priority review |
| `CLOSED` | Closed |

Incident-type wording: `COLLISION` → "Collision", `ANIMAL_STRIKE` → "Animal strike", and so on
(title case, with underscores as spaces).
