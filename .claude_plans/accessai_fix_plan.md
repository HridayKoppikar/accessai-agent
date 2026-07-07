# AccessAI Fix Plan (Option A — unified skills, LLM routing, tools-only)

## Decisions locked in
- **Multi-agent wiring: tools-only.** The ADK coordinator agent gets **direct async tool wrappers** around the skills (vision, TTS, navigation, health, sign-language, emergency). No ADK `sub_agents=` transfer gymnastics — the coordinator LLM picks which tool(s) to call. Reliable under the 40 req/min rate limit. Keeps the "4 specialized agent classes" for the rubric/pitch (they still exist as `create_*_agent()` and are exported), but the *demonstrated* orchestration is the coordinator using real tools. (Satisfies "use 3+ of: ADK, MCP, Security, Deployability, Agent skills".)
- **Routing: pure LLM, no keyword lists.** Delete both keyword routers. The coordinator's instruction tells the LLM which tool fits which intent and to call it. `main.py`'s `/api/chat` calls the unified `handle_request()` which uses the same skills (FastAPI path keeps working identically; its router becomes one thin function).
- **Unify both worlds on a shared skill layer (Option A):** ONE async `handle_request(msg, image, profile)` core that calls the skills; the ADK agent gets the *individual skills* as tools; `main.py`'s `/api/chat` calls `handle_request` directly. No divergence.
- **Encryption: keep AES-256, fix the bug only.** Fix PKCS#7 padding validation in `decrypt_data` (validate the padding byte, raise on corruption) — do NOT swap to Fernet / add HMAC / change method. Add `pycryptodomex` to `pyproject.toml` so the encryption demo in TESTING_GUIDE step 7 actually runs.
- **Docs/pitch: minimal change.** Don't rewrite README, README claims, or project description. Only fix factual errors that would embarrass a demo (e.g. `/health` lying). Do NOT add new claims.

## The unified skill layer (new file `app/router.py`)

Single source of truth for calling skills + formatting the user-facing response. Replaces the routing logic in BOTH `conversational_agent.py` and `coordinator.py`.

`app/router.py` exports:
- `handle_request(message, image_base64, user_profile) -> dict` — the full router that the ADK agent's umbrella tool AND main.py's `/api/chat` call. Returns `{type, response, ...}`.
- Thin **async helper functions** that the ADK tool wrappers wrap (one per skill):
  - `do_vision(image, task, user_input)` → wraps `mcp.vision_server.analyze_image`
  - `do_tts(text)` → wraps `skills.transcription_skill.text_to_speech`
  - `do_navigation(destination, mobility_profile, start_location=None)` → wraps `skills.navigation_skill.navigation_guidance_skill`
  - `do_health(user_input, user_profile)` → wraps `skills.health_skill.health_management_skill`
  - `do_sign_language(frames)` → wraps `skills.transcription_skill.sign_language_narrator_skill`
  - `do_emergency(user_input, user_profile)` → wraps `skills.emergency_skill.emergency_alert_skill`

Import path: imports use **`from app.mcp...` / `from app.skills...`** (absolute) so both the ADK runtime (which imports `app.agent`) and `main.py` (which inserts `app/` on path) resolve them. Falls back gracefully if `app.` prefix isn't set (try/except for the `app/`-on-sys.path case `main.py` uses).

## File-by-file changes

### 1. NEW `app/router.py` — unified skill layer
- Move the working logic from `conversational_agent.py` (which already proved vision works) into here, de-keywordized: each branch just calls the right skill and formats. Keep the nice formatted outputs (🚨 / 🧭 / 🏥 emojis etc.) that the chat-demo expects.
- `handle_request` keeps a **single hard-coded emergency safety guard**: if the message round-trips through the emergency skill tool the agent already called, fine; but as a *non-routing* net, `handle_request` itself does NOT keyword-route — it just dispatches to whichever `do_*` is requested. The LLM (agent path) decides; the FastAPI path keeps a thin request→handler. **No keyword classification lists anywhere.**
- Export both `handle_request` and the `do_*` helpers.

### 2. `app/agents/coordinator.py` — fix + wire tools
- Replace `tools=[classify_request_type, process_emergency, merge_responses, update_user_profile, get_user_profile, manage_session_state]` with **real skill tool wrappers** built from `app.router.do_*`. Each wrapper is an `async def` with a clear docstring (so ADK's FunctionTool infers a good schema) calling the corresponding `do_*`.
- Keep `classify_request_type` but make it a *hint* function the LLM MAY call (optional). **Fix its bugs** so `test_classification.py` goes green:
  - Negation block: actually `return 'chat'`-with-context (or skip emergency rules) when a negation matches.
  - Add to emergency keywords: `911`, `fell`, `fallen`, `cannot get up`, `can't get up`, `ambulance`, `stroke`, `heart attack`, `breathing`, `bleeding`.
  - `help!` alone should NOT auto-trigger emergency (test expects `chat`); require an action verb.
- Rewrite the coordinator `instruction` to LLM-routing-style: "Decide which capability the user needs and call the matching tool. Emergency is always highest priority. For 'read this aloud', call text_to_speech. For images, call analyze_image. For directions, call navigation_guidance. For health/food safety, call health_management (and analyze_image first to read a label if an image was provided). For signing, call sign_language." Emphasize: do NOT narrate "routing to X agent" — just call the tool and return the result.
- Remove the dead `process_emergency` (replaced by real `do_emergency`). Keep `update_user_profile`/`get_user_profile`/`manage_session_state` as lightweight tools (harmless, support the pitch).

### 3. NEW `app/agents/coordinator_tools.py` (or keep wrappers inside `coordinator.py`)
- The async tool wrappers (`analyze_image_tool`, `text_to_speech_tool`, `navigation_tool`, `health_tool`, `sign_language_tool`, `emergency_tool`). Each: parse args, call `app.router.do_*`, return formatted string the LLM shows the user.

### 4. `app/agents/perception.py`, `assistant.py`, `safety.py` — fix imports
- Change `from mcp.vision_server import ...` → `from app.mcp.vision_server import ...`; `from skills...` → `from app.skills...`. Keep these agents exported (rubric/pitch: "4 agents") even though the coordinator drives via tools. Optionally give `coordinator` `sub_agents=[...]` purely for documentation/transfer-availability (non-load-bearing; tools do the work).

### 5. `app/skills/transcription_skill.py` — fix sign-language
- Line ~463: `aiplatform.GenerativesModel` → `aiplatform.GenerativeModel` (correct class). Wrap the Vision call so a real gesture is detected.
- When Vertex is genuinely unavailable, the fallback must **honestly** say `"demo_mode"` and return `primary_gesture: 'unknown'` (or `'no_gesture_detected'`) — NOT always `'help'`. Update the demo stub text accordingly. (Keeping "demo mode" is fine; the lie is the bug.)
- TTS already degrades gracefully — leave it.

### 6. `app/skills/navigation_skill.py` — return real directions when possible
- `navigation_guidance_skill` already supports `start_location`; the bug is the agent wrapper passed no start. With LLM routing, the `do_navigation` helper will request `start_location` from the user/caller. Mock fallback stays for the no-API-key demo (fine, but it must be reachable and clearly labeled "demo route" — it already is).
- Also fix `assistant.navigation_instructions`/distance-sort crash risk (defensive `parse_distance`). Minor.

### 7. `app/skills/health_skill.py` — make the food-label/vision handoff real (within chat path)
- `_handle_food_safety_query` currently hardcodes `['almonds','tree nuts','peanut oil']` on keyword match. Keep a sensible default but: when the router/LLM passes an image-derived ingredient list (from OCR via `analyze_image(task='ocr')`), use THAT. Wire `do_health` to optionally OCR an attached image first when the query mentions a food/label.
- This delivers the README's "read label → check allergies" claim.

### 8. `app/security/encryption.py` — fix padding validation (AES-256 only)
- In `decrypt_data`: after slicing padding, **validate** `padding_length ∈ 1..AES_BLOCK_SIZE` and that the last `padding_length` bytes all equal `padding_length` (PKCS#7). Raise `ValueError("Invalid padding / corrupt ciphertext")` otherwise. No algorithm change, no HMAC. This is a correctness bug, not a security uplift.

### 9. `pyproject.toml` — add missing dep
- Add `pycryptodomex>=3.20` to `dependencies` (encryption imports `from Cryptodome...`). Without it, `uv sync` may not install it and the encryption demo/test fails with `ModuleNotFoundError`.

### 10. `app/main.py` — `/api/chat` calls unified router
- Replace `from conversational_agent import chat_with_accessai, process_user_request` with `from app.router import handle_request`. `/api/chat` calls `handle_request(message, image_base64, user_profile)` and returns the dict. Behavior for vision stays identical (vision was already working here). Add `/api/emergency` and `/api/navigation` minimal endpoints (ENHANCED_WEBAPP_PLAN asked for them) wired to `do_emergency`/`do_navigation` so the frontend SOS/nav buttons work.

### 11. `app/conversational_agent.py` — deprecate, keep as thin shim
- Replace its body with `from app.router import handle_request, chat_with_accessai` re-exports (so any external import keeps working). Avoids breaking imports in `main.py`/tests. Or delete its routing and import the shim. **Minimal.**

### 12. `/health` honesty fix (`app/main.py`)
- Report `vision_available` by actually attempting a trivial Vertex probe (or at least checking `_VERTEXAI_AVAILABLE` AND `GOOGLE_CLOUD_PROJECT` AND that the client isn't None), not just the env var. Same for maps. This stops the health check from claiming features are up when they aren't.

## What I'm NOT changing
- README prose / architecture diagram / pitch / project description (your instruction).
- The encryption *method* (keep AES-256 CBC + PBKDF2; only fix the padding bug + add the dep).
- The three MCP servers' tool definitions (`get_*_tools()`) — they're fine and satisfy the MCP rubric.
- The skills' public function signatures (so tests/endpoints that call them keep working).
- `Dockerfile`, `docker-compose.yml`, Cloud Run stuff (no deploy work this pass, per earlier instruction).
- ADK `App`/playground entry (`agent.py` stays; `root_agent` just behaves correctly now).

## Verification (how we know it's fixed)
1. `uv run python test_classification.py` → all 14 pass.
2. `uv run python -c "from app.security.encryption import encrypt_data, decrypt_data; ..."` (TESTING_GUIDE step 7) → Match: True, and corrupt ciphertext now raises.
3. `uv run pytest tests/integration/test_agent.py` → streaming agent returns text content (relies on Vertex or model availability; tolerate if Vertex down).
4. Manual via the unified router: feed `handle_request("Read this aloud: hi", None, {})` → returns TTS-ready string (not just echoed text). `handle_request`-equivalent for "navigate to nearest pharmacy", "emergency", "Is marzipan safe for nut allergy?", "describe this image" → each dispatches to the right skill and returns the formatted skill output.
5. `agents-cli playground` / `tests/integration/test_agent.py` style: the coordinator actually calls a tool rather than narrating "routed to Perception Agent".

## Execution mode (ultracode)
- Implement the file changes in a single cohesive pass (the files are tightly coupled — coordinator imports router imports skills; doing it atomically avoids a broken intermediate state).
- Then run a **Workflow** = adversarial review fan-out: N independent agents re-examine the changed files for correctness (imports resolve under both runtimes, the LLM-routing instruction is sound, padding fix is correct, no keyword-route regressions, marzipan path works, sign-language honesty). Findings → I apply fixes → re-run `test_classification.py` + a router smoke check.
