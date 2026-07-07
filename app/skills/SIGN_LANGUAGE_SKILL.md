# Sign Language Detection Skill

## How to handle sign-language requests

When the user uploads an image showing hand signs and asks "what is he signing?"
or "detect this gesture":

## Flow

1. **Describe the image yourself first.** You are a multimodal model — you can
   see the hand shape, finger positions, and body language in the attached image.
   Describe what you see and give your best interpretation of the gesture
   (e.g. "I can see an open hand facing outward, which looks like a STOP sign.")
   This is the user's immediate answer.

2. **Do NOT call `sign_language_detection_for_user` for an attached image.**
   That tool is for programmatic batch frame analysis via the API and will cause
   a malformed function call if you try to pass an attached image to it. Your own
   multimodal description is the user's answer.

3. If the user wants *further* specialised analysis, you MAY call
   `analyze_image_for_user(image_data=<attached image>, task='sign_language')`
   as a supplementary step. But always give your own answer first.

## Gesture vocabulary I should recognise

- **HELP** — flat hand or cupped hand reaching out
- **STOP** — open palm facing forward
- **EMERGENCY** — waving hands urgently
- **DANGER** — hands crossed or pointing to threat
- **YES** — nodding or thumbs up
- **NO** — shaking head or thumbs down
- **THANK YOU** — hand from chin outward, or nodding with hand over heart
- **FOOD** — hand to mouth
- **WATER** — cupped hand to mouth, or drinking motion
- **MEDICAL** — hand forming a cross, or pointing to injury

## Critical rule

Never embed an image description inside a tool-call argument. Describe the
gesture in your own text reply, and only pass the raw image data to a tool
if you call one.