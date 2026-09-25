# Contract: Terminal Interface — Options 2–4 (002)

This extends `specs/001-file-a-claim/contracts/cli.md`. The menu, the multi-line input rules, and
the phase 001 failure messages are unchanged. The "coming soon" replies are removed (FR-220).

## Launch

```text
uv run claim-support                 # as before
uv run claim-support --load-samples  # copy missing sample claims into data/claims/, then show the menu
```

With `--load-samples`, before the menu the app prints `Loaded N sample claims.` (N may be 0).

## Claim-number prompt (shared by options 2, 3, 4)

| Option | Prompt |
|---|---|
| 2, 3 | `Enter your claim number (format CLM-YYYY-NNNN): ` |
| 4 | `Enter your claim number (or press Enter if you don't have one): ` |

| Entry | Options 2 and 3 | Option 4 |
|---|---|---|
| empty | back to the menu | continue without a claim |
| malformed | `Claim numbers look like CLM-YYYY-NNNN. Please try again.` → re-prompt | same message + `Press Enter to continue without one.` → re-prompt |
| well-formed, not found | `We couldn't find that claim number. Please check it and try again.` → re-prompt | same message + `Press Enter to continue without one.` → re-prompt |

## Option 2: status reply (AC-6.1 to AC-6.7)

```text
Claim CLM-2026-0005: Collision (filed Sep 23, 2026)
  Status:      With a specialist team for priority review
  Last update: Sep 23, 2026 - Claim filed
  Still needed:
    • Police report number
  Waiting for an adjuster to confirm:
    • injuries to you or your passengers
  Next step:   A claims adjuster will contact you by Friday, Sep 25.
```

- **Privacy review claims:** the incident type, "Still needed", and "Waiting for…" lines are
  omitted.
- **Omitted when empty:** "Still needed" and "Waiting for an adjuster to confirm".
- **"Next step":** shown only when the follow-up date is today or later and the claim isn't
  `CLOSED`. It names the first customer-visible team (`TEAM_ROLE`), and it's omitted if there's no
  such team.
- **Last-update wording:** `FILED` → "Claim filed"; `DETAILS_UPDATED` → "Details added by you";
  `HELP_REQUESTED` → "Help request received"; `PRIVACY_REVIEW_OPENED` → "Specialist review
  started".

## Option 3: add or correct details

1. Claim-number prompt.
2. `CLOSED`:
   `This claim is closed. If you need help with it, choose option 4 (Get help with my claim).`
   Then back to the menu.
3. Privacy review (no assessment):
   `This claim is with a specialist for a privacy review. They'll contact you by <date>, and you
   can share any updates with them then.` ("by <date>" becomes "soon" if the date is past.)
   Then back to the menu.
4. Prompt: `What would you like to add or correct?` followed by the phase 001 multi-line rules.
5. Progress:
   ```text
     [1/3] Protecting your personal information ...... done
     [2/3] Comparing with your existing claim ........ done
     [3/3] Updating your claim ....................... done
   ```
6. Reply:

```text
Thanks, your claim CLM-2026-0005 is updated.
  • Added: police report
  • Corrected: when it happened (yesterday around 6pm → around 7pm)
  • An adjuster will confirm this change with you by Friday, Sep 25:
    injuries to you or your passengers
  • Our Policy Services team will confirm your new contact details with you by Tuesday, Sep 29.
    We didn't store them here.

What happens next:
  • A claims adjuster will contact you by Friday, Sep 25.

Still needed:
  • Description of the other vehicle
```

- The Added and Corrected lines use the field wording in `data-model.md`. Lists show only their
  new items (e.g., "Added: damage (rear door)").
- "Still needed" is omitted when empty.
- **No change (AC-7.6):** `We didn't find any new or changed details. Nothing was updated.`
- **Privacy (AC-7.10):** `We've received your update. A specialist will review it by <date> before
  it's added to your claim.`
- **Failures:** the phase 001 messages.

## Option 4: get help

1. Claim-number prompt (optional).
2. Prompt: `How can we help?` followed by the phase 001 multi-line rules.
3. Progress:
   ```text
     [1/3] Protecting your personal information ...... done
     [2/3] Understanding your request ................ done
     [3/3] Routing to the right team ................. done
   ```
4. Reply (routed):

```text
<opening_line — model>
  • Our Customer Relations team will contact you by Monday, Sep 28.
  • A claims adjuster will contact you by Monday, Sep 28.
Reference: HELP-2026-0001
```

**Team wording:**

| Team | Wording |
|---|---|
| `CLAIMS_ADJUSTER` | A claims adjuster |
| `CUSTOMER_RELATIONS` | Our Customer Relations team |
| `POLICY_SERVICES` | Our Policy Services team |
| `SPECIAL_REVIEW` | never shown |

**Extra lines, appended when the request includes them:**
- `FILE_A_CLAIM`: `To file a new claim, choose option 1 from the menu.`
- `OUT_OF_SCOPE`: `I'm sorry, I can only help with claims here. For billing, policy changes,
  rentals, or roadside help, please call Northstar Auto Insurance at the number on your insurance
  card.`

**When nothing is routed:** only the extra line(s) are shown, with no opening line and no
reference.
