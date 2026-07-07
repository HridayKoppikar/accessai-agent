# AccessAI: Technologies Used

A reference of every technology, framework, API, and library used in this project,
with the role it plays and any setup requirements.

---

## Core Agent Framework

### Google Agent Development Kit (ADK) 2.3.0
- **Package:** `google-adk[gcp]>=2.0.0,<3.0.0`
- **Role:** Powers the multi-agent system. The coordinator `Agent` receives user
  messages, loads per-skill instructions from `.md` files, and calls async tool
  wrappers that invoke the skill layer.
- **Why ADK:** Provides the agent runtime, session management, streaming
  (`/run_sse`), tool-calling abstraction (`FunctionTool`), and Cloud Run
  deployment scaffolding.
- **Entry point:** `app/agent.py` exposes `root_agent = create_coordinator_agent()`.
  `agents-cli playground` loads this agent for interactive testing.
- **Model:** `gemini-2.5-flash` via `Gemini(model="gemini-2.5-flash")`. Multimodal —
  can see attached images directly without calling a tool.

---

## AI Models & APIs

### Gemini 2.5 Flash
- **Access:** Via Vertex AI (preferred, GCP quotas) or Google AI API.
- **Env vars:** `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`,
  `GOOGLE_GENAI_USE_VERTEXAI=true`
- **Role:** Core reasoning model for the coordinator agent. Multimodal — handles
  text and images natively in the ADK playground chat.
- **Rate limit note:** GCP Vertex AI has per-project quotas; the coordinator
  is built with **tools-only routing** (no redundant LLM calls) to minimise usage.

### Google Cloud Text-to-Speech (TTS) API
- **Package:** `google-cloud-texttospeech>=2.37.0`
- **Role:** Converts text to spoken audio (MP3) for visually impaired users.
  Neural2 voice family (`en-US-Neural2-C/F/J`).
- **Setup:**
  ```bash
  gcloud auth application-default login
  gcloud services enable texttospeech.googleapis.com
  ```
- **Graceful degradation:** If not configured, `text_to_speech()` returns a clear
  "setup required" message rather than crashing.

### Google Cloud Speech-to-Text (STT) API
- **Package:** `google-cloud-speech` (included in `google-adk[gcp]`)
- **Role:** Transcribes spoken audio to text for hearing impaired users.
- **Setup:** Same as TTS — `gcloud auth application-default login` covers both.

### Vertex AI Vision
- **Access:** `GOOGLE_CLOUD_PROJECT` + `GOOGLE_GENAI_USE_VERTEXAI=true`
- **Role:** OCR, object detection, sign-language analysis in the FastAPI camera
  app (`POST /api/analyze-image`). Used for:
  - `task='describe'` — accessibility-focused scene description.
  - `task='ocr'` — text extraction from labels/signs.
  - `task='detect_objects'` — obstacle and object identification.
  - `task='sign_language'` — sign gesture detection.
- **In the ADK playground:** Gemini has native multimodal vision — it describes
  images directly without calling `analyze_image_for_user`. The tool is reserved
  for OCR and specialized sign-language batch analysis.

### Google Maps Platform
- **Package:** `googlemaps>=4.10.0`
- **Env var:** `GOOGLE_MAPS_API_KEY`
- **APIs used:**
  | API | Function |
  |-----|----------|
  | Maps JavaScript | Frontend camera/chat UI |
  | Directions API | Turn-by-turn walking routes |
  | Places API | Find nearby accessible locations |
  | Geocoding API | Resolve destination names to lat/lng |

---

## Web Framework

### FastAPI
- **Package:** `fastapi>=0.104.0`, served by `uvicorn>=0.24.0`
- **Role:** REST API server for the camera frontend and programmatic access.
  All `/api/*` endpoints live here.
- **Key endpoints:** `/health`, `/api/chat`, `/api/analyze-image`,
  `/api/emergency`, `/api/navigation`, `/api/transcribe-text-to-speech`,
  `/api/transcribe-speech-to-text`, `/api/detect-sign-language`
- **CORS:** Enabled for all origins (`allow_origins=["*"]`) — lock down for prod.

### Uvicorn
- **Role:** ASGI server. Runs with `reload=True` in development.
- **Command:** `uv run python -m app.main` (starts on `0.0.0.0:8080`)

---

## Security

### PyCryptodomeX
- **Package:** `pycryptodomex>=3.20.0`
- **Role:** AES-256-CBC encryption of health data at rest in
  `app/security/encryption.py`.
- **Algorithm:** PBKDF2 key derivation (100,000 iterations, SHA-256),
  random IV per encryption, PKCS#7 padding, base64 encoding.
- **Key env var:** `ENCRYPTION_KEY` (64-char hex = 32 bytes for AES-256).
  Generate with: `openssl rand -hex 32`
- **Why pycryptodomex (not pycryptodome):** The project uses the standalone
  `Cryptodome.Cipher.AES` namespace; `pycryptodome` installs as `Crypto`, while
  `pycryptodomex` installs as `Cryptodome` (matching the import in `encryption.py`).

---

## Python Package Management

### uv
- **Tool:** Astral's Rust-based package manager (`uv sync`, `uv run`, `uv add`).
- **Lock file:** `uv.lock` — committed to repo.
- **Role:** Reproducible installs, fast resolution, dependency management.
- **Key commands:**
  ```bash
  uv sync          # Install all deps from lockfile
  uv add <pkg>     # Add a package and update lockfile
  uv run pytest    # Run tests
  uv run python -m app.main  # Start the server
  ```

---

## Infrastructure & Deployment

### Docker
- **Files:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- **Role:** Containerised deployment. Non-root user (`appuser`), health-check
  endpoint, Cloud Run compatibility.
- **Build:**
  ```bash
  docker build -t accessai:latest .
  docker run -p 8080:8080 --env-file .env accessai:latest
  docker-compose up --build
  ```

### Google Cloud Run
- **Role:** Serverless container hosting. AccessAI is stateless (no database
  session storage — uses `InMemorySessionService`) and Cloud Run is the
  primary deployment target.
- **Command:**
  ```bash
  gcloud run deploy accessai --source . --allow-unauthenticated
  ```
- **See also:** `docs/CLOUD_RUN_DEPLOYMENT.md` for step-by-step guide.

### GCP Secret Manager
- **Recommended for:** `GOOGLE_MAPS_API_KEY`, `ENCRYPTION_KEY`, `GOOGLE_CLOUD_PROJECT`
- **Not implemented in this version** (uses `.env` files locally), but the
  `app/utils/secrets.py` module has `SecretManager` class with GCP Secret Manager
  fallback support ready for production migration.

### Google Cloud Logging
- **Package:** `google-cloud-logging>=3.12.0`
- **Role:** Structured audit logging to Cloud Logging. Logs via `logging_client.logger`.

### OpenTelemetry + Google GenAI Instrumentation
- **Package:** `opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0`
- **Role:** Traces GenAI API calls for observability. Set up in `app_utils/telemetry.py`.

---

## Testing

### pytest
- **Packages:** `pytest>=9.0.2`, `pytest-asyncio>=1.0.0`, `nest-asyncio>=1.6.0`
- **Files:**
  - `test_classification.py` — 14-case unit test for emergency/health/nav/perception
    classification (all currently passing).
  - `tests/integration/test_agent.py` — ADK agent streaming test (verifies
    coordinator returns text content via `Runner`).
  - `tests/integration/test_server_e2e.py` — FastAPI server test (requires
    `app.fast_api_app:app` on port 8000).
- **Run:**
  ```bash
  uv run pytest tests/ -v
  uv run python test_classification.py
  ```

---

## Configuration Reference

| Env Var | Required | Role |
|---------|----------|------|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project for Vertex AI + Maps |
| `GOOGLE_CLOUD_LOCATION` | Yes | Region, e.g. `asia-south1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Yes | Enable Vertex AI (set to `true`) |
| `GOOGLE_MAPS_API_KEY` | For navigation | Google Maps/Directions/Places/Geocoding |
| `EMERGENCY_CONTACT_EMAIL` | Recommended | Alert recipient |
| `EMERGENCY_CONTACT_PHONE` | Recommended | SMS alert recipient |
| `ENCRYPTION_KEY` | For encryption | 64-char hex key for AES-256 |
| `TTS_VOICE` | Optional | e.g. `en-US-Neural2-F` |
| `TTS_SPEED` | Optional | e.g. `1.0` |

---

## Environment Setup

```bash
# 1. Clone and cd in
cd accessai-agent

# 2. Install dependencies
uv sync

# 3. Copy and fill .env
cp .env.example .env
# Edit .env with your values (see table above)

# 4. Authenticate with Google Cloud
gcloud auth application-default login
gcloud services enable vertexai.googleapis.com \
  generativelanguage.googleapis.com \
  texttospeech.googleapis.com \
  speech.googleapis.com \
  maps-backend.googleapis.com

# 5. Start server
uv run python -m app.main

# 6. Open playground (ADK chat)
agents-cli playground
```