# Battery-Aware Intelligence & Thermal Protection Subsystem

- **Owner subsystem:** System / Power Subsystem (`src/system/power_manager.py`).
- **Core Purpose:** Protect the fanless MacBook Air M1 from overheating, thermal throttling, and battery drain by adapting AI execution profiles based on real-time hardware telemetry.
- **Planner:** `Planner` recognizes `/power`, `/eco`, `power mode`, `power status`, `check power`, `/eco on`, `/eco off`.
- **Executor:** Integrated into `src/app.py` execution loop and `SystemTool.execute` (`power_profile`, `set_power_profile`).
- **ActionResult:** Returns structured `ActionResult` with human-friendly summary, profile status, and telemetry data.

## Features
- **Power Profiles:**
  - **Performance:** Active when plugged into AC Power. Zero restrictions.
  - **Balanced:** Active when on Battery Power (> 20%). Suppresses redundant speculative AI planning passes for conversational chat, eliminating the double-inference penalty that heats the fanless chassis.
  - **Eco Saver:** Active when battery drops <= 20% or manually toggled via `/eco on`. Suppresses heavy local neural inference passes.
- **Dynamic Speculative Throttling:**
  - On battery, inspects user prompts for action keywords (`open`, `create`, `run`, `delete`, `search`, etc.).
  - Conversational prompts skip the speculative `AIPlanner` pass, cutting CPU load and thermal generation by over 50%.
- **CLI Commands:**
  - `/power` or `/eco`: Display active profile, battery percentage, and thermal optimization status.
  - `/eco on`: Manually enable Eco Saver mode.
  - `/eco off`: Revert to automated power management.
- **Resource Footprint:**
  - 0 external packages.
  - Subprocess telemetry cached for 5 seconds to avoid repeated process spawning.
  - 0% idle CPU overhead.
