# Sprint 18.0 — Voice Output & Smart Output Router

## Feature: Voice Output

- Planner: N/A (output-layer feature, wraps existing responses)
- Executor: VoiceEngine (macOS native `say` command)
- Owner subsystem: Voice
- State updates: `voice_state["enabled"]` boolean toggled by `/voice on` and `/voice off`
- ActionResult: N/A — output wrapper, not a skill

## Components

### VoiceEngine (`src/voice/voice_engine.py`)

macOS native text-to-speech engine using the built-in `say` command.

- `speak(text)` — Non-blocking speech via `subprocess.Popen`
- `speak_sync(text)` — Blocking speech for short notices
- `stop()` — Kill active speech process
- `_sanitize(text)` — Strip code fences, markdown formatting, and syntax characters
- Default voice: Samantha (en_US), rate: 190 wpm

### OutputRouter (`src/voice/output_router.py`)

Smart classifier that decides whether EDITH should speak a response or display it.

- `classify(text) → "speak" | "display"`
  - Code blocks (```) → display
  - Indented code (4+ spaces, 3+ lines) → display
  - Markdown tables (`|---|`) → display
  - Numbered lists (10+ items) → display
  - Long text (>500 chars) → display
  - Everything else → speak
- `get_spoken_notice(text)` — Brief verbal notice for display-mode responses
  - e.g. "I've written the python code on your screen."

### CLI Controls

- `/voice on` — Enable spoken responses
- `/voice off` — Disable spoken responses
- `/voice` — Show current voice status

## Tests

10 new automated tests added:
- OutputRouter classification (code, table, short text, long text, empty)
- OutputRouter spoken notices (code language detection, table notice)
- VoiceEngine sanitization (code fences, markdown stripping)
- VoiceEngine subprocess invocation (mocked)

Total: **78 tests passing**.
