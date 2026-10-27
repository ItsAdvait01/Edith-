from time import perf_counter

from brain.action_result import ActionResult
from tools.calculator import Calculator
from tools.datetime_tool import DateTimeTool
from tools.file_tool import FileTool
from tools.app_launcher import AppController
from tools.terminal_tool import TerminalTool
from tools.browser_tool import BrowserTool
from tools.memory_tool import MemoryTool
from tools.perception_tool import PerceptionTool
from tools.system_tool import SystemTool
from tools.notification_tool import NotificationTool


class ToolManager:

    def __init__(self, memory_store=None, voice_engine=None, llm=None):

        self.tools = [
            Calculator(),
            DateTimeTool(),
            FileTool(),
            AppController(),
            TerminalTool(),
            BrowserTool(),
            MemoryTool(memory_store=memory_store),
            PerceptionTool(llm=llm),
            SystemTool(),
            NotificationTool(voice_engine=voice_engine),
        ]

        self.tools_by_name = {tool.NAME: tool for tool in self.tools}
        self._validate_skill_registry()

    def get_capabilities(self):
        """Expose installed skill metadata without executing a skill."""
        return [tool.metadata() for tool in self.tools]

    def get_skill_metadata(self, name):
        """Return one skill's metadata, or None when it is not installed."""
        tool = self.tools_by_name.get(name)
        return tool.metadata() if tool is not None else None

    def _validate_skill_registry(self):
        if len(self.tools_by_name) != len(self.tools):
            raise ValueError("Every skill NAME must be unique.")

        required_fields = ("NAME", "DESCRIPTION", "RESOURCE_PROFILE", "SUPPORTED_ACTIONS")

        for tool in self.tools:
            missing_fields = [field for field in required_fields if not getattr(tool, field)]

            if missing_fields:
                missing = ", ".join(missing_fields)
                raise ValueError(f"Skill {tool.__class__.__name__} is missing metadata: {missing}")

    def process(self, user_input):

        for tool in self.tools:

            if tool.can_handle(user_input):
                task = tool.task_from_legacy_input(user_input)

                if task is not None:
                    return self.execute(task)

        return None

    def execute(self, task):
        """Execute a structured planner task without reparsing text."""
        tool = self.tools_by_name.get(task.tool)

        if tool is None:
            return ActionResult(
                success=False,
                message=f"No tool is registered for '{task.tool}'.",
                error="unknown_tool",
            )

        started_at = perf_counter()

        try:
            result = tool.execute(task)
            result.execution_time = perf_counter() - started_at
            return result
        except Exception as error:
            return ActionResult(
                success=False,
                message=f"Failed to execute {task.tool}:{task.action}.",
                error=str(error),
                execution_time=perf_counter() - started_at,
            )
