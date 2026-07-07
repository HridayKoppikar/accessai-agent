"""
VisionAI MCP Server - AccessAI

Provides vision-based tools for image analysis, OCR, object detection, and
sign language gesture recognition.

Now integrated with real Vertex AI Vision model (gemini-2.5-flash).
"""

import os
import base64
from typing import List, Dict, Any, Optional

# Load .env file automatically for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import Vertex AI / Google Gen AI
try:
    from google.cloud import aiplatform
    from google.genai import Client, types
    import vertexai

    _VERTEXAI_AVAILABLE = True

    # Initialize Vertex AI
    _project = os.getenv('GOOGLE_CLOUD_PROJECT')
    _location = os.getenv('GOOGLE_CLOUD_LOCATION', 'asia-south1')

    if _project:
        vertexai.init(project=_project, location=_location)
        # Use the genai client instead of aiplatform.GenerativesModel
        _vision_client = Client(vertexai=True)
    else:
        _vision_client = None
        _VERTEXAI_AVAILABLE = False
except ImportError:
    _VERTEXAI_AVAILABLE = False
    _vision_client = None


def _decode_image(image_data: str) -> bytes:
    """Decode base64 image data to bytes."""
    if isinstance(image_data, bytes):
        return image_data

    # Handle data URL format
    if image_data.startswith('data:image'):
       	base64_data = image_data.split(',')[1]
    else:
       	base64_data = image_data

    # ADK playground may pass base64 with URL-safe chars or missing padding;
    # normalise before decoding.
    base64_data = base64_data.strip()
    # Fix URL-safe base64 (altchars)
    base64_data = base64_data.replace('-', '+').replace('_', '/')
    # Add missing padding so length is a multiple of 4
    remainder = len(base64_data) % 4
    if remainder:
        base64_data += '=' * (4 - remainder)

    return base64.b64decode(base64_data)


async def analyze_image(
    image_data: str,
    task: str = "describe",
    options: Dict = None
) -> Dict[str, Any]:
    """Analyze image using real Vertex AI Vision model.

    Args:
        image_data: Base64 encoded image or URL
        task: One of "describe", "ocr", "detect_objects", "sign_language"
        options: Additional task-specific options

    Returns:
        Real AI analysis results
    """
    if not _VERTEXAI_AVAILABLE or _vision_client is None:
        return {
            'error': 'Vertex AI not configured',
            'task': task,
            'suggestion': (
                'Ensure these environment variables are set:\n'
                'GOOGLE_CLOUD_PROJECT=your-project-id\n'
                'GOOGLE_CLOUD_LOCATION=asia-south1\n'
                'GOOGLE_GENAI_USE_VERTEXAI=true'
            ),
            'mock_result': _get_mock_result(task)
        }

    try:
        image_bytes = _decode_image(image_data)

        if options is None:
            options = {}

        if task == "describe":
            return await _describe_scene(image_bytes, options)
        elif task == "ocr":
            return await _extract_text(image_bytes)
        elif task == "detect_objects":
            return await _detect_objects(image_bytes)
        elif task == "sign_language":
            return await _detect_sign_gestures(image_bytes)
        else:
            return {'error': f'Unknown task: {task}'}

    except Exception as e:
        return {
            'error': str(e),
            'task': task,
            'image_analyzed': False
        }


async def _describe_scene(image_bytes: bytes, options: Dict) -> Dict[str, Any]:
    """Describe scene with accessibility focus."""
    focus = options.get('focus', 'accessibility')

    prompts = {
        'accessibility': (
            "Describe this image from the perspective of helping a visually impaired person "
            "understand their environment. Include: surroundings, potential obstacles, "
            "notable features, and anything important for navigation or awareness. "
            "Be detailed but clear and organized."
        ),
        'general': (
            "Provide a detailed description of what is shown in this image. "
            "Cover the main subjects, background, and any notable details."
        ),
        'navigational': (
            "Describe this scene for someone who needs to navigate through it. "
            "Focus on: path layout, obstacles, landmarks, doorways, stairs, "
            "and anything that affects movement through the space."
        )
    }

    prompt = prompts.get(focus, prompts['accessibility'])

    response = _vision_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(role='user', parts=[types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')])
        ],
        config=types.GenerateContentConfig(system_instruction=prompt)
    )

    return {
        'task': 'describe',
        'description': response.text,
        'model': 'gemini-2.5-flash',
        'focus': focus
    }


async def _extract_text(image_bytes: bytes) -> Dict[str, Any]:
    """OCR: Extract text from image."""
    response = _vision_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(role='user', parts=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ])
        ],
        config=types.GenerateContentConfig(system_instruction="Extract ALL text visible in this image. Return only the raw text content, preserving the layout as much as possible. If there is no text, respond with 'No text detected'.")
    )

    return {
        'task': 'ocr',
        'text': response.text,
        'has_text': 'No text detected' not in response.text,
        'model': 'gemini-2.5-flash'
    }


async def _detect_objects(image_bytes: bytes) -> Dict[str, Any]:
    """Detect objects with location information."""
    response = _vision_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(role='user', parts=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ])
        ],
        config=types.GenerateContentConfig(system_instruction="List all objects visible in this image with their approximate locations. "
            "Format each as: Object Name - Location (e.g., 'chair - left foreground', 'door - center background'). "
            "Include only objects that are clearly visible.")
    )

    # Parse the response into structured format
    lines = [l.strip() for l in response.text.split('\n') if l.strip()]
    objects = []

    for line in lines[:20]:  # Limit to 20 objects
        if ' - ' in line:
            parts = line.split(' - ', 1)
            objects.append({
                'name': parts[0].strip(),
                'location': parts[1].strip() if len(parts) > 1 else 'unknown',
                'confidence': 0.85  # Approximate
            })
        else:
            objects.append({'name': line, 'location': 'unspecified', 'confidence': 0.8})

    return {
        'task': 'detect_objects',
        'objects': objects,
        'object_count': len(objects),
        'model': 'gemini-2.5-flash'
    }


async def _detect_sign_gestures(image_bytes: bytes) -> Dict[str, Any]:
    """Detect sign language gestures."""
    response = _vision_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(role='user', parts=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ])
        ],
        config=types.GenerateContentConfig(system_instruction="Analyze this image for sign language gestures. Look for hand positions, "
            "finger configurations, and body language that indicate sign language. "
            "If you see sign language, identify the most likely gesture or word being signed. "
            "If no sign language is visible, state that clearly.")
    )

    return {
        'task': 'sign_language',
        'analysis': response.text,
        'model': 'gemini-2.5-flash'
    }


async def read_text_from_image(image_data: str) -> Dict[str, Any]:
    """OCR: Extract text from an image."""
    return await analyze_image(image_data, task='ocr')


async def describe_scene(
    image_data: str,
    focus_areas: List[str] = None
) -> Dict[str, Any]:
    """Describe a scene with accessibility focus.

    Args:
        image_data: Base64 encoded image
        focus_areas: Areas to focus on (e.g., ['obstacles', 'signs', 'people'])

    Returns:
        Detailed accessibility-focused description
    """
    options = {'focus': 'accessibility'}
    if focus_areas:
        options['focus_areas'] = focus_areas

    result = await analyze_image(image_data, task='describe', options=options)

    # Add structured accessibility information
    if 'description' in result:
        result['accessibility_notes'] = _extract_accessibility_notes(result['description'])
        result['obstacles'] = _extract_obstacles(result['description'])
        result['points_of_interest'] = _extract_points_of_interest(result['description'])

    return result


def _extract_accessibility_notes(description: str) -> List[str]:
    """Extract accessibility-specific notes from description."""
    # Would use NLP to extract structured data
    return ['Access for real structured extraction in production']


def _extract_obstacles(description: str) -> List[dict]:
    """Extract obstacles from description."""
    return []


def _extract_points_of_interest(description: str) -> List[dict]:
    """Extract points of interest from description."""
    return []


async def detect_obstacles(
    image_data: str,
    mobility_profile: str = 'general'
) -> Dict[str, Any]:
    """Detect obstacles with mobility-specific considerations.

    Args:
        image_data: Base64 encoded forward-facing image
        mobility_profile: 'wheelchair', 'cane', 'general'

    Returns:
        Obstacle list with severity and location
    """
    if not _VERTEXAI_AVAILABLE or _vision_client is None:
        return {
            'error': 'Vertex AI not configured',
            'obstacles': [],
            'mobility_specific_warnings': [],
            'path_clearance': 'unknown',
            'mock_obstacles': _get_mock_obstacles(mobility_profile)
        }

    try:
        image_bytes = _decode_image(image_data)

        mobility_context = {
            'wheelchair': (
                "For wheelchair navigation, identify obstacles that would block movement. "
                "Include: curbs, steps, narrow doorways, uneven pavement, low-hanging obstacles. "
                "Rate severity: CRITICAL (blocks path), WARNING (needs caution), INFO (minor). "
                "Estimate distance: immediate (0-1m), near (1-3m), far (3m+)."
            ),
            'cane': (
                "For cane/walking stick users, identify obstacles at ground and knee level. "
                "Include: steps, uneven surfaces, low obstacles, protruding objects. "
                "Rate severity and estimate distance."
            ),
            'general': (
                "Identify common walking obstacles. Rate severity and estimate distance."
            )
        }

        prompt = mobility_context.get(mobility_profile, mobility_context['general'])

        response = _vision_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(role='user', parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
                ])
            ],
            config=types.GenerateContentConfig(system_instruction=prompt)
        )

        # Parse the response
        obstacles = _parse_obstacles_from_text(response.text)

        return {
            'obstacles_detected': len(obstacles) > 0,
            'obstacle_count': len(obstacles),
            'obstacles': obstacles,
            'mobility_specific_warnings': [o['severity'] for o in obstacles if o['severity'] in ['CRITICAL', 'WARNING']],
            'path_clearance': 'blocked' if any(o['severity'] == 'CRITICAL' for o in obstacles) else 'adequate',
            'model': 'gemini-2.5-flash'
        }
    except Exception as e:
        return {
            'error': str(e),
            'obstacles': [],
            'path_clearance': 'unknown'
        }


def _parse_obstacles_from_text(text: str) -> List[dict]:
    """Parse obstacle data from vision model response."""
    obstacles = []

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Try to parse format: "object - location - severity - distance"
        parts = line.split('-')
        if len(parts) >= 2:
            obstacle = {
                'name': parts[0].strip(),
                'location': parts[1].strip() if len(parts) > 1 else 'unspecified',
                'severity': 'WARNING' if 'warning' in line.lower() else 'INFO',
                'distance': 'near' if 'immediate' not in line else 'immediate'
            }

            if 'CRITICAL' in line:
                obstacle['severity'] = 'CRITICAL'
            if 'far' in line:
                obstacle['distance'] = 'far'

            obstacles.append(obstacle)
        else:
            obstacles.append({
                'name': line,
                'location': 'unspecified',
                'severity': 'INFO',
                'distance': 'near'
            })

    return obstacles[:10]  # Limit to 10 obstacles


def _get_mock_obstacles(mobility_profile: str) -> List[dict]:
    """Return mock obstacles for when Vertex AI unavailable."""
    mock_data = {
        'wheelchair': [
            {'name': 'curb', 'location': 'ahead', 'severity': 'CRITICAL', 'distance': '5m'},
            {'name': 'construction barrels', 'location': 'right side', 'severity': 'WARNING', 'distance': '10m'}
        ],
        'cane': [
            {'name': 'step', 'location': 'immediate front', 'severity': 'CRITICAL', 'distance': 'immediate'},
            {'name': 'debris', 'location': 'path', 'severity': 'WARNING', 'distance': '3m'}
        ],
        'general': [
            {'name': 'pedestrian', 'location': 'left', 'severity': 'INFO', 'distance': '5m'}
        ]
    }
    return mock_data.get(mobility_profile, mock_data['general'])


def _get_mock_result(task: str) -> Dict[str, Any]:
    """Return mock result when Vertex AI unavailable."""
    mocks = {
        'describe': {
            'description': "For real vision analysis, ensure Vertex AI is configured. "
                          "This is a placeholder response.",
            'model': 'none (Vertex AI not configured)'
        },
        'ocr': {
            'text': 'No text extracted (Vertex AI required)',
            'has_text': False
        },
        'detect_objects': {
            'objects': [],
            'object_count': 0
        },
        'sign_language': {
            'analysis': 'Sign language detection requires Vertex AI',
            'detected_gestures': []
        }
    }
    return mocks.get(task, {})


def get_vision_tools() -> List[Dict[str, Any]]:
    """Get list of available vision tools for MCP registration."""
    return [
        {
            'name': 'analyze_image',
            'description': 'Analyze image using Vertex AI for description, OCR, objects, or sign language',
            'parameters': {
                'type': 'object',
                'properties': {
                    'image_data': {'type': 'string', 'description': 'Base64 image or URL'},
                    'task': {'type': 'string', 'enum': ['describe', 'ocr', 'detect_objects', 'sign_language']},
                    'options': {'type': 'object'}
                }
            }
        },
        {
            'name': 'read_text_from_image',
            'description': 'Extract text from image using OCR',
            'parameters': {
                'type': 'object',
                'properties': {
                    'image_data': {'type': 'string'}
                }
            }
        },
        {
            'name': 'describe_scene',
            'description': 'Get accessibility-focused scene description',
            'parameters': {
                'type': 'object',
                'properties': {
                    'image_data': {'type': 'string'},
                    'focus_areas': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        },
        {
            'name': 'detect_obstacles',
            'description': 'Detect obstacles for walking path safety',
            'parameters': {
                'type': 'object',
                'properties': {
                    'image_data': {'type': 'string'},
                    'mobility_profile': {'type': 'string', 'enum': ['wheelchair', 'cane', 'general']}
                }
            }
        }
    ]