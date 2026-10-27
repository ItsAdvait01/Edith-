# Sprint 14.3 - Multi-Target File Operations Design

- **Planner:** Enhances the `delete`, `create file`, and `create folder` natural language mappings to accept lists of items (e.g. separated by `,` or `and`).
- **Executor:** Unchanged. The executor simply runs the resulting array of tasks in FIFO order.
- **Owner subsystem:** Brain.
- **State updates:** Enqueues multiple sequential file modification tasks.
- **ActionResult:** Each task returns its own success/failure `ActionResult`.

## Features
- Allows users to issue single natural language commands that fan out into multiple deterministic execution steps (e.g., "create file src/main.py, src/app.py and README.md").
- Reuses the existing `_split_targets` string parser originally introduced for the app launcher.
- Keeps execution atomic. A failure on file B correctly pauses the queue, leaving file C as pending for review or cancellation per existing EDITH Executor rules.
