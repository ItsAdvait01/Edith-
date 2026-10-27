import re
import subprocess
from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task
from system.power_manager import PowerManager


class SystemTool(BaseTool):
    """Inspects and controls macOS system and hardware settings."""

    NAME = "system"
    DESCRIPTION = "Inspects and controls macOS system and hardware settings (volume, battery, dark mode, lock screen, power profiles)."
    RESOURCE_PROFILE = "device"
    SUPPORTED_ACTIONS = frozenset({
        "volume_set",
        "volume_get",
        "volume_mute",
        "volume_unmute",
        "battery_status",
        "dark_mode_get",
        "dark_mode_set",
        "dark_mode_toggle",
        "lock_screen",
        "power_profile",
        "set_power_profile",
    })

    def __init__(self, power_manager=None):
        self.power_manager = power_manager or PowerManager()

    def can_handle(self, user_input):
        text = user_input.strip().lower()
        triggers = [
            "volume", "mute", "unmute", "battery",
            "dark mode", "lock screen", "lock mac",
        ]
        return any(t in text for t in triggers)

    def task_from_legacy_input(self, user_input):
        text = user_input.strip().lower()
        if "battery" in text:
            return Task(tool=self.NAME, action="battery_status")
        if text == "mute":
            return Task(tool=self.NAME, action="volume_mute")
        if text == "unmute":
            return Task(tool=self.NAME, action="volume_unmute")
        if "volume" in text:
            match = re.search(r"\b(\d{1,3})\b", text)
            if match:
                return Task(tool=self.NAME, action="volume_set", parameters={"level": int(match.group(1))})
            return Task(tool=self.NAME, action="volume_get")
        if "dark mode" in text:
            if "on" in text or "enable" in text:
                return Task(tool=self.NAME, action="dark_mode_set", parameters={"enabled": True})
            if "off" in text or "disable" in text:
                return Task(tool=self.NAME, action="dark_mode_set", parameters={"enabled": False})
            return Task(tool=self.NAME, action="dark_mode_toggle")
        if "lock" in text:
            return Task(tool=self.NAME, action="lock_screen")
        return None

    def execute(self, task: Task) -> ActionResult:
        action = task.action
        if action not in self.SUPPORTED_ACTIONS:
            return ActionResult(
                success=False,
                message=f"System skill does not support action '{action}'.",
                error="unsupported_action",
            )

        if action == "volume_get":
            return self._get_volume()
        elif action == "volume_set":
            return self._set_volume(task)
        elif action == "volume_mute":
            return self._set_mute(True)
        elif action == "volume_unmute":
            return self._set_mute(False)
        elif action == "battery_status":
            return self._get_battery()
        elif action == "dark_mode_get":
            return self._get_dark_mode()
        elif action == "dark_mode_set":
            enabled = bool(task.parameters.get("enabled", True))
            return self._set_dark_mode(enabled)
        elif action == "dark_mode_toggle":
            return self._toggle_dark_mode()
        elif action == "lock_screen":
            return self._lock_screen()
        elif action == "power_profile":
            return self._get_power_profile()
        elif action == "set_power_profile":
            return self._set_power_profile(task)

        return ActionResult(success=False, message="Unhandled system action.", error="unhandled_action")

    # ------------------------------------------------------------------
    # Power & Battery Profiles
    # ------------------------------------------------------------------

    def _get_power_profile(self) -> ActionResult:
        summary = self.power_manager.get_summary()
        status = self.power_manager.get_power_status()
        profile = self.power_manager.get_active_profile()
        return ActionResult(
            success=True,
            message=summary,
            data={"profile": profile, "status": status},
            metadata={"action": "power_profile"},
        )

    def _set_power_profile(self, task: Task) -> ActionResult:
        profile = task.parameters.get("profile") or task.target or "auto"
        self.power_manager.set_manual_profile(profile)
        active = self.power_manager.get_active_profile()
        return ActionResult(
            success=True,
            message=f"Power profile set to {active}.",
            data={"profile": active},
            metadata={"action": "set_power_profile"},
        )

    # ------------------------------------------------------------------
    # Volume Controls
    # ------------------------------------------------------------------

    def _get_volume(self) -> ActionResult:
        try:
            cmd = ["osascript", "-e", "output volume of (get volume settings)"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            level = int(res.stdout.strip())

            mute_cmd = ["osascript", "-e", "output muted of (get volume settings)"]
            mute_res = subprocess.run(mute_cmd, capture_output=True, text=True, timeout=5)
            is_muted = mute_res.stdout.strip().lower() == "true"

            status_str = f"Volume is at {level}%."
            if is_muted:
                status_str += " (Muted)"

            return ActionResult(
                success=True,
                message=status_str,
                data={"volume": level, "muted": is_muted},
                metadata={"action": "volume_get"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to get system volume: {e}",
                error=str(e),
            )

    def _set_volume(self, task: Task) -> ActionResult:
        try:
            target_level = None
            if "level" in task.parameters:
                target_level = int(task.parameters["level"])
            elif "relative" in task.parameters:
                current_res = self._get_volume()
                if current_res.success and current_res.data:
                    current_level = current_res.data.get("volume", 50)
                else:
                    current_level = 50
                target_level = current_level + int(task.parameters["relative"])
            elif task.target:
                match = re.search(r"\b(\d{1,3})\b", str(task.target))
                if match:
                    target_level = int(match.group(1))

            if target_level is None:
                return ActionResult(
                    success=False,
                    message="Volume level not specified.",
                    error="missing_parameter",
                )

            # Clamp level between 0 and 100
            target_level = max(0, min(100, target_level))

            cmd = ["osascript", "-e", f"set volume output volume {target_level}"]
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)

            return ActionResult(
                success=True,
                message=f"Volume set to {target_level}%.",
                data={"volume": target_level},
                metadata={"action": "volume_set"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to set system volume: {e}",
                error=str(e),
            )

    def _set_mute(self, muted: bool) -> ActionResult:
        try:
            arg = "true" if muted else "false"
            cmd = ["osascript", "-e", f"set volume output muted {arg}"]
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)

            msg = "System muted." if muted else "System unmuted."
            return ActionResult(
                success=True,
                message=msg,
                data={"muted": muted},
                metadata={"action": "volume_mute" if muted else "volume_unmute"},
            )
        except Exception as e:
            action_name = "mute" if muted else "unmute"
            return ActionResult(
                success=False,
                message=f"Failed to {action_name} volume: {e}",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Battery Status
    # ------------------------------------------------------------------

    def _get_battery(self) -> ActionResult:
        try:
            res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, check=True, timeout=5)
            output = res.stdout.strip()

            # Parse power source: "Now drawing from 'Battery Power'" or "'AC Power'"
            source_match = re.search(r"Now drawing from '([^']+)'", output)
            power_source = source_match.group(1) if source_match else "Unknown"

            # Parse percentage and state: e.g., "51%; discharging; (no estimate) present: true"
            batt_match = re.search(r"(\d+)%;\s*([^;]+);", output)
            if batt_match:
                percent = int(batt_match.group(1))
                state = batt_match.group(2).strip()

                time_match = re.search(r";\s*(\d+:\d+)\s+remaining", output)
                time_remaining = time_match.group(1) if time_match else None

                rem_str = f", {time_remaining} remaining" if time_remaining else ""
                message = f"Battery is at {percent}% ({state}, {power_source}{rem_str})."

                return ActionResult(
                    success=True,
                    message=message,
                    data={
                        "percentage": percent,
                        "state": state,
                        "source": power_source,
                        "time_remaining": time_remaining,
                    },
                    metadata={"action": "battery_status"},
                )

            return ActionResult(
                success=True,
                message=f"Battery status: {output}",
                data={"raw": output},
                metadata={"action": "battery_status"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to retrieve battery status: {e}",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Dark Mode
    # ------------------------------------------------------------------

    def _get_dark_mode(self) -> ActionResult:
        try:
            res = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_dark = res.returncode == 0 and res.stdout.strip().lower() == "dark"
            mode_name = "Dark" if is_dark else "Light"
            return ActionResult(
                success=True,
                message=f"System appearance is in {mode_name} Mode.",
                data={"dark_mode": is_dark},
                metadata={"action": "dark_mode_get"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to get dark mode status: {e}",
                error=str(e),
            )

    def _set_dark_mode(self, enabled: bool) -> ActionResult:
        try:
            arg = "true" if enabled else "false"
            script = f'tell application "System Events" to tell appearance preferences to set dark mode to {arg}'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or "AppleScript error"
                if "permission" in err_msg.lower() or "-54" in err_msg:
                    return ActionResult(
                        success=False,
                        message="System Events permission required to change dark mode appearance.",
                        error="permission_required",
                    )
                return ActionResult(
                    success=False,
                    message=f"Failed to set dark mode: {err_msg}",
                    error=err_msg,
                )

            mode_name = "Dark" if enabled else "Light"
            return ActionResult(
                success=True,
                message=f"Switched system appearance to {mode_name} Mode.",
                data={"dark_mode": enabled},
                metadata={"action": "dark_mode_set"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to set dark mode: {e}",
                error=str(e),
            )

    def _toggle_dark_mode(self) -> ActionResult:
        current_res = self._get_dark_mode()
        current_dark = current_res.data.get("dark_mode", False) if current_res.success and current_res.data else False
        return self._set_dark_mode(not current_dark)

    # ------------------------------------------------------------------
    # Lock Screen
    # ------------------------------------------------------------------

    def _lock_screen(self) -> ActionResult:
        try:
            # pmset displaysleepnow immediately puts displays to sleep and locks if configured
            subprocess.run(["pmset", "displaysleepnow"], check=True, timeout=5)
            return ActionResult(
                success=True,
                message="Locked system display.",
                data={"locked": True},
                metadata={"action": "lock_screen"},
            )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Failed to lock screen: {e}",
                error=str(e),
            )
