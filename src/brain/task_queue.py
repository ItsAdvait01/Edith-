from collections import deque


class TaskQueue:
    """A lightweight FIFO lifecycle manager for structured Tasks.

    The queue intentionally knows nothing about tools or operating-system
    actions. It only orders Tasks and records their execution state.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __init__(self):
        self._pending = deque()
        self._current_task = None
        self.completed_tasks = []
        self.failed_tasks = []
        self.cancelled_tasks = []
        self._attempt_counts = {}

    def enqueue(self, task):
        task.status = self.PENDING
        self._pending.append(task)
        return task

    def dequeue(self):
        if self.is_empty():
            return None

        task = self._pending.popleft()
        task.status = self.RUNNING
        self._current_task = task
        self._attempt_counts[id(task)] = self.attempts(task) + 1
        return task

    def peek(self):
        return self._pending[0] if self._pending else None

    @property
    def pending_tasks(self):
        """An ordered, read-only snapshot for interface controls."""
        return tuple(self._pending)

    def cancel(self, task):
        """Cancel a pending task without interrupting a running skill."""
        try:
            self._pending.remove(task)
        except ValueError:
            return False

        task.status = self.CANCELLED
        self.cancelled_tasks.append(task)
        return True

    def cancel_position(self, position):
        """Cancel a pending task using its one-based queue position."""
        if position < 1 or position > len(self._pending):
            return None

        task = self._pending[position - 1]
        return task if self.cancel(task) else None

    @property
    def failed_task_snapshot(self):
        """A read-only failed-task view for retry controls."""
        return tuple(self.failed_tasks)

    def retry_failed_position(self, position):
        """Return one failed task ahead of later pending work."""
        if position < 1 or position > len(self.failed_tasks):
            return None

        task = self.failed_tasks.pop(position - 1)
        task.status = self.PENDING
        self._pending.appendleft(task)
        return task

    def attempts(self, task):
        return self._attempt_counts.get(id(task), 0)

    def clear(self):
        while self._pending:
            task = self._pending.popleft()
            task.status = self.CANCELLED
            self.cancelled_tasks.append(task)

    def is_empty(self):
        return not self._pending

    def mark_completed(self, task):
        task.status = self.COMPLETED
        self.completed_tasks.append(task)
        self._finish_current_task(task)

    def mark_failed(self, task):
        task.status = self.FAILED
        self.failed_tasks.append(task)
        self._finish_current_task(task)

    def _finish_current_task(self, task):
        if self._current_task is task:
            self._current_task = None
