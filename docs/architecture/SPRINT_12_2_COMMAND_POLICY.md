# Sprint 12.2 — Command Policy Design

- **Planner:** No change. Creates `terminal:execute` tasks as before.
- **Executor:** No change. Consumes from `TaskQueue`.
- **Owner subsystem:** Security owns the policy classification (`CommandPolicy`). Skills owns execution (`TerminalTool`).
- **State updates:** No new state. `CommandPolicy` is stateless — it classifies a command and returns a risk level.
- **ActionResult:** Confirmation messages now include risk level and working directory. Metadata gains `risk_level` and `working_directory` fields.

## Risk levels

| Level | Meaning | Confirmation |
|-------|---------|-------------|
| `none` | Read-only commands (`pwd`, `ls`, `cat`, `git status`, etc.) | Not required |
| `low` | Mild side effects | Required |
| `high` | Significant changes, shell operators, unknown commands | Required |
| `destructive` | Data loss risk (`rm`, `kill`, `shutdown`, etc.) | Required |

## Changes

- `src/security/command_policy.py` — New file. Stateless classifier with `classify()`, `requires_confirmation()`, `format_preview()`.
- `src/tools/terminal_tool.py` — Delegates to `CommandPolicy`, passes `cwd` to `subprocess.run`, includes risk and directory in metadata.
- Shell operator detection unchanged (same regex).
- All existing tests pass without modification.
