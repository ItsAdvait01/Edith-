# Sprint 14.2 - File Reading Capability Design

- **Planner:** Maps natural language inputs (`read file <filename>` or `read <filename>`) to a `file` task with action `read`.
- **Executor:** Executes via the existing `FileTool`.
- **Owner subsystem:** Skills.
- **State updates:** No state updates (read-only action).
- **ActionResult:** Success with the file contents returned in both the `message` (truncated safely to 500 lines) and `data` (full content, capped at safety boundary).

## Features
- Provides EDITH with the native ability to read local text files without escaping to shell execution.
- Includes a safety truncator (500 lines) to prevent overwhelming the conversational UI or memory buffer when reading exceptionally large files.
