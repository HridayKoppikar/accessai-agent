# Health & Allergy Skill

## How to handle health-related requests

Health requests include food safety ("Is this safe for peanut allergies?"),
medication questions ("Can I eat grapefruit with my statin?"), and meal planning
("Suggest a meal with my allergies in mind").

## Two-step flow when an image is attached

When the user uploads a food-label image AND asks a safety question, do this in
order:

1. **Describe the image yourself** (briefly, 1–2 sentences) so the user knows
   you've seen it — e.g. "I can see a packaged food label."
2. **Read the label text** by calling `analyze_image_for_user(image_data=<attached image>, task='ocr')`.
3. **Then** call `health_check_for_user` with:
   - `user_query` = the user's original question **plus** the OCR'd ingredient text
     (e.g. "Is this safe for nut allergies? Ingredients: wheat flour, sugar,
     almonds, soy lecithin.")
   - `allergies` = the user's known allergies if mentioned.
4. Reply with the result the tool returns — never editorialise over the safety
   verdict. The tool states the **risk level (HIGH / MODERATE / LOW)** explicitly.

## Text-only requests

When there is no image, just describe briefly what you understand the user is
asking, then call `health_check_for_user(user_query=<their question>, ...)` with
any allergies / medications they've mentioned.

## Always relay the risk level

The health skill output includes an explicit `Risk level: HIGH | MODERATE | LOW`
line. Always pass it through to the user — it is the single most important piece
of information for an allergic user. Do not soften "HIGH" to "maybe avoid" — say
it plainly: **AVOID — contains an allergen you are allergic to.**

## Critical rule

Never put a description of the food image inside the `health_check_for_user`
argument. The argument is the structured text query + allergy lists only.
Describe the image in your own reply text.
