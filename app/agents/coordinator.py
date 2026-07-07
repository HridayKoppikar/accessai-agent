"""
Coordinator Agent - Central Orchestrator for AccessAI

LLM-routing: the coordinator LLM decides which capability each request needs
and calls the matching *real* tool (vision, TTS, navigation, health, sign, emergency).

The old keyword-classifier is retained as an optional hint function ('classify_request')
but routing is driven by the LLM understanding of the user's intent now.
"""

import os
from google.adk.agents import Agent
from google.adk.models import Gemini
from datetime import datetime
from typing import Dict, Any, Optional
from google.adk.tools import ToolContext


DEFAULT_MODEL = "gemini-2.5-flash"


# ── Skill tool wrappers ───────────────────────────────────────────────────────
# Each wrapper is a plain async function — ADK automatically wraps them as
# FunctionTool so the LLM can call them by name and access their docstring args.


async def analyze_image_for_user(
    image_data: str,
    task: str = "describe",
    user_input: str = "",
) -> str:
    """Analyze an image uploated by the user.  Use this when the user uploads a
    photo and wants to know what is in it, needs text extracted (OCR), objects
    detected, or a sign-language gesture identified.

    Args:
        image_data: Base64-encoded image string from the user.
        task: What to do with the image — "describe" (default), "ocr",
              "detect_objects", or "sign_language".
        user_input: The user's natural-language request for additional context.

    Returns:
        A formatted response describing what was found in the image.
    """
    from app.router import do_vision
    result = await do_vision(image_data, task=task, user_input=user_input)
    return result.get("response", f"Vision analysis returned: {result}")


async def text_to_speech_for_user(text_to_read: str, tool_context: ToolContext) -> str:
    """Read text aloud for visually-impaired users. Call this when the user says
    things like 'read this aloud', 'say this', or asks for audio output.

    Args:
        text_to_read: The exact text to convert to spoken audio.
    """
    from app.router import do_tts
    result = await do_tts(text_to_read, tool_context)
    return result.get("response", f"TTS result: {result}")

"""
async def text_to_speech_for_user(text_to_read: str) -> str:
    ""Read text aloud for visually-impaired users.  Call this when the user says
    things like 'read this aloud', 'say this', or asks for audio output.

    Args:
        text_to_read: The exact text to convert to spoken audio.

    Returns:
        Confirmation that the audio was generated, or a setup message if TTS is
        not yet configured.
    ""
    from app.router import do_tts
    result = await do_tts(text_to_read)
    return result.get("response", f"TTS result: {result}")
"""

async def navigation_guidance_for_user(
    destination: str,
    mobility_profile: str = "general",
    start_location_lat: Optional[float] = 18.96,
    start_location_lng: Optional[float] = 72.814,
) -> str:
    """Get turn-by-turn directions with accessibility considerations.  Call this
    when the user asks for directions, navigation, or 'how to get to' somewhere.

    Args:
        destination: Name or address of the destination.
        mobility_profile: One of "wheelchair", "cane", "visual_impairment",
                          or "general".
        start_location_lat: Optional starting latitude.
        start_location_lng: Optional starting longitude.

    Returns:
        Turn-by-turn navigation instructions formatted for reading aloud.
    """
    from app.router import do_navigation

    start = None
    if start_location_lat is not None and start_location_lng is not None:
        start = {"lat": start_location_lat, "lng": start_location_lng}

    result = await do_navigation(
        destination=destination,
        mobility_profile=mobility_profile,
        start_location=start,
    )
    return result.get("response", f"Navigation result: {result}")


async def health_check_for_user(
    user_query: str,
    allergies: Optional[list] = None,
    medications: Optional[list] = None,
    dietary_restrictions: Optional[list] = None,
) -> str:
    """Check food safety, medication interactions, or plan meals — call this for
    ANY health-related question.  Examples: 'Is this safe for nut allergies?',
    'Can I eat this with my medication?', 'What meals can I make with rice and beans?'

    Args:
        user_query: The user's health question in natural language.
        allergies: Optional list of the user's known allergies.
        medications: Optional list of current medications.
        dietary_restrictions: Optional list of dietary restrictions.

    Returns:
        A health assessment with warnings or a meal plan.
    """
    from app.router import do_health

    profile = {
        "allergies": allergies or [],
        "medications": medications or [],
        "dietary_restrictions": dietary_restrictions or [],
    }
    # Strip keys set to None to avoid confusing the skill
    profile = {k: v for k, v in profile.items() if v is not None}

    result = await do_health(user_query, profile)
    return result.get("response", f"Health result: {result}")


async def sign_language_detection_for_user(frames_data: str) -> str:
    """Detect sign-language gestures from one or more video frames / images.
    Call this when the user uploads an image or video frame and asks 'what is he
    signing?' or 'detect sign language'.

    Args:
        frames_data: Base64-encoded image or video frame(s).

    Returns:
        The detected gesture and urgency level.
    """
    from app.router import do_sign_language
    result = await do_sign_language(frames_data)
    return result.get("response", f"Sign language result: {result}")


async def emergency_alert_for_user(situation_description: str) -> str:
    """Handle an emergency.  Call this IMMEDIATELY when the user reports a
    medical or safety emergency.  Examples: 'I have fallen and cannot get up',
    'emergency — I need help', 'Call 911'.

    Args:
        situation_description: What happened / what the user reported.

    Returns:
        Emergency alert confirmation with next steps.
    """
    from app.router import do_emergency
    result = await do_emergency(situation_description)
    return result.get("response", f"Emergency result: {result}")


# ── Optional classifier (LLM-driven, but available as a hint) ─────────────────

def classify_request_type(user_input: str, context: dict = None) -> str:
    """Suggest a capability category for the user's request.

    This is NOT the router — it is an optional hint function the coordinator
    LLM may call when uncertain.  The LLM is still the final decision-maker:
    it calls the appropriate tool based on its understanding of the user's need.

    Args:
        user_input: The user's text input.
        context: Current conversation context.

    Returns:
        One of: 'emergency', 'perception', 'health', 'navigation', 'chat'
    """
    if context is None:
        context = {}

    input_lower = user_input.lower()

    # ** Negation veto — skip ALL emergency / safety routing **
    negations = [
        "not an emergency", "no emergency", "isn't an emergency",
        "wasn't an emergency", "this is not an emergency",
        "it's not an emergency",
    ]
    for neg in negations:
        if neg in input_lower:
            # User explicitly said this is NOT an emergency. Don't escalate.
            # Fall through to normal routing (skip emergency checks below).
            break
    else:
        # True emergencies: expand to include 911, fell, fallen, common crises.
        emergency_phrases = [
            "emergency", "danger", "urgent", "accident", "sos", "call 911",
            "ambulance", "breathing", "bleeding", "chest pain", "cannot get up",
            "can't get up", "fallen", "fell down", "not breathing",
            "heart attack", "stroke", "unconscious", "fainted", "fire",
        ]
        if any(p in input_lower for p in emergency_phrases):
            # "help!" with a bang, or "help" + an action, is emergency;
            # plain "help" alone is not.
            if "help!" in input_lower or (
                "help" in input_lower and any(a in input_lower for a in ["now","immediately","fell","fallen","danger","emergency","need help","injured"])
            ):
                return "emergency"
            if "sos" in input_lower:
                return "emergency"
            if any(p in input_lower for p in ["emergency","danger","accident","sos","call 911","ambulance","bleeding","chest pain","cannot get up","can't get up","heart attack","stroke","unconscious","fainted","fire"]):
                return "emergency"

    # Perception / visual
    perception_signals = [
        "describe", "look at", "scan", "read this", "what is this",
        "image", "camera", "photo", "sign", "label", "package",
        "what do you see", "sign language", "signing",
    ]
    if any(k in input_lower for k in perception_signals):
        return "perception"

    # Health
    health_signals = [
        "allergy", "allergen", "medication", "medicine", "diet",
        "ingredient", "safe to eat", "safe to consume", "safe for",
        "prescription", "nut allergy", "peanut", "marzipan",
        "dietary", "consume",
    ]
    if any(k in input_lower for k in health_signals):
        return "health"

    # Navigation
    navigation_signals = [
        "navigate", "direction", "go to", "where is", "turn",
        "walking", "path", "route", "how do i get", "nearest",
        "find a", "pharmacy", "hospital",
    ]
    if any(k in input_lower for k in navigation_signals):
        return "navigation"

    return "chat"


# ── Utility tools (kept for profile/session management — harmless) ────────────

def update_user_profile(
    user_id: str,
    profile_data: dict,
    encryption_required: bool = True
) -> dict:
    """Update user's profile with encrypted storage."""
    return {
        'user_id': user_id,
        'updated_fields': list(profile_data.keys()),
        'encrypted': encryption_required,
        'timestamp': datetime.now().isoformat(),
        'status': 'success'
    }


def get_user_profile(user_id: str, category: str = None) -> dict:
    """Retrieve user profile from encrypted storage."""
    return {
        'user_id': user_id,
        'health': {
            'allergies': [],
            'medications': [],
            'dietary_restrictions': []
        },
        'accessibility': {
            'vision_impaired': False,
            'hearing_impaired': False,
            'mobility_profile': 'general'
        },
        'emergency_contacts': [],
        'safe_zones': [],
        'preferences': {}
    }


def manage_session_state(
    session_id: str,
    updates: dict,
    action: str = 'update'
) -> dict:
    """Manage conversation session state."""
    return {
        'session_id': session_id,
        'action': action,
        'status': 'success',
        'timestamp': datetime.now().isoformat()
    }


# ── Coordinator agent creation ───────────────────────────────────────────────

def create_coordinator_agent() -> Agent:
    """Create the Coordinator agent for routing and state management.

    The coordinator's LLM decides which tool(s) to call based on the user's need.
    It does NOT narrate 'routing to X agent' — it simply calls the tool and
    returns the result to the user.
    """
    # Load per-skill instruction markdowns so the LLM gets detailed guidance
    # without the core instruction body becoming unmanageably long.
    _skill_dir = os.path.join(os.path.dirname(__file__), '..', 'skills')
    _skill_mds = ['VISION_SKILL.md', 'HEALTH_SKILL.md', 'NAVIGATION_SKILL.md',
                  'SIGN_LANGUAGE_SKILL.md', 'EMERGENCY_SKILL.md', 'TTS_SKILL.md']
    _skill_instructions = ''
    for _md in _skill_mds:
        _md_path = os.path.join(_skill_dir, _md)
        try:
            with open(_md_path, 'r', encoding='utf-8') as _f:
                _skill_instructions += _f.read() + '\n\n'
        except Exception:
            pass  # .md missing — fall through to the core instruction

    return Agent(
        name="coordinator_agent",
        model=Gemini(model=DEFAULT_MODEL),
        instruction=_skill_instructions + """You are AccessAI, a 24/7 personal accessibility assistant for
visually and hearing impaired people.  You speak clearly, are patient, and your
single goal is to make the world accessible to your user.

Every user message falls into one of these capabilities. **Pick the right tool
and call it.** Do NOT say 'routing to X agent' or narrate your internal process —
just call the tool and share the result.

## Your tools (and when to call them)

**CRITICAL for images:** You are a multimodal model — you CAN see images attached to
messages.  If the user attaches an image and asks you to describe the scene, describe
it DIRECTLY from what you see.  Do NOT call analyze_image_for_user for general
scene descriptions / object detection — you already have vision.

Only call **analyze_image_for_user** when:
  - The user specifically asks you to EXTRACT TEXT from a label, sign, or document.
    In that case call it with task='ocr'.
  - The user asks about sign language gestures in an image.  In that case call it
    with task='sign_language' (or use sign_language_detection_for_user).
  - General scene description and object detection are done by YOU directly — you
    can see the image.

1. **analyze_image_for_user(image_data, task, user_input)** —
   OCR / text extraction from images, or sign-language analysis.
   Do NOT use for general scene description — describe the image directly yourself.

2. **text_to_speech_for_user(text_to_read)** — Use when the user says 'read this aloud',
   'say this', or asks you to read something out loud.  Pass the *exact text* as a
   single string.

3. **navigation_guidance_for_user(destination, mobility_profile, ...)** — Use for
   directions / navigation.  The tool handles the rest.

4. **health_check_for_user(user_query, allergies, medications, dietary_restrictions)** —
   Use for ANY food safety, allergy, medication, or meal-planning question.

5. **sign_language_detection_for_user(frames_data)** — Programmatic batch-frame sign-
   language detection (API use).  For attached images the user uploaded directly,
   describe signs with your own vision first — do NOT call this tool.

6. **emergency_alert_for_user(situation_description)** — Highest priority. Call immediately
   for any emergency.

## General chat
If the user is just greeting you or asking what you can do, respond directly
with a brief, warm introduction listing your capabilities. Keep it short.

When responding to any request, keep your own replies brief — let the tool
outputs carry the detail. Never wrap a tool call in print() or any other
function — call the tool directly by name.

## Important ground rules
- Be patient and empathetic. Many users rely on you for safety and independence.
- You can see images attached to messages — describe scenes, objects, and what you see
  DIRECTLY without calling a tool.  Only call analyze_image_for_user for OCR (text
  extraction from labels/signs/documents) or sign-language detection.
- When a user says 'read aloud' or 'say' followed by text, call text_to_speech_for_user
  immediately — don't echo the text first, just call the tool.
- If a request spans two capabilities (e.g. 'Is this food label safe?'), you can call
  tools in sequence: first analyze_image_for_user(task='ocr') for the label text, then
  health_check_for_user with the extracted text as user_query.
- Emergency always wins over everything else. Act immediately.""",
        tools=[
            analyze_image_for_user,
            text_to_speech_for_user,
            navigation_guidance_for_user,
            health_check_for_user,
            sign_language_detection_for_user,
            emergency_alert_for_user,
            classify_request_type,
            update_user_profile,
            get_user_profile,
            manage_session_state,
        ]
    )