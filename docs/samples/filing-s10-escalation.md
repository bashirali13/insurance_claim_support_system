# S10: hit-and-run with an injury and personal details (escalated, HIGH risk)

Captured from a real run of `uv run claim-support --load-samples` with `deepseek/deepseek-v4-flash-0731` on 2026-09-25, then reviewed. All details are fictional.

## Customer reply

```text
--------------------------------------------------
 Your claim number: CLM-2026-0008
--------------------------------------------------
I'm sorry to hear about this frightening experience, and I hope your neck feels better soon.
We're sorry to hear someone was hurt.

Here's what we recorded:
  • Customer was stopped at a red light on Main St when a pickup hit the car from behind
  • The pickup drove off after the collision
  • The rear bumper was crushed
  • Customer reports a sore neck
  • Incident occurred yesterday around 6pm

What happens next:
  • A claims adjuster will contact you by Monday, Sep 28.
  • If anyone's symptoms get worse, please seek medical care right away.

What we still need from you:
  • Police report number

Choose option 3 anytime to add these details.
--------------------------------------------------
```

## Staff report

# Claim Intake Report — CLM-2026-0008
- **Processing status:** COMPLETED
- **Task:** File a new claim
- **Filed:** 2026-09-25 14:29

## Summary
The customer was stopped at a red light on Main St yesterday around 6pm when a pickup struck the rear of their vehicle and left the scene. The collision caused damage to the rear bumper, and the customer reports neck soreness. The details have been recorded for the claims team's review.

## Incident
- **Type:** COLLISION
- **UM/UIM sub-type:** HIT_AND_RUN
- **When:** Yesterday around 6pm
- **Where:** Main St
- **Customer's words (protected):**
  > Yesterday around 6pm I was stopped at a red light on Main St when a pickup hit me from behind and drove off. My bumper is crushed and my neck is sore. You can reach me at [PHONE_1].
  > - [PERSON_1]

## Facts
- **Damage:** bumper
- **Injury present:** YES (customer side: YES, others: UNKNOWN)
- **Other party involved:** YES
- **Other property damaged:** UNKNOWN
- **Vehicle drivable:** UNKNOWN
- **Police report mentioned:** UNKNOWN
- Customer was stopped at a red light on Main St
- A pickup hit the customer's car from behind and drove off
- The customer's bumper was crushed
- The customer's neck is sore
- Incident occurred yesterday around 6pm

## Coverage Lines to Review
- COLLISION
- UM_UIM
- PIP_MEDPAY

## Missing Information
- Police report number

## Contradictions
None recorded.

## Sentiment and Risk
- **Sentiment:** CALM
- **Risk level:** HIGH
- **Indicators:** INJURY_REPORTED, HIT_AND_RUN_NO_POLICE_REPORT
- **Rationale:** The customer factually describes being stopped at a red light when a pickup hit them from behind and drove off, noting a crushed bumper and sore neck. The tone is neutral and straightforward with no emotional language.

## Routing and Follow-up
- **Teams:** CLAIMS_ADJUSTER
- **Follow up by:** 2026-09-28 (1 business day(s))

## Privacy
- **Personal information types removed:** PERSON, PHONE

---
> Supports intake and triage only. Not a coverage, fault, or claim decision.
