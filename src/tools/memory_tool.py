from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task
from memory.memory_store import MemoryStore

class MemoryTool(BaseTool):
    NAME = "memory"
    DESCRIPTION = "Remembers and recalls facts or preferences."
    RESOURCE_PROFILE = "on_demand"
    SUPPORTED_ACTIONS = frozenset({"remember", "recall", "forget"})

    def __init__(self, memory_store=None):
        self.memory_store = memory_store or MemoryStore()

    def can_handle(self, user_input):
        text = user_input.lower()
        return text.startswith("remember ") or text.startswith("recall ") or text.startswith("forget ")

    def task_from_legacy_input(self, user_input):
        text = user_input.lower()
        if text.startswith("remember "):
            parts = user_input[9:].split(" is ", 1)
            if len(parts) == 2:
                return Task(tool=self.NAME, action="remember", target=parts[0].strip(), parameters={"value": parts[1].strip()})
        elif text.startswith("recall "):
            return Task(tool=self.NAME, action="recall", target=user_input[7:].strip())
        elif text.startswith("forget "):
            return Task(tool=self.NAME, action="forget", target=user_input[7:].strip())
        return None

    def execute(self, task):
        if task.action not in self.SUPPORTED_ACTIONS:
            return ActionResult(False, f"Unsupported action: {task.action}", error="unsupported_action")
        
        target = task.target.strip()
        if not target:
            return ActionResult(False, "Missing target key.", error="missing_target")

        if task.action == "remember":
            value = task.parameters.get("value")
            if not value:
                return ActionResult(False, "Missing value to remember.", error="missing_value")
            
            self.memory_store.set(target, value)
            if target.lower() in ["my name", "name"]:
                return ActionResult(True, f"I will remember that your name is {value}.", data={"key": target, "value": value})
            return ActionResult(True, f"I will remember that {target} is {value}.", data={"key": target, "value": value})
        
        elif task.action == "recall":
            value = self.memory_store.get(target)
            if value:
                if target.lower() in ["my name", "name"]:
                    return ActionResult(True, f"Your name is {value}.", data={"key": target, "value": value})
                return ActionResult(True, f"{target} is {value}.", data={"key": target, "value": value})
            else:
                if target.lower() in ["my name", "name"]:
                    return ActionResult(False, "I don't know your name yet. You can tell me by saying 'remember my name is ...'", error="not_found")
                return ActionResult(False, f"I don't remember anything about {target}.", error="not_found")
        
        elif task.action == "forget":
            deleted = self.memory_store.delete(target)
            if deleted:
                return ActionResult(True, f"I have forgotten about {target}.")
            else:
                return ActionResult(False, f"I didn't know anything about {target}.", error="not_found")
