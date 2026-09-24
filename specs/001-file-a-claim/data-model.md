# Data Model: File a New Claim (001)

All contracts are Pydantic models with `model_config = ConfigDict(frozen=True, extra="forbid")`.
Every category is a `StrEnum`. "LLM output" models are what an agent's model may return; every
other model is built or completed by deterministic code (see research R3).

---

## Enums

| Enum | Values |
|---|---|
| `PiiType` | `PHONE`, `EMAIL`, `SSN`, `CARD`, `DOB`, `DRIVER_LICENSE`, `VIN`, `PLATE`, `POLICY_NUMBER`, `ADDRESS`, `PERSON`, `OTHER_IDENTIFIER` |
| `SuggestedPiiType` | `PERSON`, `PLATE`, `DRIVER_LICENSE`, `OTHER_IDENTIFIER` (the only types the model may suggest) |
| `IncidentType` | `COLLISION`, `THEFT`, `VANDALISM`, `WEATHER`, `FIRE`, `GLASS`, `ANIMAL_STRIKE`, `UNKNOWN`, `MIXED` |
| `UmUimSubtype` | `HIT_AND_RUN`, `UNINSURED`, `COVERAGE_DENIED`, `UNDERINSURED` |
| `TriState` | `YES`, `NO`, `UNKNOWN` |
| `MissingItem` | `WHAT_HAPPENED`, `INCIDENT_DATE`, `LOCATION`, `DAMAGE_DESCRIPTION`, `OTHER_PARTY_INVOLVEMENT`, `POLICE_REPORT` |
| `CoverageLine` | `COLLISION`, `COMPREHENSIVE`, `LIABILITY_BODILY_INJURY`, `LIABILITY_PROPERTY_DAMAGE`, `UM_UIM`, `PIP_MEDPAY` |
| `Sentiment` | `CALM`, `CONCERNED`, `FRUSTRATED`, `DISTRESSED`, `ANGRY` |
| `RiskIndicator` | `INJURY_REPORTED`, `HIT_AND_RUN_NO_POLICE_REPORT`, `CONTRADICTORY_STATEMENTS`, `CRITICAL_INFO_MISSING`, `MIXED_INCIDENTS`, `LEGAL_REPRESENTATION_MENTIONED`, `POSSIBLE_PROMPT_INJECTION` |
| `RiskLevel` | `LOW`, `MEDIUM`, `HIGH` |
| `Team` | `CLAIMS_ADJUSTER`, `CUSTOMER_RELATIONS`, `SPECIAL_REVIEW`, `PRIVACY_REVIEW` (`POLICY_SERVICES` is added in phase 002) |
| `ClaimStatus` | `SUBMITTED`, `AWAITING_INFORMATION`, `ESCALATED` (`UNDER_REVIEW` and `CLOSED` are used from phase 002) |
| `ProcessingStatus` | `COMPLETED`, `REJECTED_INPUT`, `MANUAL_REVIEW_REQUIRED`, `FAILED_MODEL_ERROR`, `FAILED_VALIDATION`, `FAILED_OUTPUT` |
| `PipelineStep` | `VALIDATE_INPUT`, `INTAKE`, `ASSESSMENT`, `RISK`, `SUMMARY`, `PRIVACY_GUARD`, `SAVE` |

Enums are added only when a test needs them. The phase-002 values in parentheses are listed for
orientation and are **not** implemented in this phase.

---

## Intake & PII

### `RawSubmission` (orchestrator and intake only)
| Field | Type | Rule |
|---|---|---|
| `text` | `str` | 1–5,000 chars after stripping; whitespace-only is rejected before construction (FR-027) |

### `PiiSuggestion` (LLM output item)
| Field | Type |
|---|---|
| `text` | `str` |
| `pii_type` | `SuggestedPiiType` |

### `IntakeLlmOutput` (LLM output)
| Field | Type |
|---|---|
| `suggestions` | `list[PiiSuggestion]` |

### `SanitizedSubmission`: the only narrative type that downstream code accepts
| Field | Type | Rule |
|---|---|---|
| `text` | `str` | contains placeholders, no FR-001 matches (unless `requires_manual_review`) |
| `pii_types_removed` | `list[PiiType]` | sorted, unique; types only (FR-005, AC-1.9) |
| `requires_manual_review` | `bool` | true when the FR-004 re-scan finds anything |

---

## Assessment

### `Contradiction`
| Field | Type |
|---|---|
| `statement_a` | `str` (quoted from the protected narrative) |
| `statement_b` | `str` |

### `AssessmentLlmOutput` (LLM output)
| Field | Type | Notes |
|---|---|---|
| `incident_type` | `IncidentType` | |
| `um_uim_subtype` | `UmUimSubtype \| None` | only when another driver fled, was uninsured, was denied, or was underinsured |
| `incident_date` | `str \| None` | as stated ("yesterday around 6pm") |
| `location` | `str \| None` | general location as stated |
| `damage_areas` | `list[str]` | e.g., "rear bumper" |
| `customer_side_injured` | `TriState` | customer or their passengers |
| `others_injured` | `TriState` | people outside the customer's car |
| `other_party_involved` | `TriState` | |
| `other_property_damaged` | `TriState` | another vehicle or property |
| `vehicle_drivable` | `TriState` | |
| `police_report_mentioned` | `TriState` | |
| `key_facts` | `list[str]` | at most 6 short items |
| `contradictions` | `list[Contradiction]` | |

### `ClaimAssessment` (contract) = every `AssessmentLlmOutput` field, plus:
| Field | Type | Computed by |
|---|---|---|
| `injury_present` | `TriState` | `YES` if either injury field is `YES`; `UNKNOWN` if an injury contradiction exists or either is `UNKNOWN`; else `NO` |
| `missing_information` | `list[MissingItem]` | checklist rules (below) |
| `coverage_lines` | `list[CoverageLine]` | coverage rules (below) |

#### Missing-information checklist (FR-013)
| Incident type | Missing if… |
|---|---|
| all except `UNKNOWN`/`MIXED` | `incident_date` is None → `INCIDENT_DATE`; `location` is None → `LOCATION`; `damage_areas` empty → `DAMAGE_DESCRIPTION` (**not for `THEFT`**) |
| `COLLISION` | + `other_party_involved` = `UNKNOWN` → `OTHER_PARTY_INVOLVEMENT`; + `POLICE_REPORT` if (`um_uim_subtype` = `HIT_AND_RUN` **or** `injury_present` = `YES`) **and** `police_report_mentioned` ≠ `YES` |
| `THEFT`, `VANDALISM` | + `POLICE_REPORT` if `police_report_mentioned` ≠ `YES` |
| `UNKNOWN` | `WHAT_HAPPENED` always; + `INCIDENT_DATE`, `LOCATION` if None |
| `MIXED` | none |

#### Coverage-line rules (FR-014): each true condition adds its line once, in enum order
| Condition | Line |
|---|---|
| `incident_type == COLLISION` | `COLLISION` |
| `incident_type in {THEFT, VANDALISM, WEATHER, FIRE, GLASS, ANIMAL_STRIKE}` | `COMPREHENSIVE` |
| `others_injured == YES` | `LIABILITY_BODILY_INJURY` |
| `other_property_damaged == YES` | `LIABILITY_PROPERTY_DAMAGE` |
| `um_uim_subtype is not None` | `UM_UIM` |
| `customer_side_injured == YES` | `PIP_MEDPAY` |

---

## Sentiment, risk, and routing

### `RiskLlmOutput` (LLM output)
| Field | Type |
|---|---|
| `sentiment` | `Sentiment` |
| `legal_representation_mentioned` | `bool` |
| `possible_prompt_injection` | `bool` |
| `rationale` | `str` (≤ 300 chars, must reference facts) |

### `RiskAssessment` (contract)
| Field | Type | Computed by |
|---|---|---|
| `sentiment` | `Sentiment` | model |
| `indicators` | `list[RiskIndicator]` | rules below plus the two model flags plus the phrase check |
| `risk_level` | `RiskLevel` | FR-018 |
| `teams` | `list[Team]` | FR-019 |
| `follow_up_business_days` | `int` | FR-020 |
| `follow_up_date` | `date` | FR-021 |
| `rationale` | `str` | model |

#### Indicator rules (FR-017, FR-017a)
| Indicator | Set when |
|---|---|
| `INJURY_REPORTED` | `injury_present == YES` |
| `HIT_AND_RUN_NO_POLICE_REPORT` | `um_uim_subtype == HIT_AND_RUN` and `police_report_mentioned != YES` |
| `CONTRADICTORY_STATEMENTS` | `contradictions` non-empty |
| `CRITICAL_INFO_MISSING` | `INCIDENT_DATE` or `LOCATION` in `missing_information` |
| `MIXED_INCIDENTS` | `incident_type == MIXED` |
| `LEGAL_REPRESENTATION_MENTIONED` | model flag |
| `POSSIBLE_PROMPT_INJECTION` | model flag **or** a phrase-list match on the protected narrative |

**Risk level:**
- `HIGH` if `LEGAL_REPRESENTATION_MENTIONED` or `POSSIBLE_PROMPT_INJECTION` is present, or there
  are ≥2 indicators.
- `MEDIUM` if there is exactly 1 indicator.
- `LOW` otherwise.
- Sentiment is never an input.

**Teams:**
- `CLAIMS_ADJUSTER` always.
- `+ CUSTOMER_RELATIONS` if sentiment ∈ {`DISTRESSED`, `ANGRY`}.
- `+ SPECIAL_REVIEW` if the legal-representation or injection indicator is present.

**Follow-up:**
- 1 business day if `INJURY_REPORTED`, or `injury_present == UNKNOWN` because of a contradiction,
  or `risk_level == HIGH`.
- Otherwise 2 business days.
- Privacy review: 3 business days.

---

## Reply and report

### `SummaryLlmOutput` (LLM output; checked by the R8 output validator)
| Field | Type | Notes |
|---|---|---|
| `opening_line` | `str` | an empathetic first sentence |
| `recorded_points` | `list[str]` | 1–5 plain-language bullets for "Here's what we recorded" |
| `narrative_summary` | `str` | 2–4 sentences for the internal report |

### `CustomerReply`
| Field | Type |
|---|---|
| `text` | `str`: the rendered sections of AC-4.1 (claim number, opening, recorded points, what happens next with the team role and date, optional safety line, optional MIXED line, optional "What we still need from you") |

### `InternalReport`
| Field | Type |
|---|---|
| `markdown` | `str`: FR-024 sections in fixed order, ending with the decision notice |

Customer-facing wording for each `MissingItem` (e.g., `POLICE_REPORT` → "Police report number")
and each `Team` role (e.g., `CLAIMS_ADJUSTER` → "a claims adjuster") lives in one mapping table in
the reporting module. `SPECIAL_REVIEW` has no customer wording (AC-4.3).

---

## Persistence and results

### `HistoryEntry`
| Field | Type |
|---|---|
| `at` | `datetime` |
| `event` | `str` enum-like literal: `"FILED"`, `"PRIVACY_REVIEW_OPENED"` |

### `ClaimRecord` (`data/claims/<claim_id>.json`)
| Field | Type | Rule |
|---|---|---|
| `claim_id` | `str` | `^CLM-\d{4}-\d{4}$` |
| `status` | `ClaimStatus` | initial-status priority (FR-029) |
| `filed_at` | `datetime` | |
| `assessment` | `ClaimAssessment \| None` | `None` for privacy review |
| `teams` | `list[Team]` | |
| `follow_up_date` | `date` | |
| `history` | `list[HistoryEntry]` | ≥1 entry |

**Initial status priority (FR-029):**
1. `ESCALATED` if `risk_level == HIGH` or privacy review.
2. Otherwise `AWAITING_INFORMATION` if `missing_information` is non-empty.
3. Otherwise `SUBMITTED`.

### `TaskResult` (what every UI receives)
| Field | Type |
|---|---|
| `processing_status` | `ProcessingStatus` |
| `claim_id` | `str \| None` |
| `customer_message` | `str` (a reply or a safe failure message; never technical) |
| `report_path` | `str \| None` |

### `EventLogEntry` (one JSON line in `logs/events.log`)
| Field | Type |
|---|---|
| `ts` | `datetime` |
| `claim_id` | `str \| None` |
| `step` | `PipelineStep` |
| `outcome` | `ProcessingStatus` |
| `duration_ms` | `int` |
| `error_category` | `str \| None` (the exception class name only) |

---

## Lifecycle (this phase)

```
            ┌─ privacy re-scan / final guard hit ─► ESCALATED (Privacy Review, minimal record)
submit ─────┤
            └─ processed ─► HIGH risk? ── yes ─► ESCALATED
                                 └─ no ─► missing info? ── yes ─► AWAITING_INFORMATION
                                                   └─ no ─► SUBMITTED
failures (model, validation, output) ─► no ClaimRecord; status-only report + event log only
```
