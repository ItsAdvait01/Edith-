# Sprint 19.0 — System & Hardware Controls Subsystem

- **Planner:** Rule-based fast path in `Planner` for volume controls (`set volume to X%`, `volume up/down`, `mute`/`unmute`), battery status (`battery`, `check battery`), dark mode (`turn on/off dark mode`, `toggle dark mode`, `is dark mode on`), and lock screen (`lock screen`). `AIPlanner` automatically discovers `system` capabilities.
- **Executor:** Executes via `SystemTool` registered under name `system` in `ToolManager`.
- **Owner subsystem:** Tools (System Skill).
- **State updates:** Changes system state directly on macOS through native utilities (`osascript`, `pmset`, `defaults`). Zero internal caching or persistent state duplication.
- **ActionResult:** Returns structured `ActionResult` with human-friendly message and dictionary `data` (e.g. `percentage`, `state`, `source`, `volume`, `muted`, `dark_mode`, `locked`).

## Features
- **Volume & Audio Control:**
  - `set volume to X%`, `volume X` (clamped 0–100)
  - `volume up` (+10%), `volume down` (-10%)
  - `mute`, `unmute`
  - `what is the volume` (returns current level and mute status)
- **Power & Battery Diagnostics:**
  - `check battery`, `battery status`, `battery level`
  - Parses `pmset -g batt` for percentage, charging/discharging state, power source, and time remaining.
- **Appearance & Dark Mode:**
  - `turn on dark mode`, `turn off dark mode`, `toggle dark mode`
  - `is dark mode on` (fast check via `defaults read -g AppleInterfaceStyle`)
- **System Display Lock:**
  - `lock screen`, `lock mac` (executes display sleep via `pmset displaysleepnow`)
- **Resource Footprint:**
  - 0 external dependencies.
  - 0 cloud API calls.
  - Sub-millisecond execution times.
