from tools.tool_manager import ToolManager


class Executor:

    def __init__(self, task_queue, tool_manager=None, task_history=None, audit_logger=None):

        self.task_queue = task_queue
        self.tool_manager = tool_manager or ToolManager()
        self.task_history = task_history
        self.audit_logger = audit_logger

    def execute_next(self):
        """Execute one pending task from the queue."""
        task = self.task_queue.dequeue()

        if task is None:
            return None

        result = self.tool_manager.execute(task)

        if result.success:
            self.task_queue.mark_completed(task)
        else:
            self.task_queue.mark_failed(task)
            
        if self.task_history is not None:
            self.task_history.record(task, result)

        if self.audit_logger is not None:
            self.audit_logger.log_task(task, result)

        return result

    def execute_all(self, stop_on_failure=True):
        """Drain the FIFO queue, optionally preserving pending work after failure."""

        results = []

        while not self.task_queue.is_empty():
            result = self.execute_next()
            results.append(result)

            if stop_on_failure and not result.success:
                break

        return results
