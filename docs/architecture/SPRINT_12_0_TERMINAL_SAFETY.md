# Sprint 12.0 - Terminal Skill Safety Design

- **Planner:** The rule-based planner recognizes `run command <command>` and creates one `terminal:execute` task.
- **Executor:** `Executor` receives the task only from `TaskQueue` and routes it through `ToolManager` to `TerminalTool`.
- **Owner subsystem:** Skills owns terminal execution; Security owns explicit confirmation; Interface owns `/confirm <failed-task-position>`.
- **State updates:** `TaskQueue` records the attempt and failure. Explicit confirmation sets `task.parameters["confirmed"] = True`, then requeues the task ahead of dependent pending work.
- **ActionResult:** Includes user-safe output, exit code, stdout/stderr, confirmation requirement, error code, and execution time measured by `ToolManager`.

## Safety policy

- Read-only commands (`pwd`, `ls`, `cat`, `echo`, selected `git` inspection commands) run directly.
- Every other command returns `confirmation_required` before any shell process starts.
- `/failed` shows the stopped task; `/confirm 1` explicitly confirms it and runs the requeued workflow.
- Commands use a 10-second timeout, capture output, do not run in the background, and create no persistent process.
