from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain.action_result import ActionResult
    from brain.task import Task


class BaseTool(ABC):
    """Base contract for all EDITH skills.

    Structured execution is the primary API. The text-related methods exist
    only so ToolManager.process() can support older callers during migration.
    """

    NAME = ""
    DESCRIPTION = ""
    RESOURCE_PROFILE = "on_demand"
    SUPPORTED_ACTIONS = frozenset()

    def metadata(self):
        """Return discovery data without invoking the skill."""
        return {
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "resource_profile": self.RESOURCE_PROFILE,
            "supported_actions": tuple(sorted(self.SUPPORTED_ACTIONS)),
        }

    @abstractmethod
    def can_handle(self, user_input):
        pass

    @abstractmethod
    def task_from_legacy_input(self, user_input):
        """Convert legacy text into one Task at the system boundary."""
        return None

    @abstractmethod
    def execute(self, task: "Task") -> "ActionResult":
        pass
