# Sprint 13.1 - Context-Aware Planning Design

- **Planner:** Planner resolves the pronoun `this` by querying `ContextManager.get_active_context()`. Also supports mapping `open <target> in <app>` to `terminal:execute` tasks.
- **Executor:** No change.
- **Owner subsystem:** Brain (Planner) and Context.
- **State updates:** No new persistent state.
- **ActionResult:** The new task executes via `TerminalTool`, maintaining the existing structured execution and explicit confirmation safeguards for consequential shell commands (like `open -a`).

## Features
- The `Planner` can now optionally accept a `ContextManager`.
- If the word `this` appears in the user input, the Planner fetches the frontmost macOS window title (or application name) and replaces the word `this` with it before generating tasks.
- A new rule in the Planner converts inputs like "open Edith in VS Code" into a shell command `open -a "VS Code" "Edith"`.
- Because this relies on a shell command, the existing CommandPolicy kicks in, properly triggering user confirmation as intended by the safety design.
