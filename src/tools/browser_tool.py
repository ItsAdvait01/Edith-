import subprocess
import urllib.parse
from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task

class BrowserTool(BaseTool):
    NAME = "browser"
    DESCRIPTION = "Opens URLs and searches the web in the default browser."
    RESOURCE_PROFILE = "browser"
    SUPPORTED_ACTIONS = frozenset({"open_url", "search"})

    def __init__(self, command_runner=subprocess.run):
        self._command_runner = command_runner

    def can_handle(self, user_input):
        text = user_input.lower()
        return text.startswith("open http") or text.startswith("search ")

    def task_from_legacy_input(self, user_input):
        text = user_input.lower()
        if text.startswith("open http"):
            return Task(tool=self.NAME, action="open_url", target=user_input[5:].strip())
        elif text.startswith("search for "):
            return Task(tool=self.NAME, action="search", target=user_input[11:].strip())
        elif text.startswith("search "):
            return Task(tool=self.NAME, action="search", target=user_input[7:].strip())
        return None

    def execute(self, task):
        if task.action not in self.SUPPORTED_ACTIONS:
            return ActionResult(False, f"Unsupported action: {task.action}", error="unsupported_action")

        target = task.target.strip()
        if not target:
            return ActionResult(False, "Missing target.", error="missing_target")

        url = target
        if task.action == "search":
            query = urllib.parse.quote_plus(target)
            url = f"https://www.google.com/search?q={query}"
        elif task.action == "open_url":
            if not (url.startswith("http://") or url.startswith("https://")):
                return ActionResult(False, "Invalid URL format.", error="invalid_url")

        try:
            self._command_runner(["open", url], check=True)
            message = f"Searching for '{target}'..." if task.action == "search" else f"Opening {url}..."
            return ActionResult(True, message, data={"url": url})
        except Exception as e:
            return ActionResult(False, f"Failed to open browser.", error=str(e))
