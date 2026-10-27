import os
import subprocess

from brain.action_result import ActionResult
from brain.task import Task
from security.command_policy import CommandPolicy
from tools.base_tool import BaseTool


class TerminalTool(BaseTool):
    """Runs an explicitly planned shell command with a conservative safety gate."""

    NAME = "terminal"
    DESCRIPTION = "Runs an explicitly confirmed local shell command."
    RESOURCE_PROFILE = "operating_system"
    SUPPORTED_ACTIONS = frozenset({"execute"})

    def __init__(self, command_runner=subprocess.run, policy=None,
                 working_directory=None):
        self._command_runner = command_runner
        self._policy = policy or CommandPolicy()
        self._working_directory = working_directory

    def can_handle(self, user_input):
        return user_input.lower().startswith("run command ")

    def task_from_legacy_input(self, user_input):
        return Task(
            tool=self.NAME,
            action="execute",
            target=user_input[12:].strip(),
        )

    def execute(self, task):
        if task.action != "execute":
            return ActionResult(
                success=False,
                message=f"The terminal tool cannot {task.action}.",
                error="unsupported_action",
            )

        command = task.target.strip()

        if not command:
            return ActionResult(False, "Command missing.", error="missing_command")

        cwd = self._working_directory or os.getcwd()
        risk = self._policy.classify(command)
        needs_confirmation = self._policy.requires_confirmation(command)

        if needs_confirmation and not task.parameters.get("confirmed"):
            preview = self._policy.format_preview(command, risk, cwd)
            return ActionResult(
                success=False,
                message=preview,
                data={"command": command},
                error="confirmation_required",
                metadata={
                    "requires_confirmation": True,
                    "risk_level": risk,
                    "working_directory": cwd,
                },
            )

        try:
            completed = self._command_runner(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return ActionResult(
                success=False,
                message="Command timed out after 10 seconds.",
                data={"command": command},
                error="command_timeout",
            )
        except Exception as error:
            return ActionResult(
                success=False,
                message="Unable to start the command.",
                data={"command": command},
                error=str(error),
            )

        output = self._command_output(completed.stdout, completed.stderr)
        success = completed.returncode == 0

        return ActionResult(
            success=success,
            message=output or ("Command completed." if success else "Command failed."),
            data={
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            error=None if success else "command_failed",
            metadata={
                "requires_confirmation": needs_confirmation,
                "risk_level": risk,
                "working_directory": cwd,
            },
        )

    @staticmethod
    def _command_output(stdout, stderr):
        output = (stdout or stderr or "").strip()
        return output[:4000]
