# Text-to-Speech (TTS) Skill

## How to handle "read this aloud" requests

When the user says:
- "Read this aloud: <text>" / "Say: <text>" / "Speak: <text>"
- "Read it out loud"
- any variant of "read" + "aloud" targeting specific text

## Flow

1. **Call the tool immediately.** Do NOT echo the text first or pause —
   `text_to_speech_for_user(text_to_read=<the exact text between colons or quotes>)`.
2. The tool generates audio output (speech synthesis). If Google Cloud TTS
   is installed and authenticated, the audio data is ready for playback; if
   not, the tool returns a clear setup message.
3. Relay the tool's response — it tells the user whether audio was generated
   or what needs to be configured.

## Extracting the text to read

- "Read this aloud: AccessAI helps visually impaired people" → text = everything after the colon
- "Say: Hello" → text = "Hello"
- Strip quotation marks if present.
- If no specific text is identified, use the entire user message (minus the
  "read aloud" command prefix).