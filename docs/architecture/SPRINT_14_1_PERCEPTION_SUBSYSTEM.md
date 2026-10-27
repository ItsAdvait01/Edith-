# Sprint 14.1 - Perception Subsystem Design

- **Planner:** Planner maps natural language inputs (`take screenshot` or `capture screen`) to a `perception` task with action `capture_screen`.
- **Executor:** Executes via the new `PerceptionTool`.
- **Owner subsystem:** Perception.
- **State updates:** Writes a `.png` file representing the captured screenshot to the user's Desktop directory.
- **ActionResult:** Success with the absolute file path of the captured screenshot in `data`.

## Features
- Implements the foundational layer of the EDITH Perception Subsystem based on `EDITH_OS_ENGINEERING_RULES.md`.
- Provides a new `PerceptionTool` allowing the assistant to capture screenshots locally.
- Leverages macOS's native `screencapture` utility via standard subprocess execution.
