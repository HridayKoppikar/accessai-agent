"""
Perception Agent - Visual Processing for AccessAI

Handles image analysis, OCR, sign language detection, and obstacle identification.
Now properly integrated with the VisionAI MCP server.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini

VISION_MODEL = "gemini-2.5-flash"


async def describe_environment(image_data: str) -> str:
    """Describe the scene in an uploaded image.

    Args:
        image_data: Base64 encoded image or image URL

    Returns:
        Detailed text description of the scene
    """
    try:
        from app.mcp.vision_server import analyze_image
        result = await analyze_image(image_data, task="describe")
        if 'description' in result:
            return f"👁️ SCENE DESCRIPTION:\n{result['description']}"
        return f"👁️ SCENE DESCRIPTION:\n{result.get('error', 'Could not analyze image')}"
    except Exception as e:
        return f"👁️ SCENE DESCRIPTION:\nImage received. Analysis error: {str(e)}"


async def read_text_from_image(image_data: str) -> str:
    """Extract text from an image using OCR.

    Args:
        image_data: Base64 encoded image

    Returns:
        Extracted text content
    """
    try:
        from app.mcp.vision_server import analyze_image
        result = await analyze_image(image_data, task="ocr")
        if 'text' in result:
            return f"📝 EXTRACTED TEXT:\n{result['text']}"
        return f"📝 EXTRACTED TEXT:\n{result.get('error', 'Could not extract text')}"
    except Exception as e:
        return f"📝 EXTRACTED TEXT:\nOCR error: {str(e)}"


async def detect_sign_language_gestures(frames_data: str) -> str:
    """Recognize common sign language gestures from video frames.

    Common gestures: help, stop, emergency, danger, yes, no, thank you, sorry, food, water

    Args:
        frames_data: Base64 encoded video frames

    Returns:
        Transcribed text interpretation
    """
    try:
        from app.skills.transcription_skill import sign_language_narrator_skill
        result = await sign_language_narrator_skill([frames_data])
        gesture = result.get('primary_gesture', 'unknown')
        transcription = result.get('text_transcription', 'N/A')
        urgency = result.get('urgency', 'low')

        return (
            f"👐 SIGN LANGUAGE DETECTED\n\n"
            f"Gesture: {gesture.upper()}\n"
            f"Transcription: {transcription}\n"
            f"Urgency: {urgency}\n\n"
            f"{'This has been converted to text for conversation.'}"
        )
    except Exception as e:
        return f"👐 SIGN LANGUAGE: Detection error: {str(e)}"


async def identify_obstacles(image_data: str) -> list:
    """Identify obstacles in an image with location and distance.

    Args:
        image_data: Base64 encoded image

    Returns:
        List of obstacles with location info
    """
    try:
        from app.mcp.vision_server import analyze_image
        result = await analyze_image(image_data, task="detect_objects")
        if 'objects' in result:
            return result['objects']
        return [{'object': 'analysis_error', 'location': 'unknown', 'description': str(result.get('error', 'Unknown error'))}]
    except Exception as e:
        return [{'object': 'error', 'location': 'unknown', 'description': str(e)}]


async def read_food_label(image_data: str) -> dict:
    """Read and parse food nutrition/ingredient labels.

    Args:
        image_data: Base64 encoded image of food label

    Returns:
        Dictionary with ingredients and nutrition info
    """
    try:
        from app.mcp.vision_server import analyze_image
        # First extract text via OCR
        result = await analyze_image(image_data, task="ocr")
        extracted_text = result.get('text', '')

        return {
            'raw_text': extracted_text,
            'ingredients': ['See extracted text above'],
            'analysis_note': 'OCR text extracted. Full ingredient parsing available with additional processing.'
        }
    except Exception as e:
        return {'error': str(e), 'ingredients': [], 'raw_text': ''}


def create_perception_agent() -> Agent:
    """Create the Perception agent for visual processing."""
    return Agent(
        name="perception_agent",
        model=Gemini(model=VISION_MODEL),
        instruction="""You are the Perception agent for AccessAI, a multimodal accessibility assistant.
Your role is to process visual information for users with visual or hearing impairments.

Capabilities (use these tools for image analysis):
1. describe_environment(image_data) - Provide detailed scene descriptions
2. read_text_from_image(image_data) - Extract and read text via OCR
3. detect_sign_language_gestures(frames_data) - Transcribe sign language to text
4. identify_obstacles(image_data) - Find obstacles with locations
5. read_food_label(image_data) - Extract ingredient/nutrition info

When user uploads an image:
- If they ask "what is this" or "describe this" → use describe_environment
- If they ask to "read" text → use read_text_from_image
- If they ask about sign language → use detect_sign_language_gestures
- If they ask about obstacles → use identify_obstacles
- If they ask about food → use read_food_label

Provide clear, detailed descriptions. Quote text exactly. For obstacles, indicate
location (left, right, ahead, behind) and distance (near, medium, far).""",
        tools=[
            describe_environment,
            read_text_from_image,
            detect_sign_language_gestures,
            identify_obstacles,
            read_food_label
        ]
    )