import subprocess
from time import perf_counter

from brain.action_result import ActionResult


class ContextManager:
    """Reads active macOS context only when an interface requests it."""

    _ACTIVE_CONTEXT_SCRIPT = """
tell application \"System Events\"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    try
        set windowTitle to name of front window of frontApp
    on error
        set windowTitle to \"\"
    end try
    return appName & \"|\" & windowTitle
end tell
"""

    def __init__(self, command_runner=subprocess.run):
        self._command_runner = command_runner

    def get_active_context(self):
        """Return the current frontmost application and window, on demand."""
        started_at = perf_counter()

        try:
            completed = self._command_runner(
                ["osascript", "-e", self._ACTIVE_CONTEXT_SCRIPT],
                capture_output=True,
                text=True,
                check=True,
                timeout=1,
            )
            application, _, window_title = completed.stdout.strip().partition("|")
            message = f"Active context: {application}"

            if window_title:
                message += f" - {window_title}"

            return ActionResult(
                success=True,
                message=message,
                data={"application": application, "window_title": window_title},
                execution_time=perf_counter() - started_at,
                metadata={"source": "macos_system_events", "on_demand": True},
            )
        except Exception as error:
            return ActionResult(
                success=False,
                message="Unable to read active macOS context.",
                error=str(error),
                execution_time=perf_counter() - started_at,
                metadata={"source": "macos_system_events", "on_demand": True},
            )

    def get_clipboard(self):
        """Fetch the current text contents of the macOS clipboard."""
        started_at = perf_counter()
        try:
            completed = self._command_runner(
                ["pbpaste"],
                capture_output=True,
                text=True,
                check=True,
                timeout=1,
            )
            return ActionResult(
                success=True,
                message="Clipboard fetched successfully.",
                data={"clipboard": completed.stdout},
                execution_time=perf_counter() - started_at,
                metadata={"source": "macos_pbpaste", "on_demand": True},
            )
        except Exception as error:
            return ActionResult(
                success=False,
                message="Unable to read clipboard.",
                error=str(error),
                execution_time=perf_counter() - started_at,
                metadata={"source": "macos_pbpaste", "on_demand": True},
            )
