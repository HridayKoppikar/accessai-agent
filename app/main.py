"""
AccessAI Camera Server

FastAPI server for live camera feed with vision analysis.
Run with: uv run python app/main.py
Then open: http://localhost:8080
"""

import os
import sys
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import secret manager for GCP Secret Manager integration
from utils.secrets import get_secret, check_secrets_health

# Import the skills directly
from skills.transcription_skill import text_to_speech, speech_to_text, sign_language_narrator_skill
from mcp.vision_server import analyze_image

app = FastAPI(title="AccessAI Camera Server", version="0.1.0")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"


# =============================================================================
# Health Check & Status
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and local development."""
    # Check secrets health
    secrets_health = check_secrets_health()

    # Actually probe vision availability (not just env var)
    vision_ok = False
    maps_ok = False
    try:
        from app.mcp.vision_server import _VERTEXAI_AVAILABLE, _vision_client
        vision_ok = bool(_VERTEXAI_AVAILABLE and _vision_client is not None)
    except Exception:
        pass
    try:
        import os
        maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        maps_ok = bool(maps_key)
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "AccessAI Camera Server",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "secrets": {
            "all_configured": secrets_health['all_ready'],
            "missing": secrets_health['missing_secrets']
        },
        "features": {
            "vision_available": vision_ok,
            "maps_available": maps_ok,
            "transcription_available": True  # Skills are always available
        }
    }


@app.get("/")
async def root():
    """Serve the camera frontend."""
    camera_html = FRONTEND_DIR / "camera.html"
    if camera_html.exists():
        return FileResponse(camera_html)
    return HTMLResponse(content="""
    <html>
        <head><title>AccessAI - Accessibility Assistant</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
            <h1>🦾 AccessAI Camera Server</h1>
            <p>Your accessibility assistant is running!</p>
            <h2>Features Available:</h2>
            <ul>
                <li>✅ Real-time camera feed analysis</li>
                <li>✅ Object detection and scene description</li>
                <li>✅ OCR text extraction</li>
                <li>✅ Sign language gesture detection</li>
                <li>✅ Obstacle detection for navigation</li>
                <li>✅ Text-to-speech narration</li>
                <li>✅ Speech-to-text transcription</li>
            </ul>
            <h2>Endpoints:</h2>
            <ul>
                <li><code>/health</code> - Health check</li>
                <li><code>/api/analyze-image</code> - Analyze captured image</li>
                <li><code>/api/transcribe-text-to-speech</code> - Convert text to speech</li>
                <li><code>/api/transcribe-speech-to-text</code> - Convert speech to text</li>
                <li><code>/api/detect-sign-language</code> - Detect sign language</li>
            </ul>
            <p><strong>Note:</strong> Upload a camera.html file to the frontend/ folder for the camera interface.</p>
        </body>
    </html>
    """)


# =============================================================================
# Image Analysis API
# =============================================================================

@app.post("/api/analyze-image")
async def analyze_image_endpoint(data: dict):
    """Analyze a captured image using Vertex AI Vision."""
    try:
        import traceback
        image_data = data.get("image")
        task = data.get("task", "describe")

        if not image_data:
            raise HTTPException(status_code=400, detail="No image data provided")

        if not task:
            raise HTTPException(status_code=400, detail="No task specified")

        # Import vision server
        from mcp.vision_server import analyze_image

        # Call the vision analysis
        result = await analyze_image(image_data, task)

        # Log the result for debugging
        if 'error' in result:
            print(f"⚠️  Vision analysis error: {result['error']}")
            print(f"   Task: {task}")
            print(f"   Vertex AI available: ", end="")
            try:
                from mcp import vision_server
                print(f"{vision_server._VERTEXAI_AVAILABLE}")
                if not vision_server._VERTEXAI_AVAILABLE:
                    import os
                    print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
                    print(f"   GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
            except Exception as e:
                print(f"Error checking: {e}")

        return result

    except ImportError as e:
        print(f"❌ ImportError in analyze_image_endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import vision module: {str(e)}. "
                   "Ensure Vertex AI dependencies are installed."
        )
    except Exception as e:
        print(f"❌ Exception in analyze_image_endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Conversational Chat API
# =============================================================================

from app.router import handle_request, chat_with_accessai, do_emergency, do_navigation


@app.post("/api/chat")
async def chat_endpoint(data: dict):
    """
    Main conversational endpoint for AccessAI.

    Accepts:
        - message: User's text input
        - image_base64: Optional base64 encoded image
        - user_profile: Optional user profile (allergies, mobility, etc.)

    Returns:
        Formatted response from the appropriate skill/agent
    """
    try:
        message = data.get("message", "")
        image_base64 = data.get("image_base64")
        user_profile = data.get("user_profile", {})

        if not message:
            raise HTTPException(status_code=400, detail="No message provided")

        result = await handle_request(message, image_base64, user_profile)
        return result

    except Exception as e:
        import traceback
        print(f"❌ Exception in chat_endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Emergency & Navigation API
# =============================================================================

@app.post("/api/emergency")
async def emergency_endpoint(data: dict):
    """Trigger an emergency alert with user situation and optional location."""
    try:
        message = data.get("message", data.get("situation", ""))
        user_profile = data.get("user_profile", {})

        if not message:
            raise HTTPException(status_code=400, detail="No emergency situation provided")

        result = await do_emergency(message, user_profile)
        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Exception in emergency_endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/navigation")
async def navigation_endpoint(data: dict):
    """Get turn-by-turn directions with accessibility considerations."""
    try:
        destination = data.get("destination", "")
        mobility_profile = data.get("mobility_profile", "general")
        start_location = data.get("start_location")  # optional {lat, lng}

        if not destination:
            raise HTTPException(status_code=400, detail="No destination provided")

        result = await do_navigation(destination, mobility_profile, start_location)
        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Exception in navigation_endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Accessibility Features API
# =============================================================================

@app.post("/api/transcribe-text-to-speech")
async def text_to_speech_endpoint(data: dict):
    """Convert text to speech audio for visually impaired users."""
    try:
        text = data.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        result = await text_to_speech(text)

        # Return a more useful response
        if result.get('status') == 'unavailable':
            return {
                'status': 'info',
                'message': 'Text-to-Speech would reads: "' + text + '"',
                'tts_enabled': False,
                'setup_instructions': result.get('suggestion', 'Configure Google Cloud Text-to-Speech API'),
                'audio_data': None
            }
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe-speech-to-text")
async def speech_to_text_endpoint(data: dict):
    """Convert speech audio to text for hearing impaired users."""
    try:
        audio_data = data.get("audio")
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data provided")

        from skills.transcription_skill import speech_to_text

        result = await speech_to_text(audio_data)
        return result

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import transcription module: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detect-sign-language")
async def sign_language_detection_endpoint(data: dict):
    """Detect sign language gestures and output text."""
    try:
        video_frames = data.get("frames")
        if not video_frames:
            raise HTTPException(status_code=400, detail="No video frames provided")

        from skills.transcription_skill import sign_language_narrator_skill

        result = await sign_language_narrator_skill(video_frames)
        return result

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import sign language module: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Check secrets on startup
    secrets_health = check_secrets_health()

    print("\n" + "="*60)
    print(" 🦾 AccessAI Camera Server")
    print("="*60)
    print(f"\n  Opening at: http://localhost:8080")
    print(f"  Camera page: http://localhost:8080")
    print(f"  API endpoint: http://localhost:8080/api/analyze-image")
    print(f"  Health check: http://localhost:8080/health")
    print(f"\n  Secrets Status:")
    print(f"    • All configured: {'✓ Yes' if secrets_health['all_ready'] else '✗ No'}")
    if secrets_health['missing_secrets']:
        print(f"    • Missing: {', '.join(secrets_health['missing_secrets'])}")
    print(f"\n  Features:")
    print(f"    • Vision AI: {'✓' if get_secret('GOOGLE_CLOUD_PROJECT') else '✗ (configure GOOGLE_CLOUD_PROJECT)'}")
    print(f"    • Google Maps: {'✓' if get_secret('GOOGLE_MAPS_API_KEY') else '✗ (configure GOOGLE_MAPS_API_KEY)'}")
    print(f"    • Transcription: ✓ (skills available)")
    print(f"\n  Press Ctrl+C to stop")
    print("="*60 + "\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )