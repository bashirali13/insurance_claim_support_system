# Contract: Terminal Interface (001)

The only user-facing interface in this phase. Text shown to the customer is fixed here so the
acceptance tests can assert it exactly. Model-written text is limited to the opening line and
recorded points (see `agents.md`).

## Launch

```text
uv run claim-support
```

- Exit code `0` when the customer chooses Exit.
- Exit code `1` when configuration is missing (AC-5.7). In that case this message is printed and
  the menu is never shown:

```text
Setup needed: OPENROUTER_API_KEY and MODEL_NAME must be set in .env (see .env.example).
```

## Menu (AC-5.1)

```text
==================================================
 Northstar Auto Insurance: Claim Support
==================================================
 Your information is protected. Personal details
 like phone numbers and addresses are removed
 before your claim is processed.

 1. File a new claim
 2. Check my claim status
 3. Add or correct details on my claim
 4. Get help with my claim
 5. Exit

Choose an option (1-5):
```

| Input | Response |
|---|---|
| `1` | the filing flow |
| `2`, `3`, `4` | `This option is coming soon.`, then the menu |
| `5` | `Thank you for contacting Northstar Auto Insurance. Goodbye.`, then exit 0 |
| anything else | `Please choose a number from 1 to 5.`, then the menu |

## Filing flow

**Prompt (AC-5.2):**

```text
Tell us what happened, in your own words. Include when and where it
happened, what was damaged, and whether anyone was hurt.
Press Enter on an empty line when you're done.
>
```

Every non-empty line is captured, and an empty line ends the input. The lines are joined with `\n`.

| Condition | Message | Then |
|---|---|---|
| nothing entered / whitespace only (AC-5.5) | `Please describe what happened, then press Enter on an empty line.` | re-prompt |
| over 5,000 characters (AC-5.6) | `That's longer than we can accept here (limit 5,000 characters). Please shorten it.` | re-prompt |

**Progress (AC-5.3):** printed through the `on_progress` callback, in order:

```text
  [1/4] Protecting your personal information ...... done
  [2/4] Reviewing what happened ................... done
  [3/4] Checking if a specialist should help ...... done
  [4/4] Preparing your summary .................... done
```

**Success reply (AC-4.1):** section order is fixed. Bracketed items are filled in by code, except
where marked *model*.

```text
--------------------------------------------------
 Your claim number: <CLM-YYYY-NNNN>
--------------------------------------------------
<opening_line — model>

Here's what we recorded:
  • <recorded_point — model>            (1–5 bullets)

What happens next:
  • <Team role> will contact you by <Weekday, Mon D>.     (one bullet per customer-visible team)
  • If your pain gets worse, please seek medical care right away.   (only when injury_present = YES)
  • You described more than one incident. An adjuster will help separate them.   (only when MIXED)

What we still need from you:            (section omitted when nothing is missing)
  • <customer wording for each MissingItem>

Choose option 3 anytime to add these details.   (only when something is missing)
--------------------------------------------------
```

Team roles as the customer sees them:

| Team | Wording |
|---|---|
| `CLAIMS_ADJUSTER` | `A claims adjuster` |
| `CUSTOMER_RELATIONS` | `Our Customer Relations team` |
| `SPECIAL_REVIEW` | never shown |

## Failure messages (AC-5.8 – AC-5.11)

| Status | Message |
|---|---|
| `MANUAL_REVIEW_REQUIRED` | `Your claim number: <id>` + `We've received your submission. A specialist will review it by <Weekday, Mon D> before processing.` |
| `FAILED_MODEL_ERROR`, `FAILED_VALIDATION` | `We couldn't finish processing right now. Please try again shortly.` |
| `FAILED_OUTPUT` | `We couldn't save your request. Please try again.` |

No failure message contains exception text, model names, file paths, or risk information.
