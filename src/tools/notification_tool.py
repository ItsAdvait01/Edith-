import re
import time
import threading
import subprocess
from datetime import datetime
from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task


class NotificationTool(BaseTool):
    """Dispatches native macOS notifications, countdown timers, and spoken reminders."""

    NAME = "notification"
    DESCRIPTION = "Dispatches native macOS notifications, countdown timers, and spoken reminders."
    RESOURCE_PROFILE = "on_demand"
    SUPPORTED_ACTIONS = frozenset({
        "notify",
        "set_timer",
        "list_timers",
        "cancel_timer",
    })

    def __init__(self, voice_engine=None):
        self.voice_engine = voice_engine
        self._timers = {}  # timer_id -> dict(timer=threading.Timer, message=str, end_time=float, created_at=str)
        self._lock = threading.Lock()
        self._next_id = 1

    def can_handle(self, user_input):
        text = user_input.strip().lower()
        triggers = ["remind me", "timer", "notify", "notification"]
        return any(t in text for t in triggers)

    def task_from_legacy_input(self, user_input):
        text = user_input.strip().lower()
        if "timers" in text or text == "list timers":
            return Task(tool=self.NAME, action="list_timers")
        if text.startswith("notify"):
            msg = user_input[6:].strip()
            return Task(tool=self.NAME, action="notify", parameters={"message": msg})
        return None

    def execute(self, task: Task) -> ActionResult:
        action = task.action
        if action not in self.SUPPORTED_ACTIONS:
            return ActionResult(
                success=False,
                message=f"Notification tool does not support action '{action}'.",
                error="unsupported_action",
            )

        if action == "notify":
            return self._notify(task)
        elif action == "set_timer":
            return self._set_timer(task)
        elif action == "list_timers":
            return self._list_timers()
        elif action == "cancel_timer":
            return self._cancel_timer(task)

        return ActionResult(success=False, message="Unhandled notification action.", error="unhandled_action")

    # ------------------------------------------------------------------
    # Notification Actions
    # ------------------------------------------------------------------

    def _notify(self, task: Task) -> ActionResult:
        message = task.parameters.get("message") or task.target or "Alert from EDITH"
        title = task.parameters.get("title", "EDITH")
        sound = task.parameters.get("sound", "Glass")

        try:
            self._send_macos_notification(title, message, sound)
            return ActionResult(
                success=True,
                message=f"Notification sent: {message}",
                data={"title": title, "message": message, "sound": sound},
                metadata={"action": "notify"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to display notification: {e}",
                error=str(e),
            )

    def _set_timer(self, task: Task) -> ActionResult:
        seconds = task.parameters.get("seconds")
        if seconds is None:
            # Fallback parse from target or duration string
            target = str(task.target or "")
            match = re.search(r"(\d+(?:\.\d+)?)\s*(s|sec|seconds?|m|min|mins|minutes?|h|hr|hours?)?", target, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                unit = (match.group(2) or "m").lower()
                if unit.startswith("s"):
                    seconds = val
                elif unit.startswith("h"):
                    seconds = val * 3600
                else:
                    seconds = val * 60

        if seconds is None or seconds <= 0:
            return ActionResult(
                success=False,
                message="Timer duration must be greater than 0 seconds.",
                error="invalid_duration",
            )

        message = task.parameters.get("message") or task.target or "Time is up!"
        title = task.parameters.get("title", "EDITH Timer")

        duration_str = self._format_duration(seconds)

        with self._lock:
            timer_id = self._next_id
            self._next_id += 1

            timer_obj = threading.Timer(
                seconds,
                self._on_timer_fire,
                args=[timer_id, title, message],
            )
            timer_obj.daemon = True

            self._timers[timer_id] = {
                "timer": timer_obj,
                "message": message,
                "title": title,
                "duration_seconds": seconds,
                "end_time": time.time() + seconds,
                "created_at": datetime.now().strftime("%H:%M:%S"),
            }
            timer_obj.start()

        return ActionResult(
            success=True,
            message=f"Timer set for {duration_str}: {message} (Timer #{timer_id})",
            data={
                "timer_id": timer_id,
                "seconds": seconds,
                "duration": duration_str,
                "message": message,
            },
            metadata={"action": "set_timer"},
        )

    def _on_timer_fire(self, timer_id: int, title: str, message: str):
        # Remove from active timers
        with self._lock:
            self._timers.pop(timer_id, None)

        # Dispatch native macOS notification
        try:
            self._send_macos_notification(title, message, sound="Ping")
        except Exception:
            pass

        # Speak reminder aloud if voice engine is configured
        if self.voice_engine:
            try:
                self.voice_engine.speak(f"Boss, reminder: {message}")
            except Exception:
                pass

    def _list_timers(self) -> ActionResult:
        with self._lock:
            active_timers = []
            now = time.time()
            for tid, info in sorted(self._timers.items()):
                remaining = max(0, int(info["end_time"] - now))
                rem_str = self._format_duration(remaining)
                active_timers.append({
                    "id": tid,
                    "message": info["message"],
                    "remaining_seconds": remaining,
                    "remaining_str": rem_str,
                    "created_at": info["created_at"],
                })

        if not active_timers:
            return ActionResult(
                success=True,
                message="No active timers.",
                data={"timers": []},
                metadata={"action": "list_timers"},
            )

        lines = ["Active Timers:"]
        for t in active_timers:
            lines.append(f"#{t['id']}: '{t['message']}' — {t['remaining_str']} remaining")

        return ActionResult(
            success=True,
            message="\n".join(lines),
            data={"timers": active_timers},
            metadata={"action": "list_timers"},
        )

    def _cancel_timer(self, task: Task) -> ActionResult:
        timer_id = task.parameters.get("timer_id")
        if timer_id is None and task.target:
            try:
                timer_id = int(str(task.target).replace("#", "").strip())
            except ValueError:
                pass

        if timer_id is None:
            return ActionResult(
                success=False,
                message="Specify a timer ID to cancel, for example: /cancel-timer 1",
                error="missing_timer_id",
            )

        with self._lock:
            info = self._timers.pop(timer_id, None)
            if info:
                info["timer"].cancel()
                return ActionResult(
                    success=True,
                    message=f"Cancelled Timer #{timer_id} ('{info['message']}').",
                    data={"timer_id": timer_id, "cancelled": True},
                    metadata={"action": "cancel_timer"},
                )

        return ActionResult(
            success=False,
            message=f"No active timer found with ID #{timer_id}.",
            error="timer_not_found",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _send_macos_notification(title: str, message: str, sound: str = "Glass"):
        clean_msg = message.replace('"', '\\"')
        clean_title = title.replace('"', '\\"')
        clean_sound = sound.replace('"', '\\"')
        script = f'display notification "{clean_msg}" with title "{clean_title}" sound name "{clean_sound}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True, timeout=5)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        sec = int(round(seconds))
        if sec < 60:
            return f"{sec} seconds" if sec != 1 else "1 second"
        mins = sec // 60
        rem_sec = sec % 60
        if mins < 60:
            if rem_sec == 0:
                return f"{mins} minutes" if mins != 1 else "1 minute"
            return f"{mins}m {rem_sec}s"
        hours = mins // 60
        rem_min = mins % 60
        if rem_min == 0:
            return f"{hours} hours" if hours != 1 else "1 hour"
        return f"{hours}h {rem_min}m"
