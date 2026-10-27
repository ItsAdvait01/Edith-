from datetime import datetime
from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task


class DateTimeTool(BaseTool):

    NAME = "datetime"
    DESCRIPTION = "Returns the current local date or time."
    RESOURCE_PROFILE = "on_demand"
    SUPPORTED_ACTIONS = frozenset({"get_date", "get_time"})

    def can_handle(self, text):

        text = text.lower()

        return "time" in text or "date" in text

    def task_from_legacy_input(self, text):

        text = text.lower()

        if "time" in text:
            return Task(tool=self.NAME, action="get_time")

        if "date" in text:
            return Task(tool=self.NAME, action="get_date")

        return None

    def execute(self, task):

        if task.action == "get_time":
            value = datetime.now().strftime("%I:%M:%S %p")
            return ActionResult(True, value, data={"time": value})

        if task.action == "get_date":
            value = datetime.now().strftime("%d %B %Y")
            return ActionResult(True, value, data={"date": value})

        return ActionResult(
            success=False,
            message=f"The datetime tool cannot {task.action}.",
            error="unsupported_action",
        )
