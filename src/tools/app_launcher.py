import subprocess

from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task


class AppController(BaseTool):

    NAME = "app"
    DESCRIPTION = "Opens supported macOS applications."
    RESOURCE_PROFILE = "operating_system"
    SUPPORTED_ACTIONS = frozenset({"open"})

    APPS = {
        "chrome": "Google Chrome",
        "google chrome": "Google Chrome",
        "vscode": "Visual Studio Code",
        "vs code": "Visual Studio Code",
        "visual studio code": "Visual Studio Code",
        "finder": "Finder",
        "terminal": "Terminal",
        "spotify": "Spotify",
        "safari": "Safari",
        "notes": "Notes",
        "calendar": "Calendar"
    }

    def can_handle(self, user_input):

        return user_input.lower().startswith("open ")

    def task_from_legacy_input(self, user_input):

        return Task(tool=self.NAME, action="open", target=user_input[5:].strip())

    def execute(self, task):

        if task.action != "open":
            return ActionResult(
                success=False,
                message=f"The app tool cannot {task.action}.",
                error="unsupported_action",
            )

        app = task.target.strip().lower()

        if app not in self.APPS:
            return ActionResult(
                success=False,
                message=f"I don't know how to open '{app}'.",
                error="unknown_app",
            )

        try:

            subprocess.run(
                ["open", "-a", self.APPS[app]],
                check=True
            )

            return ActionResult(
                success=True,
                message=f"Opening {self.APPS[app]}...",
                data={"application": self.APPS[app]},
            )

        except Exception as e:

            return ActionResult(
                success=False,
                message=f"Failed to open {self.APPS[app]}.",
                error=str(e),
            )

# Backward-compatible name for existing imports.
AppLauncher = AppController
