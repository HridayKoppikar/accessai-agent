# ruff: noqa
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

"""
AccessAI - Main Application Entry Point

Multi-agent accessibility companion built with Google ADK 2.0.

Architecture:
- Coordinator Agent: Routes requests, manages state, handles priorities
- Perception Agent: Visual processing, OCR, sign language detection
- Assistant Agent: Conversation, health management, navigation
- Safety Agent: Hazard detection, emergency alerts

Model: gemini-2.5-flash (text), gemini-2.5-flash (vision)
"""

import os
from google.adk.apps import App
from app.agents.coordinator import create_coordinator_agent

# Model configuration
DEFAULT_MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-flash"


# Create root coordinator agent (orchestrates all specialized agents)
root_agent = create_coordinator_agent()

# Create app instance
app = App(
    root_agent=root_agent,
    name="app",
)


# Export for workflow composition
__all__ = ['app', 'root_agent']