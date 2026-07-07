# Navigation Skill

## How to handle navigation requests

Navigation requests: "navigate to the nearest pharmacy", "how do I get to the
hospital", "give me directions to the park", etc.

## Flow

1. Acknowledge the destination and the mobility profile you've inferred
   (wheelchair / cane / visual_impairment / general) in one short sentence.
2. Call `navigation_guidance_for_user(destination=<place>, mobility_profile=<profile>)`.
   - If the user shared a precise location, pass `start_location_lat` and
     `start_location_lng`.
   - If they didn't, call it without them — the skill will return a demo route
     with a clear note that a precise location is needed for real directions.
3. The skill returns turn-by-turn instructions formatted for reading aloud, plus
   accessibility notes for the mobility profile. Relay it to the user directly.

## Mobility profiles

- `wheelchair` — the route prioritises ramps, curb cuts, avoids stairs and
  steep inclines (>5%).
- `cane` — highlights ground-level obstacles and uneven pavement.
- `visual_impairment` — audio-described turns, notes traffic-signal locations.
- `general` — standard accessible routing.

Infer the profile from the user's words ("wheelchair accessible", "with my cane",
"I'm blind") and default to `general` when unclear.

## Critical rule

Never throw if directions are unavailable. The skill always returns a string
(either real directions or a clearly-labeled demo route). Just pass that string
to the user. If it says a precise location is needed, ask the user for their
location and offer to use the browser's geolocation.
