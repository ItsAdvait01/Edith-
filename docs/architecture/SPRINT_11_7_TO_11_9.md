# Sprints 11.7-11.9 Design Record

## 11.7 - Rule-Based Project Workflow

- **Planner:** `Planner` recognizes `create Python project [called] <name>`.
- **Executor:** Existing `Executor` consumes the ordered file tasks through `TaskQueue`.
- **Owner subsystem:** Brain owns the rule; Skills owns the file operations.
- **State updates:** `TaskQueue` records each task lifecycle; the file system receives the ordered folder/file changes.
- **ActionResult:** Existing `FileTool` returns the success/failure, created path, and execution metadata.

The workflow is deliberately small: create a project folder, `README.md`, and `main.py`. It is rule-based and does not add LLM planning.

## 11.8 - Manual Retry and Recovery

- **Planner:** No planning change.
- **Executor:** Stops after a failed task by default, preserving later pending work.
- **Owner subsystem:** Brain / `TaskQueue` owns lifecycle and retry state.
- **State updates:** The queue tracks attempt counts, failed tasks, and requeued tasks in memory only.
- **ActionResult:** The original skill result remains the source of failure details; a successful retry returns its own result.

The CLI exposes `/failed` and `/retry <position>`. Retries are manual: no loop, polling, thread, or background retry exists.

## 11.9 - On-Demand macOS Context

- **Planner:** No planning change yet.
- **Executor:** Not applicable; the Interface explicitly requests Context.
- **Owner subsystem:** Context.
- **State updates:** No persistence. A snapshot is read only when `/context` is used, then released.
- **ActionResult:** Contains active application/window data, a user-safe message, measured time, and an error if macOS access is unavailable.

`ContextManager` invokes macOS `System Events` once per explicit request. It creates no watcher, thread, polling loop, or resident service.
