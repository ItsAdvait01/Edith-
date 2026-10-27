import subprocess
from pathlib import Path
from datetime import datetime

from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task

# Temp cache directory for vision captures — doesn't clutter Desktop
_CACHE_DIR = Path.home() / ".edith_cache" / "vision"


class PerceptionTool(BaseTool):

    NAME = "perception"
    DESCRIPTION = (
        "Captures and analyses the screen. "
        "capture_screen saves a screenshot to the Desktop. "
        "analyze_screen captures a temporary screenshot and describes what is visible, "
        "explains errors, and answers questions about screen content using AI vision."
    )
    RESOURCE_PROFILE = "device"
    SUPPORTED_ACTIONS = frozenset({"capture_screen", "analyze_screen"})

    # Default vision prompt — callers can override via task.parameters["prompt"]
    _DEFAULT_VISION_PROMPT = (
        "You are EDITH, an AI assistant with vision. "
        "Look at this screenshot and describe clearly: "
        "1) What application or content is on screen. "
        "2) Any visible errors, warnings, or important status messages. "
        "3) A concise summary of what the user appears to be working on. "
        "Keep your response direct and practical."
    )

    def __init__(self, save_dir="~/Desktop", llm=None):
        self.save_dir = Path(save_dir).expanduser()
        self._llm = llm  # injected LLM instance (optional — graceful fallback if None)

    def can_handle(self, user_input):
        text = user_input.lower()
        return (
            "capture screen" in text
            or "screenshot" in text
            or "analyze screen" in text
            or "analyse screen" in text
            or "what's on my screen" in text
            or "what is on my screen" in text
            or "explain the error on my screen" in text
            or "read my screen" in text
            or "inspect screen" in text
        )

    def task_from_legacy_input(self, user_input):
        text = user_input.lower()
        if (
            "analyze" in text
            or "analyse" in text
            or "what" in text
            or "explain" in text
            or "read" in text
            or "inspect" in text
        ):
            return Task(tool=self.NAME, action="analyze_screen")
        return Task(tool=self.NAME, action="capture_screen")

    def execute(self, task):
        if task.action == "capture_screen":
            return self._capture_to_desktop()
        elif task.action == "analyze_screen":
            return self._analyze(task.parameters.get("prompt", self._DEFAULT_VISION_PROMPT))
        else:
            return ActionResult(
                success=False,
                message=f"The perception tool cannot handle action: {task.action}.",
                error="unsupported_action",
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _capture_to_desktop(self):
        """Original Sprint 14.1 behaviour — save screenshot to Desktop."""
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"EDITH_Screenshot_{timestamp}.png"
            filepath = self.save_dir / filename

            subprocess.run(["screencapture", str(filepath)], check=True)

            return ActionResult(
                success=True,
                message=f"Screenshot saved to {filepath}",
                data={"path": str(filepath)},
                metadata={"action": "capture_screen"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message="Failed to capture screen.",
                error=str(e),
            )

    def _analyze(self, prompt):
        """Sprint 21.0 — capture a temp screenshot, run vision analysis, clean up."""
        # Ensure cache directory exists
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return ActionResult(
                success=False,
                message="Could not create vision cache directory.",
                error=str(e),
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = _CACHE_DIR / f"vision_{timestamp}.png"

        # Step 1: Capture
        try:
            subprocess.run(["screencapture", "-x", str(temp_path)], check=True)
        except Exception as e:
            return ActionResult(
                success=False,
                message="Screen capture for vision analysis failed.",
                error=str(e),
            )

        # Step 2: Analyse
        analysis = None
        try:
            if self._llm is not None:
                analysis = self._llm.ask_vision(prompt, str(temp_path))
            else:
                analysis = (
                    "Vision model is not available right now. "
                    "Screenshot was captured but could not be analysed. "
                    "Make sure a vision-capable model (e.g. llava or a cloud vision provider) "
                    "is configured."
                )
        except Exception as e:
            analysis = f"Vision analysis failed: {e}"
        finally:
            # Step 3: Clean up temp file
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        return ActionResult(
            success=True,
            message=analysis,
            data={"analysis": analysis},
            metadata={"action": "analyze_screen"},
        )
