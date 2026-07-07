"""
Transcription Skill - AccessAI

Provides auditory assistance capabilities including:
- Speech-to-text (STT) for hearing impaired users
- Text-to-speech (TTS) narration for visually impaired users
- Sign language gesture detection with text narration
- Audio alerts and notifications
"""

import base64
from datetime import datetime
from typing import Dict, List, Optional, Union

# Try to import Google Cloud Speech-to-Text
try:
    from google.cloud import speech as cloud_speech
    _SPEECH_AVAILABLE = True
except ImportError:
    _SPEECH_AVAILABLE = False

# Try to import Google Cloud Text-to-Speech
try:
    from google.cloud import texttospeech as cloud_tts
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


# =============================================================================
# Text-to-Speech (TTS) Functions
# =============================================================================

def get_tts_client():
    """Get Text-to-Speech client if available."""
    if not _TTS_AVAILABLE:
        return None
    try:
        return cloud_tts.TextToSpeechClient()
    except Exception:
        return None


async def text_to_speech(
    text: str,
    voice_language: str = 'en-US',
    voice_gender: str = 'neutral',
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
    output_format: str = 'mp3'
) -> Dict:
    """
    Convert text to speech audio.

    Args:
        text: Text to convert to speech
        voice_language: Language code (e.g., 'en-US', 'en-GB')
        voice_gender: Voice gender ('male', 'female', 'neutral')
        speaking_rate: Speech rate (0.25 to 4.0)
        pitch: Pitch adjustment (-20.0 to 20.0)
        output_format: Audio format ('mp3', 'wav', 'ogg')

    Returns:
        Audio data and metadata
    """
    # Check if TTS is available
    if not _TTS_AVAILABLE:
        return {
            'status': 'unavailable',
            'text': text,
            'audio_data': None,
            'suggestion': (
                'To enable TTS, install Google Cloud Text-to-Speech:\n'
                'pip install google-cloud-texttospeech\n'
                'Then authenticate with:\n'
                'gcloud auth application-default login'
            ),
            'mock_audio_description': f'TTS Placeholder: "{text[:100]}"'
        }

    try:
        client = get_tts_client()
        if client is None:
            return {
                'status': 'client_error',
                'text': text,
                'suggestion': 'Please authenticate with Google Cloud: gcloud auth application-default login'
            }

        # Configure voice
        voice_config = cloud_tts.VoiceSelectionParams(
            language_code=voice_language,
            name='en-US-Neural2-F' if voice_gender == 'female' else 'en-US-Neural2-J' if voice_gender == 'male' else 'en-US-Neural2-C'
        )

        # Configure audio
        audio_config = cloud_tts.AudioConfig(
            audio_encoding=cloud_tts.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch
        )

        # Generate speech
        synthesis_input = cloud_tts.SynthesisInput(text=text)
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_config,
            audio_config=audio_config
        )

        # Return audio data as base64
        audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')

        return {
            'status': 'success',
            'audio_data': audio_base64,
            'format': output_format,
            'duration_estimate': f'{len(text) / 15:.1f} seconds',  # Approximate
            'voice': voice_config.name,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'error',
            'text': text,
            'error': str(e),
            'suggestion': 'Check your Google Cloud credentials and Text-to-Speech API access'
        }


def generate_audio_narration(
    content: str,
    narration_style: str = 'clear',
    speed: str = 'normal'
) -> str:
    """
    Generate audio narration for accessibility.

    This function is used by the Assistant Agent to provide:
    - Voice output for visually impaired users
    - Audio alerts and warnings
    - Spoken navigation instructions
    - TTS response to text input

    Args:
        content: Text content to narrate
        narration_style: 'clear', 'empathetic', 'urgent', 'calm'
        speed: 'slow', 'normal', 'fast'

    Returns:
        Narration instructions and audio reference
    """
    # Map narration style to voice parameters
    style_config = {
        'clear': {'pitch': 0.0, 'speaking_rate': 1.0, 'tone': 'neutral'},
        'empathetic': {'pitch': 2.0, 'speaking_rate': 0.9, 'tone': 'warm'},
        'urgent': {'pitch': -1.0, 'speaking_rate': 1.2, 'tone': 'alert'},
        'calm': {'pitch': 1.0, 'speaking_rate': 0.85, 'tone': 'soothing'}
    }

    speed_map = {
        'slow': 0.8,
        'normal': 1.0,
        'fast': 1.2
    }

    config = style_config.get(narration_style, style_config['clear'])
    config['speaking_rate'] *= speed_map.get(speed, 1.0)

    # Format content for better narration
    formatted_content = _format_for_narration(content)

    return (
        f"🔊 AUDIO NARRATION READY\n\n"
        f"Content: {formatted_content[:200]}{'...' if len(formatted_content) > 200 else ''}\n"
        f"Voice settings:\n"
        f"  • Style: {narration_style}\n"
        f"  • Speed: {speed} (rate: {config['speaking_rate']:.2f})\n"
        f"  • Pitch: {config['pitch']}\n\n"
        f"To listen: Use the TTS audio player or say 'read this aloud'\n"
        f"Estimated duration: {len(formatted_content) / 15:.1f} seconds"
    )


def _format_for_narration(text: str) -> str:
    """Format text for optimized speech synthesis."""
    # Replace common abbreviations with full words
    replacements = {
        ' Mr.': ' Mister',
        ' Mrs.': ' Missus',
        ' Dr.': ' Doctor',
        ' Jr.': ' Junior',
        ' Sr.': ' Senior',
        ' Ltd.': ' Limited',
        ' Inc.': ' Incorporated',
        ' Corp.': ' Corporation',
        ' Co.': ' Company',
        ' St.': ' Street',
        ' Ave.': ' Avenue',
        ' Rd.': ' Road',
        ' Blvd.': ' Boulevard',
        ' #': ' Number',
    }

    formatted = text
    for abbr, full in replacements.items():
        formatted = formatted.replace(abbr, full)

    return formatted


# =============================================================================
# Speech-to-Text (STT) Functions
# =============================================================================

def get_speech_client():
    """Get Speech-to-Text client if available."""
    if not _SPEECH_AVAILABLE:
        return None
    try:
        return cloud_speech.SpeechClient()
    except Exception:
        return None


async def speech_to_text(
    audio_data: Union[str, bytes],
    language_code: str = 'en-US',
    enable_automatic_punctuation: bool = True,
    profanity_filter: bool = False
) -> Dict:
    """
    Convert speech audio to text.

    This function is used by hearing impaired users to:
    - Speak instead of type
    - Transcribe phone calls
    - Convert voice messages to text

    Args:
        audio_data: Base64 encoded audio or audio file path
        language_code: Language code for speech recognition
        enable_automatic_punctuation: Add punctuation automatically
        profanity_filter: Filter profanity from output

    Returns:
        Transcribed text and confidence metrics
    """
    # Check if STT is available
    if not _SPEECH_AVAILABLE:
        return {
            'status': 'unavailable',
            'audio_received': bool(audio_data),
            'transcript': None,
            'suggestion': (
                'To enable STT, install Google Cloud Speech-to-Text:\n'
                'pip install google-cloud-speech\n'
                'Then authenticate with:\n'
                'gcloud auth application-default login'
            ),
            'mock_transcript': 'This is a placeholder transcript. Add Google Cloud Speech API to enable real transcription.'
        }

    try:
        client = get_speech_client()
        if client is None:
            return {
                'status': 'client_error',
                'suggestion': 'Please authenticate with Google Cloud: gcloud auth application-default login'
            }

        # Handle base64 audio
        if isinstance(audio_data, str) and audio_data.startswith('data:audio'):
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
        elif isinstance(audio_data, str):
            audio_bytes = base64.b64decode(audio_data)
        else:
            audio_bytes = audio_data

        # Configure recognition
        config = cloud_speech.RecognitionConfig(
            language_code=language_code,
            enable_automatic_punctuation=enable_automatic_punctuation,
            profanity_filter=profanity_filter,
            max_alternatives=1
        )

        # Perform recognition
        audio = cloud_speech.RecognitionAudio(content=audio_bytes)
        response = client.recognize(config=config, audio=audio)

        # Extract transcript
        transcript = ''
        confidence_scores = []
        for result in response.results:
            transcript += result.alternatives[0].transcript
            confidence_scores.append(result.alternatives[0].confidence)

        return {
            'status': 'success',
            'transcript': transcript,
            'confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'language': language_code,
            'word_count': len(transcript.split()),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'error',
            'audio_received': bool(audio_data),
            'error': str(e),
            'suggestion': 'Check your Google Cloud credentials and Speech-to-Text API access'
        }


async def transcription_narrator_skill(
    input_type: str,
    content: Union[str, bytes] = None
) -> str:
    """
    Skill for handling speech-to-text and text-to-speech operations.

    This skill is attached to the Assistant Agent and provides:
    - Text input from hearing impaired users (keyboard typing) → read aloud
    - Speech input from users → text transcription
    - Audio narration of visual content descriptions

    Args:
        input_type: 'text_to_speak' or 'speech_to_text'
        content: Text to convert to speech OR audio data for transcription

    Returns:
        Transcribed text or TTS audio reference
    """
    if input_type == 'text_to_speak':
        # Convert user's typed text to speech (for visually impaired)
        if isinstance(content, str):
            result = await text_to_speech(content)
            if result['status'] == 'success':
                return (
                    f"🔊 TEXT-TO-SPEECH READY\n\n"
                    f"Original text: \"{content[:100]}{'...' if len(content) > 100 else ''}\"\n"
                    f"Audio generated: Yes\n"
                    f"Duration: ~{len(content) / 15:.1f} seconds\n\n"
                    f"The audio is ready for playback through your device's speaker."
                )
            else:
                return (
                    f"🔊 TEXT-TO-SPEECH\n\n"
                    f"Original text: \"{content[:100]}{'...' if len(content) > 100 else ''}\"\n\n"
                    f"{result.get('suggestion', 'TTS not available')}"
                )

    elif input_type == 'speech_to_text':
        # Convert user's speech to text (for hearing impaired)
        result = await speech_to_text(content)
        if result['status'] == 'success':
            return (
                f"📝 SPEECH-TO-TEXT COMPLETE\n\n"
                f"Transcript: \"{result['transcript']}\"\n"
                f"Confidence: {result['confidence']:.0%}\n"
                f"Word count: {result['word_count']}\n\n"
                f"The spoken words have been transcribed to text."
            )
        else:
            return (
                f"📝 SPEECH-TO-TEXT\n\n"
                f"{result.get('suggestion', 'STT not available')}"
            )

    return "Please provide input_type ('text_to_speak' or 'speech_to_text') and content."


# =============================================================================
# Sign Language Detection & Narration
# =============================================================================

async def sign_language_narrator_skill(
    video_frames: Union[str, List[str]],
    gesture_scope: str = 'emergency'
) -> Dict:
    """
    Detect sign language gestures and provide text narration.

    This skill is used by hearing impaired users to communicate via sign language.
    The system detects gestures and outputs text for the conversation partner.

    Args:
        video_frames: Base64 encoded image/video frame(s)
        gesture_scope: 'emergency' (limited gesture set) or 'full' (extended vocabulary)

    Returns:
        Detected gestures with text transcription
    """
    # Emergency gesture vocabulary (most critical for accessibility)
    emergency_gestures = {
        'help': {
            'keywords': ['help', 'assistance', 'need help'],
            'urgency': 'high',
            'action': 'alert_user'
        },
        'stop': {
            'keywords': ['stop', 'wait', 'hold on'],
            'urgency': 'medium',
            'action': 'pause_operation'
        },
        'emergency': {
            'keywords': ['emergency', 'crisis', 'urgent', '911'],
            'urgency': 'critical',
            'action': 'trigger_emergency'
        },
        'danger': {
            'keywords': ['danger', 'unsafe', 'threat', 'harm'],
            'urgency': 'critical',
            'action': 'trigger_emergency'
        },
        'yes': {
            'keywords': ['yes', 'correct', 'affirmative', 'okay', 'ok'],
            'urgency': 'low',
            'action': 'confirm'
        },
        'no': {
            'keywords': ['no', 'negative', 'incorrect', 'wrong'],
            'urgency': 'low',
            'action': 'deny'
        },
        'thank you': {
            'keywords': ['thank', 'thanks', 'grateful', 'appreciate'],
            'urgency': 'low',
            'action': 'acknowledge'
        },
        'food': {
            'keywords': ['food', 'eat', 'hungry', 'meal', 'drink'],
            'urgency': 'low',
            'action': 'request_assistance'
        },
        'water': {
            'keywords': ['water', 'drink', 'thirsty', 'beverage'],
            'urgency': 'low',
            'action': 'request_assistance'
        },
        'medical': {
            'keywords': ['medical', 'doctor', 'hospital', 'sick', 'pain', 'injury'],
            'urgency': 'high',
            'action': 'alert_user'
        }
    }

    # Try real sign-language detection via the VisionAI MCP server, which is the
    # proven, working Vertex path (same code path the FastAPI camera app uses).
    try:
        from app.mcp.vision_server import analyze_image

        if isinstance(video_frames, str):
            frames_data = [video_frames]
        else:
            frames_data = list(video_frames)[:5]  # Use first 5 frames

        detected_gestures = []
        for frame_index, frame in enumerate(frames_data):
            result = await analyze_image(frame, task="sign_language")
            # If Vertex is not configured, analyze_image returns an 'error' key;
            # bail out to the honest demo fallback instead of fabricating a gesture.
            if 'error' in result and not result.get('analysis'):
                break

            detected_text = (result.get('analysis', '') or '').lower().strip()
            if not detected_text or 'no sign language' in detected_text or 'not visible' in detected_text:
                continue

            for gesture, info in emergency_gestures.items():
                if gesture in detected_text or any(kw in detected_text for kw in info['keywords']):
                    detected_gestures.append({
                        'gesture': gesture,
                        'confidence': 0.85,
                        'frame': frame_index
                    })
                    break

            if detected_gestures:
                break  # one primary gesture is enough

        if detected_gestures:
            primary = detected_gestures[0]['gesture']
            info = emergency_gestures.get(primary, {})
            return {
                'status': 'success',
                'gestures_detected': detected_gestures,
                'primary_gesture': primary,
                'text_transcription': primary.upper(),
                'related_keywords': info.get('keywords', []),
                'urgency': info.get('urgency', 'low'),
                'recommended_action': info.get('action', 'none'),
                'timestamp': datetime.now().isoformat()
            }

    except Exception:
        # Fall through to the honest demo fallback below
        pass

    # Honest fallback: when Vertex AI Vision is not configured we MUST NOT
    # fabricate a gesture. The previous "always return help" stub was unsafe —
    # it would report a fake emergency gesture for any uploaded image.
    return {
        'status': 'demo_mode',
        'gestures_detected': [],
        'primary_gesture': 'no_gesture_detected',
        'text_transcription': 'NO_GESTURE_DETECTED',
        'related_keywords': [],
        'urgency': 'low',
        'recommended_action': 'none',
        'message': (
            'Demo mode: live sign-language detection requires Vertex AI Vision. '
            'When GOOGLE_CLOUD_PROJECT is configured and authenticated, this skill '
            'analyzes the uploaded frame(s) and reports the detected gesture. '
            'No gesture was fabricated for this request.'
        ),
        'timestamp': datetime.now().isoformat()
    }


async def narrate_sign_to_text(sign_input: str) -> str:
    """
    Convert sign language input to readable text output.

    This is the output side of sign language communication -
    taking detected sign language and presenting it as text
    for the conversation partner (hearing person) to read.

    Args:
        sign_input: Detected gesture or sign language text

    Returns:
        Formatted text output for display
    """
    return (
        f"👐 SIGN LANGUAGE DETECTED\n\n"
        f"Gesture: {sign_input.upper()}\n\n"
        f"This sign has been converted to text for reading."
    )


# =============================================================================
# Audio Alert Functions
# =============================================================================

def generate_audio_alert(
    alert_type: str,
    message: str,
    urgency: str = 'warning'
) -> Dict:
    """
    Generate audio alert with appropriate tone and urgency.

    Args:
        alert_type: 'obstacle', 'emergency', 'navigation', 'health', 'info'
        message: Alert message content
        urgency: 'critical', 'warning', 'info'

    Returns:
        Audio alert configuration
    """
    urgency_config = {
        'critical': {
            'tone': 'urgent',
            'repeat': 3,
            'background_sound': 'alarm'
        },
        'warning': {
            'tone': 'alert',
            'repeat': 2,
            'background_sound': 'beep'
        },
        'info': {
            'tone': 'calm',
            'repeat': 1,
            'background_sound': 'none'
        }
    }

    config = urgency_config.get(urgency, urgency_config['info'])

    # Prepend urgency indicator
    urgency_prefix = {
        'critical': '🚨 EMERGENCY: ',
        'warning': '⚠️ WARNING: ',
        'info': 'ℹ️ INFO: '
    }

    full_message = urgency_prefix.get(urgency, '') + message

    return {
        'alert_type': alert_type,
        'urgency': urgency,
        'message': full_message,
        'audio_config': config,
        'repeat_count': config['repeat'],
        'playback_priority': 'high' if urgency in ['critical', 'warning'] else 'normal'
    }


# =============================================================================
# Main Skill Interface
# =============================================================================

async def transcription_skill(
    user_input: str,
    input_mode: str = 'text',
    audio_data: str = None
) -> str:
    """
    Main skill interface for transcription and narration services.

    This skill enables:
    - Hearing impaired: Type text → converted to speech
    - Visually impaired: Hear everything through TTS
    - Sign language users: Sign → detected → text output

    Args:
        user_input: Text input from user
        input_mode: 'text', 'speech', 'sign_language'
        audio_data: Audio data if input_mode is 'speech'

    Returns:
        Processed result in appropriate format
    """
    if input_mode == 'text':
        # Text input - convert to speech for visually impaired users
        narration = generate_audio_narration(user_input, narration_style='clear')
        return narration

    elif input_mode == 'speech':
        # Speech input - transcribe for hearing impaired users
        result = await speech_to_text(audio_data or user_input)
        if result['status'] == 'success':
            return f"📝 TRANSCRIBED: {result['transcript']}"
        return f"📝 TRANSCRIPTION: {result.get('mock_transcript', 'Unavailable')}"

    elif input_mode == 'sign_language':
        # Sign language input - detect and output text
        result = await sign_language_narrator_skill(user_input)
        if result['status'] == 'success':
            return (
                f"👐 SIGN DETECTED\n\n"
                f"Gesture: {result['primary_gesture'].upper()}\n"
                f"Urgency: {result['urgency']}\n"
                f"Recommended action: {result['recommended_action']}\n\n"
                f"When this connects to real vision AI, it will detect actual sign language!"
            )
        return f"👐 SIGN LANGUAGE: {result.get('text_transcription', 'Detecting...')}"

    return "Please specify input_mode: 'text', 'speech', or 'sign_language'"


# Example usage context for the agent
TRANSCRIPTION_SKILL_INSTRUCTION = """
You have access to transcription_narrator_skill and sign_language_narrator_skill for auditory assistance.

For VISUALLY IMPAIRED users:
- ALWAYS offer to read text aloud using TTS
- Provide audio alerts for important events
- Use clear, calm narration for general content
- Use urgent tone for emergencies and warnings

For HEARING IMPAIRED users:
- Provide text transcription of any spoken content
- Use clear text display with high contrast formatting
- Offer sign language gesture detection if available
- Never rely solely on audio alerts

For SIGN LANGUAGE users:
- Detect gestures from video input
- Output corresponding text for conversation
- Prioritize emergency gestures (help, danger, stop)
- When vision AI is connected, support full gesture vocabulary

Remember: These features make AccessAI accessible to users with different types of impairments.
"""