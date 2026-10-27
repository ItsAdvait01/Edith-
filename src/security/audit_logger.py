import json
from datetime import datetime
from pathlib import Path


class AuditLogger:
    """Security subsystem component for logging executed tasks.
    
    Adheres to EDITH_OS_ENGINEERING_RULES.md (Security subsystem owns auditing).
    Writes an append-only JSONL log of tasks to a local file.
    """

    def __init__(self, log_path="~/.edith_audit.log"):
        self.log_path = Path(log_path).expanduser()

    def log_task(self, task, action_result):
        """Record the outcome of a task execution."""
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": task.tool,
            "action": task.action,
            "target": task.target,
            "parameters": task.parameters,
            "success": action_result.success,
            "error": action_result.error,
            "execution_time_ms": round(action_result.execution_time * 1000, 2),
            "metadata": action_result.metadata
        }

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            # Audit logging must not crash the main execution loop if the disk is full/unwritable
            pass
