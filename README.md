# AccessAI: Multimodal Accessibility Companion 🦾

A 24/7 personal accessibility assistant for visually and hearing impaired users, built with Google's Agent Development Kit (ADK).

**Track:** Agents for Good - Social Impact / Accessibility

---

## For judges
[Quick Start](#quick-start) (to run locally)
Cloud Run Deployment:
Agent Dev UI: https://accessai-124930446189.asia-south1.run.app/
Demo Camera App: https://accessai-124930446189.asia-south1.run.app/camera

## Overview

AccessAI is a multi-agent system that provides real-time environmental awareness, navigation assistance, health management, and emergency support for people with disabilities. The agent processes visual input, monitors safety, manages health data securely, and provides an empathetic conversational interface.

### Why Agents?

Unlike traditional assistants, AccessAI uses a **multi-agent architecture** to:
- Process complex, multi-modal inputs (images, text, location) simultaneously
- Maintain context across specialized domains (health, safety, navigation)
- Prioritize emergencies and safety warnings in real-time
- Orchestrate multiple capabilities for single user requests

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AccessAI Coordinator                         │
│              (Central Orchestrator / State Manager)              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Perception     │  │   Assistant     │  │   Safety        │
│  Agent          │  │   Agent         │  │   Agent         │
│                 │  │                 │  │                 │
│ • Visual input  │  │ • Text/Chat     │  │ • Hazard        │
│   processing    │  │   interface     │  │   detection     │
│ • Sign language │  │ • Voice TTS/STT │  │ • Emergency     │
│   gesture       │  │ • Health        │  │ • Location      │
│ • Object/scene  │  │   management    │  │   monitoring    │
│   recognition   │  │ • Task planning │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MCP Server:    │  │  MCP Server:    │  │  MCP Server:    │
│  VisionAI       │  │  HealthGuard    │  │  Navigo         │
│                 │  │                 │  │                 │
│ • Image         │  │ • Allergy       │  │ • Map data      │
│   analysis      │  │   checker       │  │ • Hazard DB     │
│ • OCR           │  │ • Medication    │  │ • Real-time     │
│ • Sign          │  │   tracker       │  │   updates       │
│   gestures      │  │ • Nutrition     │  │                 │
│ • Object        │  │                 │  │                 │
│   detection     │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Architecture Notes:**
- **Skills vs Agents:** Skills (in `app/skills/`) are reusable functions that agents can call, while agents (in `app/agents/`) are ADK stateful entities with conversation history and decision-making capabilities. The Transcription Skill serves all three agents but lives separately because it's a utility, not a decision-maker.
- **MCP Server Design:** Each sub-agent has a focused toolset (Vision Agent gets vision tools, Safety Agent gets hazard/navigation tools). This reduces hallucination risk (agents can't call tools they shouldn't) and makes debugging easier (if navigation fails, you know it's Navigo, not some collision between 20 tools).
- **Coordinator Routing:** The central orchestrator classifies user input using prompt-based routing ("You are a router...") and dispatches to the appropriate specialist agent(s). Multiple agents can be invoked for complex requests.

---

## Features

### 👁️ Perception Agent (Visual Processing)
- **Scene Description**: Detailed environmental descriptions from camera input
- **OCR**: Read text from signs, labels, documents
- **Sign Language Gesture Detection**: Detect common gestures (help, stop, emergency, danger, yes, no, thank you, food, water, medical)
- **Obstacle Detection**: Identify walking path hazards with location and distance
- **Food Label Reading**: Extract ingredients and nutrition information

### 💬 Assistant Agent (Core Interface)
- **Conversational Interface**: Natural, empathetic chat (primary input for non-speaking users)
- **Health Management**: Allergy checking, medication tracking, dietary restrictions
- **Meal Planning**: Safe recipe suggestions based on available ingredients
- **Navigation**: Turn-by-turn directions with mobility profile considerations
- **Text-to-Speech Narration**: Audio output for visually impaired users

### ⚠️ Safety Agent (Hazard Detection & Emergency)
- **Hazard Detection**: Real-time visual hazard scanning with severity levels (CRITICAL, WARNING, INFO)
- **Walking Obstacles**: Immediate warnings for path hazards
- **Environment Safety**: Overall safety assessment with recommendations
- **Emergency Alerts**: Trigger alerts with location and situation details
- **Geofencing**: Monitor safe zones and alert on deviations

### 🔊 Transcription Skill (Auditory Assistance)
- **Speech-to-Text (STT)**: Transcribe spoken words to text for hearing impaired users
- **Text-to-Speech (TTS)**: Read typed text aloud for visually impaired users
- **Sign Language Narrator**: Detect sign language gestures and output text for conversation partners
- **Audio Alerts**: Urgent warnings and notifications with appropriate tone

---

## Key Concepts Demonstrated (Kaggle Rubric)

| Course Requirement | Implementation | Demo Status |
|-------------------|----------------|-------------|
| **Agent/Multi-agent (ADK)** | 4 specialized agents (Coordinator, Perception, Assistant, Safety) with skill integration | ✅ Ready |
| **MCP Server** | 3 custom MCP servers (VisionAI, HealthGuard, Navigo) | ✅ Ready |
| **Security Features** | AES-256 encryption, privacy controls, data minimization, consent management | ✅ Ready |
| **Deployability** | Docker + docker-compose + Cloud Run ready | ✅ Ready |
| **Agent Skills** | Emergency, navigation, health, transcription skills in `app/skills/` | ✅ Ready |

---

## Project Structure

```
accessai-agent/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── agent.py                 # Main entry point (coordinator agent)
│   ├── main.py                  # FastAPI server with API endpoints
│   ├── main_workflow.py         # ADK Workflow graph (optional)
│   ├── agents/                  # Specialized agent implementations
│   │   ├── __init__.py
│   │   ├── coordinator.py       # Central orchestrator
│   │   ├── perception.py        # Visual processing
│   │   ├── assistant.py         # Core interface & health
│   │   └── safety.py            # Hazard detection & emergency
│   ├── mcp/                     # MCP servers
│   │   ├── __init__.py
│   │   ├── vision_server.py     # Vision AI tools
│   │   ├── health_server.py     # Health & nutrition tools
│   │   └── navigation_server.py # Maps & routing tools
│   ├── skills/                  # Agent skills (NEW)
│   │   ├── __init__.py
│   │   ├── emergency_skill.py   # Emergency alert skill
│   │   ├── navigation_skill.py  # Navigation skill
│   │   ├── health_skill.py      # Health management skill
│   │   └── transcription_skill.py # STT/TTS/Sign language skill
│   ├── security/                # Security module
│   │   ├── __init__.py
│   │   ├── encryption.py        # AES-256 encryption
│   │   └── privacy.py           # Privacy controls
│   └── utils/                   # Utility functions
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── deployment/
│   └── cloud-run/               # Cloud Run deployment configs
├── Dockerfile                   # Docker build configuration
├── docker-compose.yml           # Local development setup
├── pyproject.toml
├── README.md
└── .env.example
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Google Cloud project with AI Platform (requires billing)
- (Optional) Google Maps API key for navigation features

### Installation

```bash
# Install uv if not already installed
# macOS: brew install uv
# Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Clone and navigate to project
cd accessai-agent

# Install dependencies
uv sync
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required GCP Secrets:
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Your region (e.g., `asia-south1`)
- `GOOGLE_GENAI_USE_VERTEXAI=true` - Enable Vertex AI
- `GOOGLE_MAPS_API_KEY` - (Optional) For real navigation features

### Running Locally

```bash
# Option 1: Run the FastAPI server with camera feed support
uv run python -m app.main

# Option 2: Run the ADK agent playground
agents-cli playground

# Option 3: Using Docker
docker-compose up --build
```

---

## Usage Examples

### 1. Visual Environment Description
```
User: [uploads image of street scene]
AccessAI: 👁️ Visual: You are on a paved sidewalk. Ahead there is a crosswalk with 
          traffic lights. A bus stop bench is on your right, 5 meters away.
          ⚠️ Safety: Construction barrels blocking part of the path 10m ahead.
```

### 2. Food Safety Check
```
User: Is this safe for someone with peanut allergies?
[uploads food label image]
AccessAI: 🏥 Health Alert: ALLERGEN WARNING - Contains peanut oil
          Cross-contamination risk: HIGH
          Recommendation: Do not consume
```

### 3. Emergency Response
```
User: emergency
AccessAI: 🚨 EMERGENCY: Emergency Alert Activated
          - Recording emergency details
          - Notifying emergency contacts
          - Please confirm: Should I call emergency services?
```

### 4. Navigation with Accessibility
```
User: Navigate to nearest pharmacy
AccessAI: 🧭 Navigation:
          • Starting route on wheelchair-accessible path
          • Head north on Main Street 200m
          • Turn left toward Park Avenue 500m
          • Destination: Main Street Pharmacy (wheelchair ramp, lowered counter)
```

### 5. Text-to-Speech (Visually Impaired)
```
User: "Read this aloud: AccessAI helps visually impaired people navigate the world"
AccessAI: 🔊 TEXT-TO-SPEECH GENERATED
          Text: "AccessAI helps visually impaired people navigate the world"
          Status: success
          Audio data is ready for playback through your device.
```
_Requires Google Cloud Text-to-Speech (`uv add google-cloud-texttospeech`) and
authentication with `gcloud auth application-default login`._

### 6. Sign Language Detection (Hearing Impaired)
```
User: [uploads image of hand gesture] "What is he signing?"
AccessAI: [describes the gesture directly with its own multimodal vision]
          I can see an open palm facing forward — this appears to be a STOP gesture.
          Urgency: medium. It has been converted to text for conversation.
```
_The coordinator LLM (Gemini) has native multimodal vision and describes sign
gestures directly. A dedicated Vertex AI sign-language analysis tool is also
available for batch frame processing and longer vocabulary recognition._

---

## Security & Privacy

### Data Protection
- **AES-256 Encryption**: All health data encrypted at rest
- **Privacy-First**: Camera feeds processed in real-time, never stored
- **Minimal Retention**: Configurable data retention policies
- **No Third-Party Sharing**: User data stays within your GCP project

### Privacy Features
- User consent management for data categories
- Right to be forgotten (complete data deletion)
- Data access logging and audit trails
- Portable data export (GDPR compliant)

---

## Deployment

### Docker Deployment

```bash
# Build the Docker image
docker build -t accessai:latest .

# Run locally
docker run -p 8080:8080 --env-file .env accessai:latest

# Or use docker-compose
docker-compose up --build
```

### Cloud Run Deployment

```bash
# Set GCP project
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud run deploy accessai \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true"
```

### Environment Variables for Production

For production deployments, we recommend using **GCP Secret Manager** instead of environment variables:

```bash
# Store secrets in Secret Manager
gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic"
echo -n "your-api-key" | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

# Reference in Cloud Run
gcloud run deploy accessai \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

See the [GCP Secret Manager Documentation](https://cloud.google.com/secret-manager/docs) for more details.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and status (probes Vertex AI + Maps availability) |
| `/api/analyze-image` | POST | Real-time camera image analysis (vision, OCR, objects) |
| `/api/chat` | POST | Unified conversational interface — routes to vision/TTS/nav/health/emergency |
| `/api/emergency` | POST | Trigger an emergency alert with location and situation details |
| `/api/navigation` | POST | Get turn-by-turn directions with accessibility (wheelchair/cane/visual/general) |
| `/api/transcribe-text-to-speech` | POST | Convert text to speech audio (requires `google-cloud-texttospeech`) |
| `/api/transcribe-speech-to-text` | POST | Convert speech audio to text (requires `google-cloud-speech`) |
| `/api/detect-sign-language` | POST | Detect sign language gestures from video frames |

All endpoints are served by a single **unified skill router** (`app/router.py`) used by both
the FastAPI server and the ADK multi-agent coordinator. The coordinator LLM (powered by
Gemini 2.5 Flash) decides which capability to invoke based on the user's request and calls
the matching skill tool.

---

## Evaluation Rubric Alignment

### Category 1: The Pitch (30 points)

| Criteria | Implementation |
|----------|----------------|
| **Core Concept & Value (10)** | Clear mission: accessibility for visually/hearing impaired. Track: Agents for Good. Innovative multimodal approach. |
| **YouTube Video (10)** | Demo: real-time hazard detection → meal safety check → emergency alert workflow + sign language detection. |
| **Writeup (10)** | Well-documented architecture, clear problem statement, navigation and health use cases with before/after scenarios. |

### Category 2: The Implementation (70 points)

| Criteria | Implementation |
|----------|----------------|
| **Technical (50)** | 4-agent architecture, 3 MCP servers, 4 agent skills, AES-256 encryption, real-time vision processing, STT/TTS support. |
| **Documentation (20)** | Complete README with diagrams, API docs, deployment guide, security policies. |

---

## Troubleshooting

### Vertex AI Not Working
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Enable required APIs
gcloud services enable vertexai.googleapis.com
```

### Google Maps Features Not Working
- Add `GOOGLE_MAPS_API_KEY` to your `.env` file
- Enable Maps Platform APIs in GCP Console

### Encryption Errors
- Ensure `ENCRYPTION_KEY` is a valid 64-character hex string (32 bytes)
- Generate a new key: `openssl rand -hex 32`

---

## Future Enhancements

1. **Sign Language Full Vocabulary**: Expand from gestures to full ASL/BSL translation
2. **Wearable Integration**: Haptic feedback devices for hazard warnings
3. **Community Hazard Database**: Crowdsourced accessibility information
4. **Multi-language Support**: Global language coverage for OCR and conversation
5. **Real-time Video Processing**: Live camera feed analysis for continuous obstacle detection

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

---

## License

Copyright 2026 Hriday Koppikar

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built as part of Kaggle's **5-Day AI Agents: Intensive Vibe Coding Course with Google**.

Special thanks to:
- Google's Agent Development Kit team
- The accessibility community for feedback and guidance
- Open-source vision and NLP model developers

