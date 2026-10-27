from pathlib import Path

from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task


class FileTool(BaseTool):

    NAME = "file"
    DESCRIPTION = "Creates, lists, deletes, and reads local files and folders."
    RESOURCE_PROFILE = "file_system"
    SUPPORTED_ACTIONS = frozenset({"create_file", "create_folder", "delete", "list", "read"})

    def can_handle(self, user_input):

        text = user_input.lower()

        keywords = [
            "create folder",
            "create file",
            "list",
            "delete",
            "read file",
            "read"
        ]

        return any(keyword in text for keyword in keywords)

    def task_from_legacy_input(self, user_input):

        text = user_input.lower()

        if text.startswith("create folder"):
            return Task(self.NAME, "create_folder", user_input[13:].strip())

        if text.startswith("create file"):
            return Task(self.NAME, "create_file", user_input[11:].strip())

        if text.startswith("list"):
            return Task(self.NAME, "list", user_input[4:].strip() or ".")

        if text.startswith("delete"):
            return Task(self.NAME, "delete", user_input[6:].strip())

        if text.startswith("read file "):
            return Task(self.NAME, "read", user_input[10:].strip())

        if text.startswith("read "):
            return Task(self.NAME, "read", user_input[5:].strip())

        return None

    def execute(self, task):

        target = task.target.strip()

        if task.action == "create_folder":
            if not target:
                return ActionResult(False, "Folder name missing.", error="missing_target")

            path = Path(target)
            path.mkdir(exist_ok=True)
            return ActionResult(
                success=True,
                message=f"Folder '{target}' created successfully.",
                data={"path": str(path)},
                metadata={"action": task.action},
            )

        if task.action == "create_file":
            if not target:
                return ActionResult(False, "File name missing.", error="missing_target")

            path = Path(target)
            path.touch(exist_ok=True)
            return ActionResult(
                success=True,
                message=f"File '{target}' created successfully.",
                data={"path": str(path)},
                metadata={"action": task.action},
            )

        if task.action == "list":
            path = Path(target or ".")

            if not path.exists():
                return ActionResult(False, "Folder not found.", error="path_not_found")

            files = [item.name for item in path.iterdir()]
            return ActionResult(
                success=True,
                message="\n".join(files) if files else "Folder is empty.",
                data={"files": files, "path": str(path)},
                metadata={"action": task.action},
            )

        if task.action == "read":
            if not target:
                return ActionResult(False, "File name missing.", error="missing_target")

            path = Path(target)

            if not path.exists():
                return ActionResult(False, "File not found.", error="path_not_found")

            if path.is_dir():
                return ActionResult(False, f"'{target}' is a directory. Cannot read as a file.", error="is_directory")

            try:
                with open(path, "r") as f:
                    # Read up to the first 500 lines to prevent memory/UI flooding
                    lines = []
                    for _ in range(500):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    
                    content = "".join(lines)
                    message = content
                    if f.readline():
                        message += "\n... [output truncated]"
                
                return ActionResult(
                    success=True,
                    message=message,
                    data={"path": str(path), "content": content},
                    metadata={"action": task.action},
                )
            except Exception as e:
                return ActionResult(False, f"Failed to read file: {e}", error="read_failed")

        if task.action == "delete":
            if not target:
                return ActionResult(False, "File name missing.", error="missing_target")

            path = Path(target)

            if not path.exists():
                return ActionResult(False, "File not found.", error="path_not_found")

            if path.is_dir():
                return ActionResult(
                    False,
                    "Deleting folders is disabled.",
                    error="directory_deletion_disabled",
                )

            path.unlink()
            return ActionResult(
                success=True,
                message=f"{target} deleted.",
                data={"path": str(path)},
                metadata={"action": task.action},
            )

        return ActionResult(
            success=False,
            message=f"The file tool cannot {task.action}.",
            error="unsupported_action",
        )
