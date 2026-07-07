"""
DEPRECATED shim — kept so external imports of this module keep working.

All real logic now lives in `app/router.py`.  This file exists only to
re-export the router functions under their old names.

DEPRECATION NOTE:
  Use `from app.router import handle_request, chat_with_accessai, do_*`
  instead of `from conversational_agent import ...`.  This shim will be
  removed in a future version.
"""

# Re-export the router's public surface under the legacy module path.
from app.router import (
    handle_request,
    chat_with_accessai,
    do_vision,
    do_tts,
    do_navigation,
    do_health,
    do_sign_language,
    do_emergency,
)

# Legacy alias: process_user_request was the old name for handle_request.
process_user_request = handle_request


__all__ = [
    "handle_request",
    "chat_with_accessai",
    "process_user_request",  # legacy alias
    "do_vision",
    "do_tts",
    "do_navigation",
    "do_health",
    "do_sign_language",
    "do_emergency",
]