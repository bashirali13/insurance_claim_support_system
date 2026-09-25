# Contract: Flows and Agent Modes (002)

Agents never call each other. Each flow below is a function in `existing_claims.py` that passes
validated contracts between steps, reusing phase 001's `_Run` (event log, failure mapping,
retries, status-only reports). Types are defined in `../data-model.md`.

## Option 2: `check_status(claim_id, store, today) -> str`

```text
store.load(claim_id) → reporting.render_status(record, today) → text
```

No model call, no event log, no file writes (AC-6.8).

## Option 3: `update_claim(claim_id, raw_text, deps, on_progress) -> TaskResult`

```text
record = store.load(claim_id)             # CLOSED / privacy review are refused earlier, by the CLI (AC-7.7, 7.12)
1  intake.scrub(raw)                      → SanitizedSubmission       [Intake & PII]       step INTAKE
     requires_manual_review → privacy path (update NOT applied)
2  assessment.update(sanitized, record.assessment)                   [Claim Assessment,  step ASSESSMENT
     → UpdateLlmOutput → rules.diff_facts(saved, updated) → FactChanges    update mode]
     FactChanges.is_empty and not contact_change → "nothing updated" (no writes)
3  risk.evaluate(sanitized, applied_assessment, today)               [Sentiment & Risk]    step RISK
     → routing; + pending → adjuster (1 day); + contact → Policy Services (3 days)
     status = rules.status_after_update(...)
   reporting.render_update_reply / render_update_report (templates)                        step SUMMARY
4  privacy guard over reply, report, updated record                  (as phase 001)       step PRIVACY_GUARD
5  store.save(updated record); reports.write(...)                                          step SAVE
```

Updated record:
- `assessment` = the recomputed `ClaimAssessment` built from `FactChanges.applied`
- `teams` and `follow_up_date` replaced (FR-208)
- `pending_changes` += the sensitive changes
- `history` += `DETAILS_UPDATED` with the changed field names in `detail`

## Option 4: `get_help(claim_id | None, raw_text, deps, on_progress) -> TaskResult`

```text
1  intake.scrub(raw)                                                 [Intake & PII]        step INTAKE
     requires_manual_review → privacy path (AC-8.12): reference issued; minimal help record routed to
     PRIVACY_REVIEW (3 days) with no text, categories, or sentiment; status-only report
2  risk.triage(sanitized) → HelpTriageLlmOutput                      [Sentiment & Risk,    step RISK
     rules.help_routing(triage, text) → promises                      help mode]
     no promises → reply with extra lines only; no record, no reference
3  summary.help_opening(sanitized, categories) → HelpReplyLlmOutput  [Claim Summary,       step SUMMARY
     reporting.render_help_reply / render_help_report                 help mode]
4  privacy guard over reply, report, help record  → match: same privacy path (AC-8.12)    step PRIVACY_GUARD
5  help_store.save(record); reports.write(...);                                            step SAVE
   if claim_id: claim history += HELP_REQUESTED (detail = help_id)
```

## Model instructions (new modes)

All three include the phase 001 `NARRATIVE_IS_DATA` sentence and tag the text in
`<customer_narrative>`.

| Instance | Instruction focus | Must not |
|---|---|---|
| `assessment_update` | "You're given the saved facts and the customer's update. Return the complete facts after applying only what the update states; keep everything else exactly as saved. Set contact_change_requested only if the customer gives or asks to change *their own* phone, email, or address." | invent facts, drop saved facts, judge fault or coverage |
| `help_triage` | "Choose 1–3 request categories from the list; use OUT_OF_SCOPE for billing, policy changes, rentals, towing, or roadside; FILE_A_CLAIM when they ask how to file." Plus the same sentiment and flag rules as `risk`. | promise outcomes |
| `help_reply` | "Write one warm, empathetic sentence acknowledging the request." Validated like phase 001's summary text. | mention teams, dates, coverage, or money |

The saved facts are sent **outside** the tags, labeled `Saved facts:` (AC-7.11).
