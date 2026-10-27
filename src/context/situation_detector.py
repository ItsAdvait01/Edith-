"""Sprint 21.1 — Situational Awareness Mode.

Tracks the user's current real-world context so EDITH can adapt
its output format without being asked every time.

Modes
-----
default   Adaptive auto-select (existing Sprint 21.1 card/speak/display logic).
driving   Voice-only crisp spoken summary of the 2-3 key points.
          No rich cards. A follow-up spoken prompt ("Want me to navigate?").
meeting   Silent mode. Single compact notification line on screen only.
          Voice is suppressed — user is in a call.
desk      Full rich cards with action hints and a spoken executive summary.
          Maximum detail; user has both eyes on the screen.
"""

import random


class SituationDetector:
    """Tracks and exposes the user's current situational output mode."""

    MODES = frozenset({"default", "driving", "meeting", "desk"})

    _DESCRIPTIONS = {
        "default":  "Adaptive — auto-selects card, spoken, or display format.",
        "driving":  "Voice-only — crisp spoken summaries, no rich screen cards.",
        "meeting":  "Silent — compact single-line text, voice suppressed.",
        "desk":     "Full detail — rich cards, highlights, and action hints.",
    }

    _MODE_ICONS = {
        "default": "⚡",
        "driving": "🚗",
        "meeting": "🤫",
        "desk":    "🖥",
    }

    def __init__(self):
        self._mode: str = "default"

    # ── Public API ─────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> bool:
        """Set the active mode. Returns False if mode is unknown."""
        mode = mode.strip().lower()
        if mode not in self.MODES:
            return False
        self._mode = mode
        return True

    @property
    def mode(self) -> str:
        """The currently active situational mode."""
        return self._mode

    def get_summary(self) -> str:
        """Return a human-readable summary of the current mode for CLI display."""
        icon = self._MODE_ICONS.get(self._mode, "")
        desc = self._DESCRIPTIONS.get(self._mode, "")
        return (
            f"Output mode: {icon} {self._mode.capitalize()}\n"
            f"  {desc}\n"
            f"  Change with: /mode driving | /mode desk | /mode meeting | /mode default"
        )
