import datetime
import random


class VoicePersonality:
    """Personality and conversational layer for EDITH's voice interface.

    Provides situational phrasing, time-aware greetings, snappy pre-acknowledgments,
    and voice safety dialogues. Integrates with MemoryStore for personal touch.
    """

    RATE_FAST = 215       # Snappy acknowledgments
    RATE_NORMAL = 190     # Conversational responses
    RATE_DELIBERATE = 175 # Safety warnings and confirmations

    ACK_PHRASES = [
        "Got you, Boss.",
        "Say no more.",
        "Right on it.",
        "Pulling that up now.",
        "Scanning that now.",
        "Working on that, Boss.",
        "On it.",
    ]

    def __init__(self, memory_store=None):
        self.memory_store = memory_store
        self._ack_index = 0

    def get_user_name(self):
        """Retrieve remembered user name from MemoryStore if available."""
        if not self.memory_store:
            return None

        # Check standard name keys
        for key in ["my name", "name", "user_name"]:
            val = None
            if hasattr(self.memory_store, "get"):
                val = self.memory_store.get(key)
            elif hasattr(self.memory_store, "recall"):
                val = self.memory_store.recall(key)
            if val:
                return str(val).strip()
        return None

    def get_greeting(self, custom_time=None):
        """Generate a time-aware FRIDAY greeting, addressing the user by name or Boss."""
        now = custom_time or datetime.datetime.now()
        hour = now.hour

        if 5 <= hour < 12:
            time_greeting = "Good morning"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon"
        elif 17 <= hour < 22:
            time_greeting = "Good evening"
        else:
            time_greeting = "Hello"

        name = self.get_user_name() or "Boss"
        return f"{time_greeting}, {name}. Systems green and ready to roll."

    def get_acknowledgment(self):
        """Return a brief, snappy acknowledgment cue before long thinking/processing."""
        phrase = self.ACK_PHRASES[self._ack_index % len(self.ACK_PHRASES)]
        self._ack_index += 1
        return phrase

    def get_task_completion_notice(self, success=True, task_desc=""):
        """Provide a conversational voice summary of task execution."""
        name = self.get_user_name() or "Boss"
        suffix = f", {name}"

        if success:
            return f"All set{suffix}. Task completed."
        return f"Heads up{suffix}, ran into an issue executing that task."

    def get_confirmation_notice(self, target="", risk_level="high"):
        """Provide a clear, deliberate voice prompt for gated actions."""
        if risk_level in ["destructive", "high"]:
            return "Heads up: this command requires your authorization. Should I give the green light?"
        return "Please confirm if you would like me to execute this action."
