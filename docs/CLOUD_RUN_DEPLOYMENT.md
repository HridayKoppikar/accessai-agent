# Cloud Run Deployment Guide

Step-by-step instructions to deploy AccessAI to Google Cloud Run.

---

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed (`gcloud` CLI)
- A Google Cloud project with billing enabled
- Docker (optional — Cloud Run can build from source)
- `GOOGLE_CLOUD_PROJECT` noted

---

## Step 1: Set Your Project

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

---

## Step 2: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  texttospeech.googleapis.com \
  speech.googleapis.com \
  aiplatform.googleapis.com \
  generativelanguage.googleapis.com \
  maps-backend.googleapis.com \
  places.googleapis.com \
  cloudlogging.googleapis.com
```

Or via the Cloud Console:
https://console.cloud.google.com/apis/library

---

## Step 3: Store Secrets in Secret Manager (Recommended)

Instead of `.env` files, store secrets in GCP Secret Manager for production security.

```bash
# Create secrets
gcloud secrets create ENCRYPTION_KEY --data-file=- <<< "$(openssl rand -hex 32)"
gcloud secrets create GOOGLE_MAPS_API_KEY --data-file=- <<< "YOUR_MAPS_API_KEY"
gcloud secrets create GOOGLE_CLOUD_PROJECT --data-file=- <<< "YOUR_PROJECT_ID"

# Grant Cloud Run service account access
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 4: Build and Deploy

### Option A: Direct source deploy (recommended for this project)

Cloud Run builds from source — no Dockerfile needed:

```bash
gcloud run deploy accessai \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=asia-south1" \
  --set-env-vars="TTS_SPEED=1.0" \
  --set-secrets="ENCRYPTION_KEY=ENCRYPTION_KEY:latest" \
  --set-secrets="GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest" \
  --set-secrets="GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest" \
  --timeout=60s \
  --memory=512Mi \
  --cpu=1"
```

> **Note:** If deploying from Windows, ensure line endings are LF not CRLF,
> or pass `--no-crlf` to avoid build errors.

### Option B: Docker build locally

```bash
cd accessai-agent

# Build
docker build -t gcr.io/YOUR_PROJECT_ID/accessai:latest .

# Push to Artifact Registry
docker push gcr.io/YOUR_PROJECT_ID/accessai:latest

# Deploy
gcloud run deploy accessai \
  --image gcr.io/YOUR_PROJECT_ID/accessai:latest \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=asia-south1" \
  --set-secrets="ENCRYPTION_KEY=ENCRYPTION_KEY:latest" \
  --set-secrets="GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest" \
  --set-secrets="GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest" \
  --timeout=60s \
  --memory=512Mi \
  --cpu=1
```

---

## Step 5: Verify the Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe accessai \
  --platform managed \
  --region asia-south1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health check
curl "${SERVICE_URL}/health"

# Test chat endpoint
curl -X POST "${SERVICE_URL}/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "emergency - I have fallen and cannot get up"}'
```

Expected health response:
```json
{
  "status": "healthy",
  "service": "AccessAI Camera Server",
  "features": {
    "vision_available": true,
    "maps_available": true,
    "transcription_available": true
  }
}
```

---

## Step 6: (Optional) Set Up a Custom Domain

```bash
# Map a custom domain to the Cloud Run service
gcloud run domain-mappings create \
  --service accessai \
  --domain accessai.your-domain.com \
  --region asia-south1

# Add the DNS record shown in the output to your DNS provider
```

You'll need to add an A record or CNAME in your domain registrar pointing to the
IP address output by the command.

---

## Step 7: Environment Variables Reference

| Variable | Source | Example |
|----------|--------|---------|
| `GOOGLE_CLOUD_PROJECT` | Secret Manager | `gen-lang-client-0354994829` |
| `GOOGLE_CLOUD_LOCATION` | Hardcoded / env | `asia-south1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Hardcoded / env | `true` |
| `GOOGLE_MAPS_API_KEY` | Secret Manager | `AIzaSy...` |
| `ENCRYPTION_KEY` | Secret Manager | `3c7da14c...` (64-char hex) |
| `EMERGENCY_CONTACT_EMAIL` | Secret Manager | `emergency@example.com` |
| `EMERGENCY_CONTACT_PHONE` | Secret Manager | `+1234567890` |
| `TTS_VOICE` | Env (optional) | `en-US-Neural2-F` |
| `TTS_SPEED` | Env (optional) | `1.0` |

---

## Step 8: Update After Code Changes

```bash
# Rebuild and redeploy
gcloud run deploy accessai \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=asia-south1" \
  --set-secrets="ENCRYPTION_KEY=ENCRYPTION_KEY:latest" \
  --set-secrets="GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest" \
  --set-secrets="GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest" \
  --timeout=60s \
  --memory=512Mi \
  --cpu=1
```

Cloud Run builds the new image, replaces the old container, and keeps the same URL.

---

## Troubleshooting

### Vertex AI not available
```bash
# Verify authentication
gcloud auth application-default login

# Check project
gcloud config get-value project

# Enable Vertex AI API
gcloud services enable vertexai.googleapis.com
```

### Maps features not working
- Ensure `GOOGLE_MAPS_API_KEY` is set and the Maps API is enabled in your project.
- Check the Maps API has no usage restrictions that block your domain/server IPs.

### Container fails to start
```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=accessai" --limit=50
```

### Cold start latency
- Increase memory to 1GiB: `--memory=1Gi`
- Set minimum instances to avoid cold starts:
  ```bash
  gcloud run services update accessai \
    --region asia-south1 \
    --min-instances=1
  ```

### CORS errors in frontend
The server is configured with `allow_origins=["*"]` for development.
For production, restrict to your domain:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## CI/CD with Cloud Build (Optional)

For automatic deploys on push to `main`, create `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/accessai:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/accessai:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'accessai'
      - '--image'
      - 'gcr.io/$PROJECT_ID/accessai:$COMMIT_SHA'
      - '--platform'
      - 'managed'
      - '--region'
      - 'asia-south1'
      - '--allow-unauthenticated'
      - '--set-secrets=ENCRYPTION_KEY=ENCRYPTION_KEY:latest,GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest'

images:
  - 'gcr.io/$PROJECT_ID/accessai:$COMMIT_SHA'
```