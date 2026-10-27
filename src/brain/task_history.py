from datetime import datetime


class TaskHistory:
    """Lightweight in-memory history of completed and failed tasks.

    Stores a bounded list of task outcomes for review.
    """

    def __init__(self, max_size=100):
        self.max_size = max_size
        self._entries = []

    def record(self, task, result):
        entry = {
            "task": f"{task.tool}:{task.action} {task.target}".strip(),
            "success": result.success,
            "message": result.message,
            "error": result.error,
            "execution_time": result.execution_time,
            "timestamp": datetime.now().isoformat()
        }
        self._entries.append(entry)
        
        if len(self._entries) > self.max_size:
            self._entries.pop(0)

    @property
    def entries(self):
        """Return a read-only list of all history entries."""
        return list(self._entries)

    def clear(self):
        self._entries.clear()
