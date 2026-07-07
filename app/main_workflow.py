# AccessAI: Multimodal Accessibility Companion
# Main Entry Point - ADK 2.0 Workflow Graph API

"""
AccessAI is a 24/7 personal accessibility assistant that serves both
visually impaired and hearing impaired users through a multi-agent
architecture built with Google's Agent Development Kit (ADK) 2.0.

Track: Agents for Good - Social Impact / Accessibility
"""

from google.adk.agents import Agent
from google.adk.workflow import Workflow, Function, Edge, RequestInput
from google.adk.models import Gemini
from google.genai import types
from app.agents.coordinator import coordinator_agent
from app.agents.perception import perception_agent
from app.agents.assistant import assistant_agent
from app.agents.safety import safety_agent