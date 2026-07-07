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
AccessAI - Multimodal Accessibility Companion
Main Application Module

A 24/7 personal accessibility assistant for visually and hearing impaired users,
built with Google's Agent Development Kit (ADK) 2.0.
"""

from .agent import app

__all__ = ["app"]