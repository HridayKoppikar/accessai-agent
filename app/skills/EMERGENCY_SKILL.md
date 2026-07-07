# Emergency Skill

## Highest priority — override everything else

If the user says they have fallen, cannot get up, are bleeding, can't breathe,
need an ambulance, are in danger, or describe any other crisis, **call
`emergency_alert_for_user` immediately.** No hesitation, no polite preamble.

## Flow

1. **Call the tool NOW** — `emergency_alert_for_user(situation_description=<the user's exact words>)`.
   - Pass the user's own words as the situation_deletion.
   - Do NOT pause to ask clarifying questions first.
2. Relay the tool's emergency alert confirmation (alert ID, actions being taken,
   next steps) to the user verbatim.
3. Ask for their current location if possible.
4. Keep reassuring them while the alert propagates.

## Never

- Ask "are you sure this is an emergency?" — act first.
- Try to handle it with another tool — `emergency_alert_for_user` exists
  solely for this case.
- Narrate the process in detail — call the tool, relay the result.