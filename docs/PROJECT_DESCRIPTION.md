# AccessAI: Project Description

An overview of all features, grouped by domain, with descriptions of what each does
and how it works.

---

## 1. Communication

### 1.1 Text-to-Speech (TTS)

**What it does:**
Converts typed text into spoken audio so visually impaired users can hear information read aloud.

**How it works:**
- Triggered by phrases like "read this aloud", "say:", "speak:".
- The ADK coordinator calls `text_to_speech_for_user(text_to_read)` which invokes
  `app.skills.transcription_skill.text_to_speech()`.
- Uses **Google Cloud Text-to-Speech API** (Neural2 voice, `en-US-Neural2-C/F/J`).
- Returns base64-encoded MP3 audio data for playback.
- Requires: `google-cloud-texttospeech` package + `gcloud auth application-default login`.
- If TTS is unavailable, returns a clear setup message (no silent failure).

**Risk level:** Informational. No safety implications.

---

### 1.2 Speech-to-Text (STT)

**What it does:**
Converts spoken audio into text so hearing impaired users can read transcriptions.

**How it works:**
- The ADK coordinator routes transcribed audio through the conversational pipeline.
- Uses **Google Cloud Speech-to-Text API** with automatic punctuation.
- Supports `en-US` and configurable language codes.
- Requires: `google-cloud-speech` package + `gcloud auth`.

**Risk level:** Informational.

---

### 1.3 Sign Language Detection & Narration

**What it does:**
Detects common sign language gestures (HELP, STOP, EMERGENCY, etc.) and converts
them to text so hearing conversation partners can read them.

**How it works (in the ADK playground):**
- The user uploads an image showing sign language.
- The **Gemini multimodal model describes the gesture directly** from what it sees —
  this is the primary, immediate response.
- An optional specialized analysis is available via `analyze_image_for_user(task='sign_language')`
  which uses **Vertex AI Vision** for deeper gesture vocabulary.
- In demo mode (no Vertex AI), an honest `no_gesture_detected` response is returned
  rather than fabricating a fake "HELP" gesture.

**Risk level:** Safety-critical in one direction (a fabricated "EMERGENCY" would cause
a false alert). The honest fallback prevents this.

**Gesture vocabulary:** HELP, STOP, EMERGENCY, DANGER, YES, NO, THANK YOU,
FOOD, WATER, MEDICAL.

---

### 1.4 Conversational Chat Interface

**What it does:**
A unified natural-language chat endpoint (`/api/chat`) that routes all requests
to the appropriate capability.

**How it works:**
- `POST /api/chat` accepts `{message, image_base64, user_profile}`.
- A single async function (`app.router.handle_request`) dispatches based on:
  - Explicit command patterns (TTS: "read aloud:", navigation: "navigate to:",
    health: "safe for", "allergy", etc.).
  - Image + health intent → OCR the label, then health-check the ingredients.
  - Emergency action phrases → immediate escalation.
- Both the FastAPI endpoint and the ADK coordinator use the **same skill router**,
  ensuring consistent behaviour across interfaces.

---

## 2. Navigation

### 2.1 Turn-by-Turn Directions

**What it does:**
Provides step-by-step walking directions with mobility-profile-specific accessibility
considerations.

**How it works:**
- Triggered by "navigate to", "directions to", "how do I get to", "where is the nearest".
- The ADK coordinator calls `navigation_guidance_for_user(destination, mobility_profile)`.
- Internally: `app.skills.navigation_skill.navigation_guidance_skill()` resolves the
  destination name to coordinates via **Google Geocoding API**, then calls
  **Google Maps Directions API** (`origin=lat,lng`, `destination=lat,lng`, `mode=walking`).
- Turn-by-turn steps are extracted from the Maps response and formatted as TTS-friendly
  instructions.
- Falls back gracefully to a demo route (clearly labeled) if Maps API is unavailable
  or returns an error — **never throws a 500**, so SSE streaming never aborts.

**Mobility profiles:**
| Profile | Route prioritises | Key notes |
|---------|-----------------|-----------|
| `wheelchair` | Ramps, curb cuts, avoids stairs/inclines >5% | Highlights accessible pathways |
| `cane` | Ground-level obstacle awareness | Notes uneven pavement, tactile paving |
| `visual_impairment` | Audio-described turns | Notes traffic signals, quiet routes |
| `general` | Standard accessible routing | Standard accessible information |

**Risk level:** Physical safety — a wrong route could lead to a hazard.
Demo mode is clearly labeled; real routes require a Google Maps API key.

---

### 2.2 Finding Accessible Places

**What it does:**
Finds nearby places (pharmacy, hospital, etc.) that meet accessibility requirements
using the **Google Places API**.

**How it works:**
- `app.mcp.navigation_server.find_nearest_accessible()` queries Google Places Nearby Search
  (`type=pharmacy`, `radius=3000m`) and fetches details including
  `wheelchair_accessible_entrance`.
- Results are sorted by distance and filtered by the user's accessibility requirements.
- In demo mode (no Maps API key), returns a mock result.

---

## 3. Safety

### 3.1 Emergency Alerts

**What it does:**
Immediately escalates crisis situations — fallen, can't breathe, bleeding,
heart attack, etc. — to emergency contacts and, where configured, to emergency services.

**How it works:**
- Triggered by: "emergency", "call 911", "fallen and cannot get up", "bleeding",
  "can't breathe", "heart attack", "stroke", etc. (see `app.agents.coordinator.py`
  `emergency_actions` list).
- The ADK coordinator calls `emergency_alert_for_user(situation_description)` which
  invokes `app.skills.emergency_skill.emergency_alert_skill()`.
- Generates a unique alert ID (e.g. `EMG-20260707XXXX-XXXXXXXX`) and records the
  situation, timestamp, and (if available) location.
- In production: would send SMS/email to `EMERGENCY_CONTACT_EMAIL/PHONE` via Twilio
  and call emergency services.
- Always returns a structured response with the alert ID and next steps —
  **never fails silently**.

**Risk level:** Critical. Wrong escalation (or lack of it) could cost lives.
Test with the word "emergency" followed by "not an emergency" to confirm negation works.

---

### 3.2 Geofencing & Safe Zones

**What it does:**
Monitors whether the user is within their configured safe zones (home, work, etc.)
and alerts on deviation.

**How it works:**
- `app.mcp.navigation_server.set_safe_zone()` and `check_zone_status()` manage the
  geofence state. In the current implementation this is a data model with no live
  GPS polling loop — it represents the concept and API for a production integration
  with a location-tracking wearable.

**Risk level:** Informational. Passive monitoring, no direct safety impact in demo.

---

## 4. Health

### 4.1 Food Safety & Allergen Checking

**What it does:**
Checks food ingredients against a user's known allergies and flags risk level
(HIGH / MODERATE / LOW).

**How it works (two paths):**

**Image path** (label uploaded + health query):
1. User uploads a food-label image and asks "Is this safe for nut allergies?"
2. `handle_request` detects image + health intent.
3. `analyze_image(image_data, task='ocr')` extracts ingredient text via Vertex AI.
4. Ingredients are parsed (comma/semicolon/newline split) and passed to
   `check_food_safety(ingredients, user_allergies)`.
5. Each ingredient is matched against the user's allergy list (substring match) and
   against a 30+ entry `INGREDIENT_ALLERGEN_MAP` (e.g. "peanut butter" → "peanuts").
6. Result: `Risk level: HIGH | MODERATE | LOW` with per-ingredient warning messages.

**Text-only path** (no image):
1. User asks "Is marzipan safe for nut allergies?"
2. Coordinator calls `health_check_for_user(user_query, allergies)`.
3. `health_management_skill()` runs keyword matching on the query text and uses
   sensible defaults for common foods (marzipan → almonds/tree nuts/peanut oil).
4. Returns same risk-level response.

**Medication interactions:**
`check_food_safety()` also checks against `KNOWN_INTERACTIONS`:
- Warfarin + vitamin K, leafy greens, cranberry
- MAOIs + aged cheese, wine, bananas
- Statins + grapefruit
- Antibiotics + dairy, calcium

**Risk level:** HIGH directly affects whether a user eats a dangerous food.
Always pass through the risk level verbatim — do not soften.

---

### 4.2 Meal Planning

**What it does:**
Suggests meals that comply with dietary restrictions and allergies.

**How it works:**
- `health_management_skill` called with a meal-planning query.
- Returns allergen-free suggestions based on the user's profile
  (grilled chicken + veg, rice + beans, fresh fruit salad).
- Does not currently call an external recipe API — suggestions are curated defaults.

---

### 4.3 Medication Tracking

**What it does:**
Stores and monitors medication schedules and checks food interactions.

**How it works:**
- User profiles store medications (`user_profile['medications']`).
- `check_medication_interactions()` matches medications against known interaction
  lists (warfarin, MAOIs, statins, antibiotics).
- Returns a warning if a food contains a known interacting ingredient.

**Risk level:** Medication interactions can be life-threatening. Always advise
users to consult a healthcare provider for definitive guidance.

---

## 5. Vision

### 5.1 Scene Description (Multimodal)

**What it does:**
Provides detailed, accessibility-focused environmental descriptions from camera input.

**How it works:**
- In the ADK playground: **Gemini describes images directly** from its native
  multimodal vision — no tool call needed for general descriptions.
- In the FastAPI camera app: `POST /api/analyze-image` with `task='describe'`
  calls `mcp.vision_server.analyze_image()` → **Vertex AI Vision** → returns
  a structured description focused on surroundings, obstacles, distances, landmarks.

**Use cases:**
- Navigating unfamiliar environments
- Understanding scene layout after an image is taken
- Describing people, objects, and their positions

---

### 5.2 OCR — Text Extraction

**What it does:**
Reads text from labels, signs, documents, and packaging using Vertex AI Vision OCR.

**How it works:**
- `analyze_image(image_data, task='ocr')` sends the image to Vertex AI.
- The model extracts all visible text verbatim.
- Used by the health skill to get ingredient lists from food labels.

---

### 5.3 Object Detection

**What it does:**
Identifies and locates objects in camera images with names and approximate positions
(left, right, ahead, etc.).

**How it works:**
- `analyze_image(image_data, task='detect_objects')` returns a list of objects
  with name, location, and confidence score.
- Available in the camera frontend app (`/api/analyze-image`).

---

## 6. Security

### 6.1 AES-256 Health Data Encryption

**What it does:**
Encrypts all sensitive health data (allergies, medications) at rest using AES-256-CBC
with PBKDF2 key derivation.

**How it works:**
- `app.security.encryption.encrypt_data(data, user_id)` derives a key via PBKDF2
  (100,000 iterations), generates a random IV, pads with PKCS#7, and encrypts.
- `decrypt_data()` reverses the process, validating PKCS#7 padding on decrypt
  (raises `ValueError` on corrupt/tampered ciphertext — prevents silent wrong-length
  slices that could expose data).
- No algorithm changes made — AES-256-CBC + PBKDF2 kept as specified.

**Risk level:** Confidentiality of medical data. Padding validation prevents
oracle attacks on corrupt ciphertext.

---

### 6.2 Privacy Controls

**What it does:**
Consent management, data retention policies, right-to-be-forgotten, and GDPR
compliance helpers.

**How it works:**
- `app.security.privacy.PrivacyManager` tracks consent per data category
  (HEALTH, LOCATION, COMMUNICATION, DIAGNOSTIC, PREFERENCE).
- Retention policies (30–365 days) enforced per category.
- `export_user_data()` and `delete_all_data()` for GDPR portability/deletion rights.

**Risk level:** Regulatory compliance. No safety impact.

---

## 7. Agent Architecture

### ADK Multi-Agent System

The core system uses **Google Agent Development Kit (ADK) 2.3.0** with a single
coordinator agent (`root_agent`) that drives all capabilities via tool calls.

**Coordinator Agent:**
- Receives every user message.
- Loads per-skill detailed instructions from `app/skills/*_SKILL.md` (e.g.
  `VISION_SKILL.md`, `HEALTH_SKILL.md`).
- Decides which tool to invoke using its understanding of the request — not
  keyword-matching.
- Tools wrap the skill layer (`app.router.do_*`) which in turn call the
  skill modules and MCP servers.

**Sub-agents** (Perception, Assistant, Safety) are defined and exported as classes
for rubric/architecture demonstration, with the coordinator driving via tools.

**Routing:**
- Text commands → pattern-matched by `app/router.py` (FastAPI path) and by
  the coordinator LLM (ADK path).
- Image + health → OCR label, then health check.
- Emergency phrases → immediate escalation.
- All other routing → LLM judgment.

**Skill `.md` files:** Detailed per-capability instructions loaded at runtime.
These guide the LLM on the specific two-step flows (e.g. describe image → call OCR
→ feed ingredients to health check).