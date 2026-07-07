"""
AccessAI Unified Skill Router

Single source of truth for calling skills and formatting user-facing responses.
Used by BOTH the ADK agent path (app/agent.py → coordinator tools) and the FastAPI
path (app/main.py → /api/chat).  No keyword-classification lists — the LLM
(agent) or the caller (FastAPI) decides which handler to invoke; the router simply
executes.

Exports:
  handle_request(message, image, profile) -> dict      # full-turn router
  do_vision(image, task, user_input)                    # thin skill helpers
  do_tts(text_to_read)
  do_navigation(destination, mobility_profile, start_location)
  do_health(user_query, user_profile, ingredient_list)
  do_sign_language(frames)
  do_emergency(user_input, user_profile)
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from google.adk.tools import ToolContext
from google.genai import types as genai_types
import base64
# ── Thin async helpers (one per skill) ────────────────────────────────────────
# Each is a ~3-line wrapper that calls the real skill and returns the response
# string the agent / chat endpoint displays to the user.


async def do_vision(
    image_data: str,
    task: str = "describe",
    user_input: str = "",
) -> Dict[str, Any]:
    """Analyze an image: describe scene, OCR text, detect objects, or detect sign language.

    Args:
        image_data: Base64-encoded image.
        task: One of "describe", "ocr", "detect_objects", "sign_language".
        user_input: Natural-language request for context.
    """
    from app.mcp.vision_server import analyze_image

    result = await analyze_image(image_data, task=task)

    if "error" in result and not result.get("description") and not result.get("text") and not result.get("objects"):
        return {
            "type": "vision",
            "task": task,
            "response": (
                "👁️ IMAGE ANALYSIS\n\n"
                f"Status: Vision AI not available.\n"
                f"Reason: {result['error']}\n\n"
                f"{result.get('suggestion', 'Configure GOOGLE_CLOUD_PROJECT and authenticate with gcloud.')}"
            ),
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }

    # Build the human-friendly response
    if task == "describe":
        desc = result.get("description", "")
        return {
            "type": "vision",
            "task": task,
            "response": f"👁️ SCENE DESCRIPTION\n\n{desc}",
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }
    elif task == "ocr":
        text = result.get("text", "") or ""
        return {
            "type": "ocr",
            "task": task,
            "response": f"📝 EXTRACTED TEXT\n\n{text}",
            "extracted_text": text,
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }
    elif task == "detect_objects":
        objects = result.get("objects", [])
        if not objects:
            response = "🔍 OBJECT DETECTION\n\nNo objects detected."
        else:
            lines = [f"  • {obj.get('name', 'unknown')} — {obj.get('location', 'unknown')}" for obj in objects]
            response = f"🔍 OBJECT DETECTION ({len(objects)} objects)\n\n" + "\n".join(lines)
        return {
            "type": "vision",
            "task": task,
            "response": response,
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }
    elif task == "sign_language":
        analysis = result.get("analysis", "")
        return {
            "type": "sign_language",
            "task": task,
            "response": f"👐 SIGN LANGUAGE ANALYSIS\n\n{analysis}",
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }
    else:
        return {
            "type": "vision",
            "task": task,
            "response": f"👁️ VISION RESULT\n\n{result}",
            "analysis_result": result,
            "timestamp": datetime.now().isoformat(),
        }

async def do_tts(text_to_read: str, tool_context: ToolContext) -> Dict[str, Any]:
    from app.skills.transcription_skill import text_to_speech

    tts_result = await text_to_speech(text_to_read)

    if tts_result.get("status") not in ("success",):
        return {
            "type": "tts",
            "response": (
                "🔊 TEXT-TO-SPEECH\n\n"
                f"Status: TTS not available.\n"
                f"{tts_result.get('suggestion', 'Configure Google Cloud TTS.')}"
            ),
        }

    audio_bytes = base64.b64decode(tts_result["audio_data"])
    audio_part = genai_types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")

    filename = f"tts_output_{datetime.now().timestamp()}.mp3"
    version = await tool_context.save_artifact(filename, audio_part)

    return {
        "type": "tts",
        "response": f"🔊 Audio generated and saved as artifact '{filename}' (version {version}). Playable in the ADK dev UI's Artifacts panel.",
        "artifact_filename": filename,
    }
"""
async def do_tts(text_to_read: str) -> Dict[str, Any]:
    ""Convert text to speech audio (for visually-impaired users).

    Args:
        text_to_read: The text to read aloud.
    ""
    from app.skills.transcription_skill import text_to_speech, generate_audio_narration

    tts_result = await text_to_speech(text_to_read)

    if tts_result.get("status") in ("unavailable", "client_error", "error"):
        return {
            "type": "tts",
            "original_text": text_to_read,
            "response": (
                "🔊 TEXT-TO-SPEECH\n\n"
                f"Text: \"{text_to_read}\"\n\n"
                f"Status: TTS not available.\n"
                f"{tts_result.get('suggestion', 'Configure Google Cloud Text-to-Speech to enable audio output.')}"
            ),
            "audio_data": None,
            "timestamp": datetime.now().isoformat(),
        }

    return {
        "type": "tts",
        "original_text": text_to_read,
        "response": (
            "🔊 TEXT-TO-SPEECH GENERATED\n\n"
            f"Text: \"{text_to_read}\"\n\n"
            f"Status: {tts_result.get('status', 'success')}\n\n"
            "Audio data is ready for playback through your device."
        ),
        "audio_data": tts_result.get("audio_data"),
        "timestamp": datetime.now().isoformat(),
    }
"""

async def do_navigation(
    destination: str,
    mobility_profile: str = "general",
    start_location: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Get turn-by-turn navigation with accessibility considerations.

    Args:
        destination: Name or address of the destination.
        mobility_profile: One of "wheelchair", "cane", "visual_impairment", "general".
        start_location: Optional {lat, lng} dict; if None, a generic start is used.
    """
    from app.skills.navigation_skill import navigation_guidance_skill

    guidance = await navigation_guidance_skill(
        destination=destination,
        mobility_profile=mobility_profile,
        start_location=start_location,
    )

    return {
        "type": "navigation",
        "destination": destination,
        "response": guidance,
        "timestamp": datetime.now().isoformat(),
    }


async def do_health(
    user_query: str,
    user_profile: Optional[Dict[str, Any]] = None,
    ingredient_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Handle health-related queries: food safety, medications, meal planning.

    Args:
        user_query: The user's health question (e.g. "Is marzipan safe for nut allergies?").
        user_profile: Dict with optional keys allergies[], medications[], dietary_restrictions[].
        ingredient_list: Optional list of OCR'd ingredients (from a label) — takes precedence
                         over the keyword-guess inside the health skill.
    """
    from app.skills.health_skill import health_management_skill, check_food_safety

    delta = {}
    if ingredient_list is not None:
        # Pass the OCR-derived ingredients so the skill doesn't fabricate defaults.
        delta["_ocr_ingredients"] = ingredient_list

    profile = {**(user_profile or {}), **delta}
    result = await health_management_skill(user_query, profile)

    return {
        "type": "health",
        "response": result,
        "timestamp": datetime.now().isoformat(),
    }


async def do_sign_language(frames: Any) -> Dict[str, Any]:
    """Detect sign-language gestures from video frames.

    Args:
        frames: A single base64 frame or a list of frames.
    """
    from app.skills.transcription_skill import sign_language_narrator_skill

    if isinstance(frames, str):
        frames_data = [frames]
    else:
        frames_data = list(frames)[:5]

    result = await sign_language_narrator_skill(frames_data)

    primary = result.get("primary_gesture", "unknown")
    urgency = result.get("urgency", "low")
    action = result.get("recommended_action", "none")

    status_line = "success" if result.get("status") == "success" else "demo_mode (Vertex AI not configured)"

    return {
        "type": "sign_language",
        "response": (
            "👐 SIGN LANGUAGE DETECTION\n\n"
            f"Status: {status_line}\n"
            f"Primary gesture: {primary.upper()}\n"
            f"Urgency: {urgency}\n"
            f"Recommended action: {action}\n\n"
            f"{result.get('message', 'Gesture detected.')}"
        ),
        "detection_result": result,
        "timestamp": datetime.now().isoformat(),
    }


async def do_emergency(
    user_input: str,
    user_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle an emergency situation — notify contacts, record details.

    Args:
        user_input: Description of the emergency.
        user_profile: Optional user profile with emergency contacts, location, medical info.
    """
    from app.skills.emergency_skill import emergency_alert_skill, contact_emergency_services

    response = await emergency_alert_skill(user_input, location_available=True)

    return {
        "type": "emergency",
        "priority": "critical",
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }


# ── Full-turn handler ─────────────────────────────────────────────────────────
# Used directly by main.py's /api/chat endpoint.  The LLM-based ADK agent uses
# the individual do_* tools above so it can compose them (e.g. OCR a label THEN
# run do_health with the extracted ingredients).


async def handle_request(
    message: str,
    image_base64: Optional[str] = None,
    user_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process a user request into a structured {type, response, ...} dict.

    The QoS and security safety-net (not a keyword router — the LLM decides intent):
    - If an image is provided AND the message is a simple description request,
      return vision analysis.
    - If an image is provided along with a health/food query, OCR the label and
      pass ingredients to do_health so the README's "read label → check allergies"
      pipeline actually works end-to-end.
    - If the message contains a recognized *emergency action* phrase, escalate.

    All other routing is done by the caller (ADK agent LLM picks the right do_*
    tool; FastAPI callers pass explicit intent via the message+image combination).
    """
    import re

    if user_profile is None:
        user_profile = {}

    input_lower = message.lower().strip()

    # ── Fast safety-net: emergency action phrases that MUST escalate ──
    emergency_actions = [
        "fallen", "cannot get up", "can't get up", "call 911", "ambulance",
        "heart attack", "stroke", "bleeding", "can't breathe", "cannot breathe",
        "car accident", "house fire", "attacked", "unconscious", "fainted",
    ]
    negations = [
        "not an emergency", "no emergency", "isn't an emergency",
        "wasn't an emergency", "this is not an emergency", "it's not an emergency",
    ]
    # Negations veto the safety-net
    has_negation = any(n in input_lower for n in negations)
    if not has_negation and any(act in input_lower for act in emergency_actions):
        return await do_emergency(message, user_profile)

    # ── Explicit text commands (no keyword guessing) ──
    # These mirror the discrete actions an LLM calls as tools, so the FastAPI
    # /api/chat endpoint behaves correctly when a user types a plain command
    # (the frontend chat box can't run the ADK agent itself).
    # These are *action triggers*, not the brittle intent-classifier from before.

    # TTS: "read this aloud: <text>" / "say: <text>" / "read aloud <text>"
    tts_patterns = [
        (r"read (?:this|that|it) (?:aloud|out loud)[:\s]+(.+)", None),
        (r"read aloud[:\s]+(.+)", None),
        (r"say[:\s]+(.+)", None),
        (r"speak[:\s]+(.+)", None),
    ]
    for pat, _ in tts_patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            text_to_read = m.group(1).strip().strip('"'+"'") or message
            return await do_tts(text_to_read)

    # Navigation: "navigate to ...", "directions to ...", "how to get to ...",
    # "where is the nearest ...", etc.
    nav_patterns = [
        r"navigate to (.+?)(?:\?|$| with| providing| for)",
        r"directions to (.+?)(?:\?|$| with| providing| for)",
        r"how (?:do i get|to get) to (.+?)(?:\?|$| with| providing| for)",
        r"(?:where is|find) (?:the )?nearest (.+?)(?:\?|$)",
        r"go to (.+?)(?:\?|$| with| providing| for)",
    ]
    mobility = "general"
    if "wheelchair" in input_lower or "wheel chair" in input_lower:
        mobility = "wheelchair"
    elif "cane" in input_lower:
        mobility = "cane"
    elif "visual impairment" in input_lower or "blind" in input_lower:
        mobility = "visual_impairment"
    # strip the "with wheelchair accessibility" tail before extracting
    trimmed = re.sub(r"\s+with\s+wheelchair\s+(?:accessibility|access).*", "", message, flags=re.IGNORECASE)
    for pat in nav_patterns:
        m = re.search(pat, trimmed, re.IGNORECASE)
        if m:
            dest = m.group(1).strip().rstrip(".?!")
            # Clean up articles left over from patterns like "nearest pharmacy"
            dest = re.sub(r"^(the\s+)", "", dest, flags=re.IGNORECASE).strip()
            return await do_navigation(destination=dest, mobility_profile=mobility)

    # Health (text-only): explicit food-safety / allergy / medication phrasing
    health_phrases = [
        "safe for", "safe to eat", "safe to consume", "allergy", "allergen",
        "medication", "taking", "meal plan", "plan a meal",
    ]
    if any(p in input_lower for p in health_phrases):
        if "allergies" in user_profile or "allergy" in input_lower or "allergen" in input_lower:
            user_profile.setdefault("allergies", [])
        return await do_health(message, user_profile)

    # Sign language (text mention of signing without an image): help reply
    if any(p in input_lower for p in ["sign language", "what is he signing", "signing", "gesture"]):
        return {
            "type": "sign_language",
            "response": (
                "👐 SIGN LANGUAGE DETECTION\n\n"
                "To detect sign language gestures, please upload an image or video frame.\n\n"
                "I can detect these common gestures:\n"
                "  • HELP — Requesting assistance\n"
                "  • STOP — Request to pause\n"
                "  • EMERGENCY — Urgent help needed\n"
                "  • DANGER — Warning about a threat\n"
                "  • YES / NO — Affirmation or denial\n"
                "  • THANK YOU — Gratitude\n"
                "  • FOOD / WATER — Basic needs\n"
                "  • MEDICAL — Health assistance needed\n\n"
                "Upload an image showing a hand gesture and I'll tell you what it means."
            ),
            "timestamp": datetime.now().isoformat(),
        }

    # ── Image + health/food query → OCR then health ──
    health_intent_signals = [
        "safe", "allergy", "allergen", "ingredient", "dietary",
        "consume", "peanut", "nut", "marzipan", "dairy", "gluten",
    ]
    if image_base64 and any(s in input_lower for s in health_intent_signals):
        from app.mcp.vision_server import analyze_image
        ocr = await analyze_image(image_base64, task="ocr")
        ingredient_list: Optional[List[str]] = None
        if "text" in ocr and ocr.get("text"):
            raw = ocr["text"]
            # Simple split: comma, semicolon, or newline delimited
            ingredient_list = [
                t.strip()
                for t in re.split(r"[,\n;]|\band\b", raw, flags=re.IGNORECASE)
                if t.strip() and len(t.strip()) > 1
            ]
        return await do_health(message, user_profile, ingredient_list=ingredient_list)

    # ── Image with no strong intent → vision (describe) ──
    if image_base64:
        return await do_vision(image_base64, task="describe", user_input=message)

    # ── No image, no emergency, no clear handle: return a structured chat ──
    # The ADK agent uses individual tools for TTS / nav / health / sign, so this
    # branch is mainly the FastAPI fallback path when only a text message is sent.
    return _chat_response(message)


def _chat_response(user_input: str) -> Dict[str, Any]:
    """Polite fallback when the message doesn't clearly map to a tool."""
    return {
        "type": "chat",
        "response": (
            "💬 ACCESSAI ASSISTANT\n\n"
            f"I received your message: \"{user_input}\"\n\n"
            "I can help you with:\n"
            "  • 👁️ Image analysis — Upload a photo and I'll describe it\n"
            "  • 🔊 Text-to-speech — Say 'read this aloud: [text]'\n"
            "  • 🧭 Navigation — Ask for directions to a place\n"
            "  • 🏥 Health — Ask about allergies, food safety, medications\n"
            "  • 👐 Sign language — Upload sign language images for transcription\n"
            "  • 🚨 Emergency — Describe an emergency situation\n\n"
            "What would you like help with?"
        ),
        "timestamp": datetime.now().isoformat(),
    }


# ── Convenience alias for external imports ────────────────────────────────────

async def chat_with_accessai(
    message: str,
    image_base64: Optional[str] = None,
    user_profile: Optional[Dict[str, Any]] = None,
) -> str:
    """Main chat interface — returns the 'response' string for display."""
    result = await handle_request(message, image_base64, user_profile)
    return result.get("response", "I apologize, but I couldn't process your request.")