# Sprint 20.0 — Native Reminders, Timers & Notifications Subsystem

- **Planner:** Rule-based fast path in `Planner` for reminders (`remind me in X minutes to Y`), timers (`set a timer for X minutes`, `timer for X seconds`), notifications (`notify me X`), and queue management (`/timers`, `/cancel-timer <id>`). `AIPlanner` automatically discovers `notification` tool capabilities.
- **Executor:** Executes via `NotificationTool` registered under name `notification` in `ToolManager`.
- **Owner subsystem:** Tools (Notification Skill).
- **State updates:** Event-driven in-memory tracker using non-blocking `threading.Timer`. When a timer fires, dispatches native macOS notification banner via `osascript` and speaks the alert aloud if `VoiceEngine` is configured.
- **ActionResult:** Returns structured `ActionResult` with human-friendly message and dictionary `data` (e.g. `timer_id`, `seconds`, `duration`, `message`).

## Features
- **Native macOS Notifications:**
  - `notify me <message>`: Dispatches instant macOS banner alert with sound.
- **Countdown Timers & Reminders:**
  - `set a timer for 25 minutes (Pomodoro)`
  - `remind me in 15 minutes to commit my changes`
  - Non-blocking callback: fires macOS desktop banner and speaks aloud through F.R.I.D.A.Y. voice persona.
- **Timer Management:**
  - `/timers`: List active timers with remaining time countdowns.
  - `/cancel-timer <ID>`: Cancel an active timer cleanly.
- **Resource Footprint:**
  - 0 external dependencies (no third-party notification packages).
  - 0 polling threads or persistent background daemons.
  - 0% idle CPU overhead.
