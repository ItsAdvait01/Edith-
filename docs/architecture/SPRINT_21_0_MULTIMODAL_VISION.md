# Sprint 21.0 — Multimodal Screen Understanding Subsystem

- **Planner:** Fast-path routes in `Planner` for `analyze screen`, `what's on my screen`, `read my screen`, `inspect screen`, `explain the error on my screen`, and regex patterns matching `explain * screen`, `describe * display`, `what is on my monitor`. LLM prompts pass targeted queries into `parameters={"prompt": ...}`.
- **Executor:** Executes via `PerceptionTool` registered under `perception` in `ToolManager`. Tool accepts injected `LLM` instance.
- **Owner Subsystem:** Perception & Core LLM Subsystems (`src/tools/perception_tool.py`, `src/core/llm.py`).
- **State Updates:** Captures a silent, temporary screenshot to `~/.edith_cache/vision/` using native macOS `screencapture -x`. Passes base64-encoded image to `LLM.ask_vision()`. Guarantees file deletion in `finally` block to prevent disk clutter.
- **ActionResult:** Returns structured `ActionResult` with human-readable summary, raw analysis in `data["analysis"]`, and metadata `{"action": "analyze_screen"}`.

## Features
- **Zero-Clutter Temporary Captures:**
  - Unlike `capture_screen` which saves user screenshots to `~/Desktop`, `analyze_screen` writes to a transient cache folder and auto-deletes immediately upon completion.
- **Universal Multimodal Support (`ask_vision`):**
  - **Local Ollama:** Formats payload with `images` array (compatible with `llava`, `minicpm-v`).
  - **Cloud Endpoints:** Formats OpenAI-compatible vision content payload (`image_url` with data URI).
  - Graceful fallback: If no vision model is installed or call fails, returns a clear explanation rather than raising an unhandled exception.
- **Dual-Channel Output Integration:**
  - Executive verbal summary spoken via Tara / F.R.I.D.A.Y. voice persona.
  - Complete descriptive analysis displayed on screen.
