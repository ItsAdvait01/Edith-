# Sprint 12.1 — Natural-Language Confirmation Design

- **Planner:** `Planner.is_confirmation()` recognizes exact confirmation phrases (`yes`, `y`, `confirm`). No fuzzy matching.
- **Executor:** No change. Consumes from `TaskQueue` via `execute_all()`.
- **Owner subsystem:** Security owns the confirmation staging slot via `ConfirmationManager`. Interface owns the input check and rendering.
- **State updates:** `ConfirmationManager` holds at most one staged task. The task enters staging when its execution returns `error="confirmation_required"`. It leaves staging on explicit confirm (natural language or `/confirm`) or on any non-confirmation input (stale cancellation). No persistence, no thread, no polling.
- **ActionResult:** Unchanged. A confirmed task returns its normal execution result through the existing skill.

## Safety invariants

- Only exact, whole-input phrases (`yes`, `y`, `confirm`) trigger confirmation.
- Confirmation applies only when exactly one task is staged.
- Any other input cancels the staged task, preventing stale confirmations from being accidentally triggered later.
- `/confirm 1` continues to work exactly as before (backward compatible).
