# EDITH OS — Antigravity Development Context

You are continuing development of **EDITH OS**, a modular local personal AI assistant on a single-user MacBook Air M1 (8 GB RAM).

**Project path:** `/Users/satyawanambre/Edith`

---

## Critical Principles

- **Do not rewrite working code.** Extend the architecture while preserving compatibility where practical.
- **Local-first, lightweight, event-driven, battery-efficient.** Do not add unnecessary background threads, polling loops, databases, brokers, or cloud dependencies.

---

## Required Reading (before any implementation)

Read these documents first for full context:

- `README.md`
- `docs/architecture/EDITH_OS_ENGINEERING_RULES.md`
- `docs/architecture/SPRINT_11_7_TO_11_9.md`
- `docs/architecture/SPRINT_12_0_TERMINAL_SAFETY.md`

---

## Current Architecture

```
User → Planner → TaskQueue → Executor → ToolManager → Skills → macOS
```

### Core Components

| File | Role |
|------|------|
| `src/brain/task.py` | Structured task object |
| `src/brain/action_result.py` | Structured execution result |
| `src/brain/planner.py` | Rule-based planner (no AI planning yet) |
| `src/brain/task_queue.py` | FIFO task queue using `deque` |
| `src/brain/executor.py` | Consumes tasks from TaskQueue |
| `src/tools/tool_manager.py` | Dispatches tasks to skills by `task.tool` |
| `src/tools/base_tool.py` | Base class for all skills |

### Current Skills

| Skill | NAME | File |
|-------|------|------|
| Calculator | `calculator` | `src/tools/` |
| DateTimeTool | `datetime` | `src/tools/` |
| FileTool | `file` | `src/tools/` |
| AppController | `app` | `src/tools/` |
| TerminalTool | `terminal` | `src/tools/terminal_tool.py` |
| SystemTool | `system` | `src/tools/system_tool.py` |
| NotificationTool | `notification` | `src/tools/notification_tool.py` |

### Skill Contracts

Every skill:
- Receives a structured `Task`.
- Returns `ActionResult`, never a raw string.
- Declares `NAME`, `DESCRIPTION`, `RESOURCE_PROFILE`, and `SUPPORTED_ACTIONS`.
- Does not print directly.

### ActionResult Fields

```
success, message, data, error, execution_time, metadata
```

### ToolManager

Dispatches structured tasks using `task.tool`, measures execution time, and exposes:
```python
get_capabilities()
get_skill_metadata(name)
```

### TaskQueue Behavior

- FIFO queue using `deque`.
- States: `pending`, `running`, `completed`, `failed`, `cancelled`.
- Supports: enqueue, dequeue, peek, cancel, clear, retry failed task, attempt counting, queue-position cancellation.
- Executor consumes only from TaskQueue.
- Executor stops on task failure by default and preserves later tasks as pending.
- Retried failed tasks return to the front of the queue so dependencies remain ordered.

---

## Supported Input Examples

```
open chrome and vscode
create folder AI
create file main.py
create Python project called VisionAI
run command pwd
```

`create Python project called VisionAI` creates this ordered workflow:
```
create folder VisionAI
create file VisionAI/README.md
create file VisionAI/main.py
```

---

## CLI Queue Controls

```
/queue          — show current queue
/cancel 1       — cancel task at position 1
/clear-queue    — clear entire queue
/failed         — list failed tasks
/retry 1        — retry failed task 1
/confirm 1      — confirm a blocked task
/context        — show on-demand macOS context
```

---

## Sprint 11.9 — Context Foundation

- `src/context/context_manager.py`
- Uses macOS `System Events` only on explicit `/context`.
- No persistent watcher, polling, thread, or background service.
- May require Accessibility/Automation permission on macOS.
- Live context access returning a structured failure when `System Events` access is unavailable is **expected behavior**.

---

## Sprint 12.0 — Terminal Safety

- `src/tools/terminal_tool.py`
- Planner recognizes `run command <shell command>`.
- **Read-only commands** (`pwd`, `ls`, `cat`, `echo`, `which`, `python --version`, `git status`, `git log`, `git diff`) run directly.
- **State-changing commands** require explicit confirmation.
- **Shell operators** (`;`, `|`, `&`, redirects, `$`, backticks, parentheses, newlines) always require confirmation, even if a command starts with a read-only prefix.
- A blocked task returns `ActionResult(error="confirmation_required")`, becomes failed, and appears under `/failed`.
- To execute: `/confirm 1`.

### Manual Test Reference

```
run command mkdir /tmp/edith-terminal-demo
```
correctly required confirmation. Inputs like `yes run` are not valid commands — they are treated as ordinary chat text. Correct flow:
```
/failed
/confirm 1
run command ls -ld /tmp/edith-terminal-demo
```

---

## Sprint 12.1 — Natural-Language Confirmation

- `src/security/confirmation_manager.py` extended with staging slot.
- `Planner.is_confirmation()` recognizes exact phrases: `yes`, `y`, `confirm`.
- When a task returns `confirmation_required`, it is auto-staged in `ConfirmationManager`.
- Typing "yes" confirms **only** the staged task. Any other input cancels the staged task.
- `/confirm 1` still works (backward compatible).
- No fuzzy matching, no partial matching, no substring matching.

---

## Sprint 12.2 — Command Policy

- `src/security/command_policy.py` — Stateless classifier with four risk levels: `none`, `low`, `high`, `destructive`.
- `TerminalTool` delegates to `CommandPolicy` instead of a hardcoded allowlist.
- Commands run in a controlled working directory (`cwd` passed to `subprocess.run`).
- Confirmation preview now shows risk level and working directory.
- `ActionResult.metadata` includes `risk_level` and `working_directory`.
- Read-only prefix list and shell-operator detection unchanged.

---

## Testing

```bash
cd /Users/satyawanambre/Edith
source venv/bin/activate
python -m unittest discover -s tests -v
```

## Sprint 12.3 — Task History

- `src/brain/task_history.py` — In-memory TaskHistory class stores execution outcomes of the last 100 tasks.
- `Executor` captures `ActionResult`s automatically on completion or failure.
- `/history` command added to CLI to view previous actions and their statuses.

---

## Sprint 13.0 — Browser Skill

- `src/tools/browser_tool.py` — BrowserTool maps structured commands to `open <url>` in macOS.
- `Planner` now supports `open http...` and `search <query>`.
- Searches use Google by default and auto-encode queries.

---

## Sprint 13.1 — Context-Aware Planning

- `src/brain/planner.py` uses `ContextManager` to dynamically replace the pronoun `this` with the active macOS window title or application name.
- Planner supports `open <target> in <app>` parsing.
- Ensures explicit user confirmation is preserved by sending resulting shell commands (`open -a`) through `TerminalTool`.

---

## Sprint 13.2 — Memory Subsystem Foundation

- `src/memory/memory_store.py` establishes the foundational Memory subsystem.
- Lightweight, local, in-memory dictionary keeps session state without persistence layers.
- `src/tools/memory_tool.py` manages `remember`, `recall`, and `forget` actions.
- `Planner` accepts `remember X is Y`, `recall X`, and `forget X`.

## Sprint 14.0 — Durable Memory

- `src/memory/memory_store.py` upgraded to save to and load from `~/.edith_memory.json`.
- Memory is now persistent across EDITH sessions without requiring external databases.

---

## Sprint 14.1 — Perception Subsystem

- `src/tools/perception_tool.py` establishes the Perception subsystem using macOS `screencapture`.
- `Planner` accepts `take screenshot` and `capture screen` to generate a screenshot saved to `~/Desktop`.

---

## Sprint 14.2 — File Reading Capability

- `src/tools/file_tool.py` supports a `read` action for text files with a 500-line safety cap.
- `Planner` parses `read file <filename>` into a structured file tool task.

---

## Sprint 14.3 — Multi-Target File Operations

- `src/brain/planner.py` uses `_split_targets` for file creation, folder creation, and deletions.
- Converts commands like `delete file X and Y` into multiple sequential enqueued tasks.

---

## Sprint 16.0–16.2 — AI-Powered Brain

- `src/brain/ai_planner.py` — `AIPlanner` uses gemma3:4b via Ollama to parse any natural language into validated `Task` objects.
- Layered architecture: Rule-based planner (instant) → AI planner (LLM, ~1-2s) → Chat fallback.
- System prompt is dynamically built from registered skill capabilities.
- Validates all LLM-generated tasks: rejects hallucinated tools and invalid actions.
- Non-streaming Ollama call with 10-second timeout. No retries (avoids loops).
- Ollama failures are silent — falls through to normal chat.

---

## Sprint 17.0 — Universal Cloud API

- `src/core/llm.py` refactored into a universal adapter supporting local Ollama and OpenAI-compatible REST endpoints.
- Settings driven by environment variables (`EDITH_AI_PROVIDER`, `EDITH_CLOUD_KEY`, etc.).
- Allows seamless switching to cloud models (OpenAI, Groq, DeepSeek) while preserving local-first defaults.
- Added `ask_stream()` for live chat and `ask_sync()` for structured JSON planning.

---

## Sprint 18.0 — Voice Output & Smart Output Router

- `src/voice/voice_engine.py` — macOS native TTS engine using the built-in `say` command (0 dependencies, 0 extra RAM).
- `src/voice/output_router.py` — Smart classifier: code/tables/long text → display on screen; conversational text → speak aloud.
- Non-blocking speech via `subprocess.Popen` so EDITH stays responsive while talking.
- CLI controls: `/voice on`, `/voice off`, `/voice`.
- Voice defaults to OFF; user opts in explicitly.

---

## Sprint 18.1 — JARVIS Voice Upgrade & Dual-Channel Output

- `src/voice/voice_personality.py` — Configured with **F.R.I.D.A.Y.** tactical persona (warm, loyal, direct, addresses user as Boss/name, "Systems green and ready to roll", witty cues like "Say no more", "Got you, Boss").
- `src/voice/voice_engine.py` paired with native macOS **Tara** (Indian English female) voice at original speech pace (190 WPM default, 215 WPM snappy cues, 175 WPM safety prompts).
- `src/voice/output_router.py` upgraded with **Dual-Channel Synthesis**: extracts 1–2 sentence executive verbal summaries before code/tables, keeping full code on screen while speaking the thesis aloud.
- Integrated with `MemoryStore` to remember the user's name ("Your name is {name}").
- Intelligent code explanations: step-by-step for multi-step code, full for short code, simple for tricky code, always closing with an interactive follow-up check.
- **Dynamic Tone Shifting & Humor**: Auto-shifts between casual/friendly (witty, modern slang like "no sweat", "gotchu", "piece of cake", F.R.I.D.A.Y. humor) when chatting, and sharp, tactical, formal mode when handling critical code, system tasks, or safety authorizations.

---

## Sprint 19.0 — System & Hardware Controls

- `src/tools/system_tool.py` — `SystemTool` inspects and controls macOS volume, battery diagnostics, system appearance (dark mode), and display locking.
- Fast-path deterministic parsing in `Planner` for `set volume <N>%`, `volume up/down`, `mute`/`unmute`, `check battery`, `toggle dark mode`, `is dark mode on`, `lock screen`.
- Dynamically discovered by `AIPlanner` via `ToolManager.get_capabilities()`.
- Uses native macOS utilities (`osascript`, `pmset`, `defaults`). Zero cloud, zero external dependencies.
- Structured `ActionResult` returns with human-readable status and rich typed data dictionaries.

---

## Sprint 20.0 — Native Reminders, Timers & Notifications

- `src/tools/notification_tool.py` — `NotificationTool` handles native macOS banner alerts, non-blocking countdown timers, and spoken reminder alerts.
- Fast-path deterministic parsing in `Planner` for `remind me in X minutes to Y`, `set a timer for X minutes`, `notify me X`, `/timers`, `/cancel-timer <id>`.
- Non-blocking callback: fires macOS desktop banner and speaks aloud through F.R.I.D.A.Y. voice persona when `/voice on` is active.
- Pure event-driven implementation using `threading.Timer`. Zero external dependencies, 0% idle CPU.

---

## Battery-Aware Intelligence & Thermal Protection

- `src/system/power_manager.py` — `PowerManager` dynamically adapts execution profiles based on macOS battery and power telemetry.
- Prevents overheating on the fanless MacBook Air M1 by eliminating redundant speculative AI planning passes on battery.
- Three power profiles: `Performance` (AC Power), `Balanced` (Battery Aware), `Eco Saver` (Low Battery / Manual).
- CLI commands: `/power`, `/eco`, `/eco on`, `/eco off`.
- Telemetry cached for 5 seconds to eliminate process spawning overhead.

---

## Sprint 21.0 — Multimodal Screen Understanding

- `src/tools/perception_tool.py` — `PerceptionTool` upgraded with `analyze_screen` action.
  - Captures a temporary screenshot to `~/.edith_cache/vision/` (does **not** clutter Desktop).
  - Base64-encodes the PNG and passes it to `LLM.ask_vision()` with a structured F.R.I.D.A.Y. vision prompt.
  - Temp file is cleaned up automatically after analysis.
  - If no vision-capable LLM is available, returns a graceful human-readable fallback message.
- `src/core/llm.py` — `ask_vision(prompt, image_path)` added to `LLM`.
  - **Ollama**: sends image via `images` list in the messages payload (compatible with `llava`, `minicpm-v`).
  - **Cloud**: sends image via OpenAI vision content-array (`image_url` with inline base64 data URI).
  - Returns plain-text analysis. Never raises — all errors returned as strings.
- `src/tools/tool_manager.py` — Accepts `llm=` kwarg and injects it into `PerceptionTool`.
- `src/brain/planner.py` — Fast-path routes for:
  - `analyze screen` / `analyse screen`
  - `what's on my screen` / `what is on my screen`
  - `read my screen` / `inspect screen`
  - `explain the error on my screen` / `explain error on screen`
  - Pattern-matched phrases: `explain * screen`, `describe * display`, `what is on my monitor`
- `src/app.py`:
  - Passes `llm=brain` into `ToolManager` to connect the LLM to the vision path.
  - Removes old OS-context-only handler for `what's on my screen` — now routed to vision.
  - Vision analysis output goes through the `OutputRouter` dual-channel path (spoken executive summary + full text on screen).

---

## Sprint 21.1 — Adaptive Output & Situational Awareness

- `src/voice/output_router.py` — `OutputRouter` upgraded with multi-channel classifier (`speak`, `card`, `code`, `table`, `display`).
  - Unicode box-drawing card renderer with zero extra dependencies.
  - `OutputRouter.render_for_mode(mode, action_result, response_text)` dynamically adapts to:
    - **Driving**: Short voice-only summary of 2-3 points, no screen card clutter, randomized hands-free voice follow-up ("Want me to navigate to the first one?").
    - **At a desk**: Timeline / rich cards with action hints (`↳ Ask a follow-up anytime`) + spoken executive summary.
    - **In a meeting**: Silent mode (`📌 Compact one-line text`), voice output suppressed.
    - **Default**: Adaptive smart-selection (card for structured results, speak for conversational text).
- `src/context/situation_detector.py` — `SituationDetector` manages situational output modes (`default`, `driving`, `meeting`, `desk`).
- `src/app.py`:
  - CLI control via `/mode`, `/mode driving`, `/mode desk`, `/mode meeting`, `/mode default`, and natural aliases ("i am driving").
  - Seamless execution loop output dispatching via `render_for_mode`.

---

## Testing

```bash
cd /Users/satyawanambre/Edith
source venv/bin/activate
python -m unittest discover -s tests -v
```

**Status:** 117 automated tests passing after Adaptive Output & Situational Awareness (Sprint 21.1).

---

## Recommended Future Roadmap

| Sprint | Focus | Summary |
|--------|-------|---------|
| 13.0 ✅ | Browser skill foundation | Structured browser skill behind the same Task, ActionResult, TaskQueue, confirmation, and metadata contracts. |
| 13.1 ✅ | Context-aware planning | Use on-demand Context subsystem to resolve phrases like "open this in VS Code"; preserve explicit confirmation for consequential actions. |
| 13.2 ✅ | Memory Subsystem Foundation | Local, lightweight session-state memory via `MemoryStore` and `MemoryTool` with basic `remember`/`recall` planner bindings. |
| 14.0 ✅ | Durable Memory | Persist the memory store to a local JSON file (`~/.edith_memory.json`) so facts survive restarts. |
| 14.1 ✅ | Perception Subsystem | Establish Perception foundation with a Screen Capture skill mapping to native macOS `screencapture`. |
| 14.2 ✅ | File Reading Capability | Expand `FileTool` and `Planner` to read text files directly with output safety truncation. |
| 14.3 ✅ | Multi-Target File Ops | Allow Planner to split commands like `delete A and B` into distinct queue items. |
| 15.0 ✅ | System Auditing | `AuditLogger` records all completed tasks and their outcomes to `~/.edith_audit.log`. |
| 15.1 ✅ | Clipboard Awareness | `ContextManager` can securely read the clipboard, allowing `clipboard` as a natural-language alias. |
| 15.2 ✅ | Visible Task Status | `app.py` execution loop streams live queue progression (⚙️ / ✅) instead of freezing. |
| 16.0–16.2 ✅ | AI-Powered Brain | `AIPlanner` uses gemma3:4b via Ollama to parse any natural language into validated Tasks; rule-based planner preserved as fast path. |
| 17.0 ✅ | Universal Cloud API | Universal adapter supporting local Ollama and OpenAI-compatible REST endpoints. |
| 18.0 ✅ | Voice Output & Smart Router | macOS native TTS engine (`say`) and OutputRouter classifier. |
| 18.1 ✅ | F.R.I.D.A.Y. Voice Persona | Tara voice, Dual-Channel output, tone shifting, theory audio explanations. |
| 19.0 ✅ | System & Hardware Controls | Volume get/set/mute, battery diagnostics, dark mode, screen lock. |
| 20.0 ✅ | Native Reminders & Timers | Native macOS banners, countdown timers, spoken voice alerts, `/timers`. |
| 20.1 ✅ | Battery-Aware Intelligence | Dynamic power profiling, speculative AI throttling, fanless M1 thermal protection, `/power`, `/eco`. |
| 21.0 ✅ | Multimodal Screen Understanding | `PerceptionTool.analyze_screen` — captures a temp screenshot, passes it to `LLM.ask_vision()`, returns spoken + on-screen analysis. Compatible with Ollama vision models (llava) and cloud vision APIs. |
| 21.1 ✅ | Adaptive & Situational Output | `OutputRouter.render_for_mode` & `SituationDetector` supporting Driving, Meeting, Desk, and Default adaptive profiles. |
| 22.0 ⏳ | Proactive System & Event Watchers | Low battery / thermal warning hooks, startup daily briefing (battery, active timers, clipboard summary). |
| 23.0 ⏳ | Voice Input (Speech-to-Text) | Hands-free / push-to-talk voice input via native macOS Dictation or local whisper.cpp. |

---

## Five Required Architecture Questions

Before implementing **any** feature, answer these:

1. **Who plans it?**
2. **Who executes it?**
3. **Which subsystem owns it?**
4. **How is state updated?**
5. **What ActionResult is returned?**
