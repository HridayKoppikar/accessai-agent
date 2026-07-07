# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# =============================================================================
# AccessAI Dockerfile
# Supports both local development and Cloud Run deployment
# =============================================================================

FROM python:3.11-slim

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /app

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock* ./

# Install all dependencies including dev
RUN uv sync --frozen

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8080

# Expose port for Cloud Run / local development
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Build arguments for versioning
ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Run the FastAPI application (used by Cloud Run)
CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]

# =============================================================================
# Alternative: Run the ADK agent directly for playground mode
# =============================================================================
# CMD ["uv", "run", "python", "-m", "app.agent"]