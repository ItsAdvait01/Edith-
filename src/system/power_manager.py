import re
import time
import subprocess
from cnfig.settings import CLOUD_API_KEY


class PowerManager:
    """Monitors macOS power telemetry and adapts AI execution profiles
    to protect the fanless M1 MacBook Air from overheating and battery drain.
    """

    PROFILE_PERFORMANCE = "performance"
    PROFILE_BALANCED = "balanced"
    PROFILE_ECO_SAVER = "eco_saver"

    # Action keywords that indicate an explicit OS / tool operation
    # (If a prompt contains these, AI planning might be needed; otherwise it's conversational)
    ACTION_KEYWORDS = frozenset({
        "open", "launch", "start", "run", "execute", "create", "make",
        "delete", "remove", "read", "view", "show", "search", "browse",
        "volume", "mute", "unmute", "battery", "lock", "dark mode",
        "timer", "remind", "reminder", "notify", "notification",
        "remember", "recall", "forget", "screenshot", "capture", "calculate",
    })

    def __init__(self):
        self._manual_profile = None  # None (auto), 'eco', 'performance'
        self._cached_status = None
        self._cache_timestamp = 0
        self._cache_ttl = 5.0  # seconds

    def get_power_status(self) -> dict:
        """Query macOS pmset with short-lived caching."""
        now = time.time()
        if self._cached_status and (now - self._cache_timestamp < self._cache_ttl):
            return self._cached_status

        status = {
            "percentage": 100,
            "source": "AC Power",
            "state": "charged",
            "is_on_battery": False,
            "is_low_battery": False,
            "time_remaining": None,
        }

        try:
            res = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
            output = res.stdout.strip()

            source_match = re.search(r"Now drawing from '([^']+)'", output)
            if source_match:
                source = source_match.group(1)
                status["source"] = source
                status["is_on_battery"] = "battery" in source.lower()

            batt_match = re.search(r"(\d+)%;\s*([^;]+);", output)
            if batt_match:
                status["percentage"] = int(batt_match.group(1))
                status["state"] = batt_match.group(2).strip()

            time_match = re.search(r";\s*(\d+:\d+)\s+remaining", output)
            if time_match:
                status["time_remaining"] = time_match.group(1)

            status["is_low_battery"] = status["is_on_battery"] and status["percentage"] <= 20

        except Exception:
            pass

        self._cached_status = status
        self._cache_timestamp = now
        return status

    def get_active_profile(self) -> str:
        """Determine the active power profile."""
        if self._manual_profile == "eco":
            return self.PROFILE_ECO_SAVER
        elif self._manual_profile == "performance":
            return self.PROFILE_PERFORMANCE

        status = self.get_power_status()
        if not status["is_on_battery"]:
            return self.PROFILE_PERFORMANCE
        elif status["is_low_battery"]:
            return self.PROFILE_ECO_SAVER
        else:
            return self.PROFILE_BALANCED

    def set_manual_profile(self, profile: str):
        """Set manual profile override: 'eco', 'performance', or 'auto' (None)."""
        clean = (profile or "").strip().lower()
        if clean in ["eco", "eco_saver", "saver"]:
            self._manual_profile = "eco"
        elif clean in ["perf", "performance", "high"]:
            self._manual_profile = "performance"
        else:
            self._manual_profile = None  # auto

    def should_throttle_speculative_ai(self, user_input: str = "") -> bool:
        """Check if speculative AI planning should be skipped to prevent heat/battery drain.

        On a fanless M1, running Ollama gemma3:4b pegs 8 cores at 100%.
        If the user is on battery power (or eco mode) and the prompt is conversational
        (no action keywords like 'open', 'create', 'run'), running speculative AI planner
        is a waste of battery. Skipping it saves an entire 4B neural inference pass!
        """
        profile = self.get_active_profile()

        # Performance mode (plugged in): no throttling needed
        if profile == self.PROFILE_PERFORMANCE:
            return False

        # In Eco Saver (<=20% battery or manual eco): throttle all speculative passes
        if profile == self.PROFILE_ECO_SAVER:
            return True

        # In Balanced mode (on battery > 20%):
        # Check if the prompt looks like an OS command
        words = set(re.findall(r"\b\w+\b", user_input.lower()))
        has_action = bool(words & self.ACTION_KEYWORDS)

        # If it has NO action keyword, it is almost certainly chat/question/conversational
        # Throttle speculative planner to save CPU and battery
        return not has_action

    def get_recommended_provider(self, current_provider: str) -> str:
        """Recommend Cloud provider if on battery power and an API key is present,
        offloading compute from the fanless M1 to keep it ice-cold.
        """
        status = self.get_power_status()
        if status["is_on_battery"] and CLOUD_API_KEY:
            return "cloud"
        return current_provider

    def get_summary(self) -> str:
        """Return a formatted power status summary."""
        status = self.get_power_status()
        profile = self.get_active_profile()

        profile_names = {
            self.PROFILE_PERFORMANCE: "Performance (AC Plugged In)",
            self.PROFILE_BALANCED: "Balanced (Battery Aware)",
            self.PROFILE_ECO_SAVER: "Eco Saver (Maximum Battery Protection)",
        }

        mode_desc = profile_names.get(profile, profile)
        source = status["source"]
        pct = status["percentage"]
        state = status["state"]
        rem = f", {status['time_remaining']} remaining" if status.get("time_remaining") else ""

        lines = [
            f"Power Profile: {mode_desc}",
            f"Battery: {pct}% ({state}, {source}{rem})",
        ]

        if profile == self.PROFILE_PERFORMANCE:
            lines.append("Thermal Optimization: Unrestricted (AC power connected).")
        elif profile == self.PROFILE_BALANCED:
            lines.append("Thermal Optimization: Active (Speculative AI throttled for conversational chats to keep Mac cool).")
        else:
            lines.append("Thermal Optimization: High Protection (Heavy local inference suppressed to extend battery).")

        return "\n".join(lines)
