import re
import random


class OutputRouter:
    """Sprint 21.1 — Adaptive Output Renderer.

    Classifies EDITH responses into four output channels:
        'speak'   — short conversational answer, spoken aloud directly.
        'card'    — structured key-value data rendered as a rich terminal card
                    + key fields spoken aloud as a crisp sentence.
        'code'    — code block displayed on screen + spoken executive summary.
        'table'   — markdown table displayed on screen + spoken summary.
        'display' — long text displayed on screen + spoken summary.

    Card rendering uses Unicode box-drawing characters (zero dependencies).
    Voice output for cards speaks only the most important 1-3 fields.
    """

    # Thresholds
    MAX_SPEAK_LENGTH = 500
    LONG_LIST_THRESHOLD = 10

    # ──────────────────────────────────────────────────────────────────
    # Classification
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def classify(response_text):
        """Classify a text response into: 'speak', 'code', 'table', or 'display'.

        Note: 'card' is determined separately by extract_card_data() because it
        requires a structured ActionResult, not raw text.
        """
        if not response_text or not response_text.strip():
            return "speak"

        text = response_text.strip()

        if "```" in text:
            return "code"

        indented_lines = re.findall(r"^    .+", text, re.MULTILINE)
        if len(indented_lines) >= 3:
            return "code"

        if re.search(r"\|[-:]+\|", text):
            return "table"

        numbered_items = re.findall(r"^\d+\.\s", text, re.MULTILINE)
        if len(numbered_items) >= OutputRouter.LONG_LIST_THRESHOLD:
            return "display"

        if len(text) > OutputRouter.MAX_SPEAK_LENGTH:
            return "display"

        return "speak"

    # ──────────────────────────────────────────────────────────────────
    # Card system — Sprint 21.1
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def extract_card_data(action_result):
        """Inspect an ActionResult and return (title, icon, rows) for card rendering.

        Returns None if the result is not suitable for a card (e.g. plain text answer).
        Each row is a (label, value) string tuple.
        """
        if action_result is None:
            return None

        data = getattr(action_result, "data", None) or {}
        metadata = getattr(action_result, "metadata", None) or {}
        action = metadata.get("action", "")

        if action == "battery_status" and "percentage" in data:
            rows = [("Charge", f"{data['percentage']}%")]
            state = data.get("state", "")
            if state:
                rows.append(("Status", state.capitalize()))
            source = data.get("source", "")
            if source:
                rows.append(("Source", source))
            time_left = data.get("time_remaining")
            if time_left:
                rows.append(("Time Left", time_left))
            return ("Battery Status", "🔋", rows)

        if action == "power_profile" and "profile" in data:
            profile = data["profile"]
            status = data.get("status", {}) or {}
            rows = [("Profile", profile)]
            pct = status.get("percentage") if isinstance(status, dict) else None
            if pct is not None:
                rows.append(("Battery", f"{pct}%"))
            source = status.get("power_source") if isinstance(status, dict) else None
            if source:
                rows.append(("Power", source))
            throttle = status.get("throttle_ai") if isinstance(status, dict) else None
            if throttle is not None:
                rows.append(("AI Throttle", "Active ⚡" if throttle else "Off"))
            return ("Power Profile", "⚡", rows)

        if action == "set_power_profile" and "profile" in data:
            return ("Power Profile", "⚡", [("Active Profile", data["profile"])])

        if action in ("volume_get", "volume_set") and "volume" in data:
            muted = data.get("muted", False)
            rows = [("Volume", f"{data['volume']}%")]
            if muted:
                rows.append(("Status", "Muted 🔇"))
            return ("Volume", "🔊", rows)

        if action in ("volume_mute", "volume_unmute"):
            state = "Muted 🔇" if action == "volume_mute" else "Unmuted 🔊"
            return ("Volume", "🔊", [("Status", state)])

        if action in ("dark_mode_get", "dark_mode_set") and "dark_mode" in data:
            is_dark = data["dark_mode"]
            mode = "Dark Mode 🌙" if is_dark else "Light Mode ☀️"
            return ("Display", "🖥", [("Appearance", mode)])

        if action == "recall" and "key" in data and "value" in data:
            return ("Memory Recall", "🧠", [
                ("Key", str(data["key"]).capitalize()),
                ("Value", str(data["value"])),
            ])

        if action == "remember" and "key" in data and "value" in data:
            return ("Memory Saved", "🧠", [
                ("Key", str(data["key"]).capitalize()),
                ("Value", str(data["value"])),
            ])

        if action == "list_timers":
            timers = data.get("timers", [])
            if not timers:
                return None
            rows = [(f"Timer #{t.get('id', i + 1)}", t.get("message", "—")) for i, t in enumerate(timers[:6])]
            return ("Active Timers", "⏱", rows)

        if action == "lock_screen" and data.get("locked"):
            return ("Security", "🔒", [("Display", "Locked")])

        return None

    @staticmethod
    def render_card(title, rows, icon=""):
        """Render a Unicode box-drawing card from a title and list of (label, value) rows.

        Example output:
            ╭─────────────────────────────────╮
            │  🔋 Battery Status              │
            ├───────────────┬─────────────────┤
            │  Charge       │  74%            │
            │  Status       │  Discharging    │
            │  Source       │  Battery Power  │
            ╰───────────────┴─────────────────╯
        """
        if not rows:
            return f"  {icon} {title}".strip()

        max_label = max(len(str(r[0])) for r in rows)
        max_value = max(len(str(r[1])) for r in rows)

        # Minimum column widths
        max_label = max(max_label, 8)
        max_value = max(max_value, 10)

        label_col = max_label + 2   # padding
        value_col = max_value + 2

        title_text = f"  {icon} {title}" if icon else f"  {title}"
        total_inner = label_col + value_col + 1   # +1 for the │ divider

        # Ensure header fits
        if len(title_text) + 2 > total_inner:
            value_col += len(title_text) + 2 - total_inner
            total_inner = label_col + value_col + 1

        top    = f"╭{'─' * total_inner}╮"
        header = f"│{title_text:<{total_inner}}│"
        div    = f"├{'─' * label_col}┬{'─' * value_col}┤"
        bottom = f"╰{'─' * label_col}┴{'─' * value_col}╯"

        lines = [top, header, div]
        for label, value in rows:
            l_cell = f"  {label}"
            v_cell = f"  {value}"
            lines.append(f"│{l_cell:<{label_col}}│{v_cell:<{value_col}}│")
        lines.append(bottom)

        return "\n".join(lines)

    @staticmethod
    def card_spoken_summary(title, rows, max_fields=3):
        """Generate a concise spoken sentence from a card's key-value rows.

        Speaks the most important fields naturally, e.g.:
        "Battery Status: Charge is 74%, Status is Discharging, and Source is Battery Power."
        """
        if not rows:
            return f"Here is your {title}."

        key_rows = rows[:max_fields]
        parts = [f"{label} is {value}" for label, value in key_rows]

        if len(parts) == 1:
            return f"{title}: {parts[0]}."
        elif len(parts) == 2:
            return f"{title}: {parts[0]}, and {parts[1]}."
        else:
            return f"{title}: {', '.join(parts[:-1])}, and {parts[-1]}."

    # ──────────────────────────────────────────────────────────────────
    # Existing dual-channel helpers (Sprint 18.1 — unchanged)
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def extract_executive_summary(response_text):
        """Extract a concise 1-2 sentence spoken summary from rich or long text."""
        if not response_text or not response_text.strip():
            return ""

        text = response_text.strip()

        if "```" in text:
            lead_text = text.split("```")[0].strip()
            lead_text = re.sub(r"^#{1,6}\s*", "", lead_text, flags=re.MULTILINE).strip()
            if lead_text:
                sentences = re.split(r"(?<=[.!?])\s+", lead_text)
                if sentences and len(sentences[0]) > 10:
                    summary = sentences[0]
                    if len(sentences) > 1 and len(summary) + len(sentences[1]) < 180:
                        summary += " " + sentences[1]
                    return summary.strip()

        clean_lead = re.sub(r"```[\s\S]*?```", "", text)
        clean_lead = re.sub(r"^#{1,6}\s*", "", clean_lead, flags=re.MULTILINE).strip()
        clean_lead = "\n".join(
            line for line in clean_lead.splitlines() if not line.strip().startswith("|")
        ).strip()

        sentences = re.split(r"(?<=[.!?])\s+", clean_lead)
        if sentences and len(sentences[0]) > 10:
            summary = sentences[0]
            if len(sentences) > 1 and len(summary) + len(sentences[1]) < 180:
                summary += " " + sentences[1]
            return summary.strip()

        return ""

    @staticmethod
    def get_spoken_notice(response_text):
        """Generate a dual-channel spoken notice for display-mode responses."""
        text = response_text.strip() if response_text else ""
        summary = OutputRouter.extract_executive_summary(text)

        if "```" in text:
            lang_match = re.search(r"```(\w+)", text)
            lang = f"{lang_match.group(1)} " if lang_match else ""
            if summary:
                return f"{summary} I've placed the {lang}code on your screen."
            return f"I've written the {lang}code on your screen."

        if re.search(r"\|[-:]+\|", text):
            if summary:
                return f"{summary} I've displayed the table on your screen."
            return "I've displayed the table on your screen."

        numbered_items = re.findall(r"^\d+\.\s", text, re.MULTILINE)
        if len(numbered_items) >= OutputRouter.LONG_LIST_THRESHOLD:
            if summary:
                return f"{summary} I've listed the results on your screen."
            return "I've listed the results on your screen."

        if len(text) > OutputRouter.MAX_SPEAK_LENGTH:
            if summary:
                return f"{summary} I've put the full details on your screen."
            return "It's a detailed response. I've put it on your screen."

        return "Check your screen."

    @staticmethod
    def format_spoken_sentence(text):
        """Format short answers or raw data into a natural spoken sentence."""
        if not text or not text.strip():
            return ""

        clean = text.strip()

        if re.match(r"^-?\d+(\.\d+)?$", clean):
            return f"The result is {clean}."

        if re.match(r"^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?$", clean):
            return f"The current time is {clean}."

        if (
            re.match(r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}$", clean)
            or re.match(r"^[A-Za-z]+\s+\d{1,2},?\s+\d{4}$", clean)
            or re.match(r"^\d{4}-\d{2}-\d{2}$", clean)
        ):
            return f"Today's date is {clean}."

        words = clean.split()
        if len(words) == 1 and words[0].isalpha():
            return clean

        return clean

    @staticmethod
    def is_theory_or_explanation(response_text, user_query=None):
        """Check if a user query or response represents a conceptual theory or explanation."""
        if not response_text or not response_text.strip():
            return False

        if user_query:
            q = user_query.strip().lower()
            triggers = [
                "explain", "how does", "how do", "how to", "what is", "what are",
                "why does", "why do", "why is", "describe", "break down",
                "walk me through", "teach me", "tell me about", "theory", "concept", "pitfalls"
            ]
            if any(t in q for t in triggers):
                return True

        text_lower = response_text.lower()
        has_purpose = "purpose" in text_lower
        other_markers = [
            "key component", "components", "input", "output",
            "common error", "pitfall", "interactive check", "example"
        ]
        marker_count = sum(1 for m in other_markers if m in text_lower)
        if has_purpose and marker_count >= 2:
            return True

        return False

    @staticmethod
    def format_spoken_explanation(response_text):
        """Format a rich descriptive theory or explanation response for speech."""
        if not response_text or not response_text.strip():
            return ""

        text = response_text.strip()

        def _replace_code(match):
            lang = match.group(1)
            lang_str = f"{lang} " if lang else ""
            return f"\nI've placed the {lang_str}code implementation on your screen.\n"

        spoken_text = re.sub(r"```(\w+)?[\s\S]*?```", _replace_code, text)
        return spoken_text.strip()

    # ══════════════════════════════════════════════════════════════════
    # Sprint 21.1 — Situational Renderers
    # ══════════════════════════════════════════════════════════════════

    # Varied driving follow-ups so EDITH never sounds robotic
    _DRIVING_FOLLOW_UPS = [
        "Want me to navigate to the first one?",
        "Should I pull up directions in Maps?",
        "Say 'navigate' and I'll open Maps for you.",
        "Want me to set a reminder for that?",
        "Should I read that again when you're ready?",
        "Want me to call ahead?",
        "Say the word and I'll handle the rest.",
    ]

    @staticmethod
    def render_for_mode(mode, action_result=None, response_text=""):
        """Dispatch to the correct situational renderer.

        Args:
            mode:          'driving' | 'meeting' | 'desk' | 'default'
            action_result: Optional ActionResult from a tool execution.
            response_text: Raw text string (from LLM or tool message).

        Returns:
            RenderOutput — a structured container with:
                .screen     str | None  — text to print (None = show plain ✅ line)
                .voice      str | None  — text to speak (None = silence)
                .follow_up  str | None  — optional second spoken prompt
        """
        if mode == "driving":
            return OutputRouter._render_driving(action_result, response_text)
        if mode == "meeting":
            return OutputRouter._render_meeting(action_result, response_text)
        if mode == "desk":
            return OutputRouter._render_desk(action_result, response_text)
        return OutputRouter._render_default(action_result, response_text)

    # ── Driving ────────────────────────────────────────────────────────
    @staticmethod
    def _render_driving(action_result, response_text):
        """Voice-only. Crisp spoken summary of the top 2-3 points. No rich cards.
        Adds a randomised follow-up prompt for hands-free convenience."""
        card_data = OutputRouter.extract_card_data(action_result) if action_result else None

        if card_data:
            title, _icon, rows = card_data
            key_rows = rows[:3]
            if len(key_rows) == 1:
                voice = f"{title}: {key_rows[0][1]}."
            else:
                items = [f"{i + 1}. {label}: {value}" for i, (label, value) in enumerate(key_rows)]
                voice = f"{title}. " + ". ".join(items) + "."
        else:
            # Pull 2-3 plain sentences from text, strip markdown noise
            raw = (response_text or "").strip()
            clean = re.sub(r"```[\s\S]*?```", "", raw)
            clean = re.sub(r"^#{1,6}\s*", "", clean, flags=re.MULTILINE)
            clean = re.sub(r"\*+", "", clean).strip()
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", clean)
                if s.strip() and not s.strip().startswith("|")
            ][:3]

            if not sentences:
                voice = "I've got a response ready — check your screen when you can."
            elif len(sentences) == 1:
                voice = sentences[0]
            else:
                numbered = [f"{i + 1}. {s}" for i, s in enumerate(sentences)]
                voice = ". ".join(numbered)

        follow_up = random.choice(OutputRouter._DRIVING_FOLLOW_UPS)
        # screen=None → caller shows a minimal ✅ indicator instead of a full card
        return RenderOutput(screen=None, voice=voice, follow_up=follow_up, mode="driving")

    # ── Meeting ────────────────────────────────────────────────────────
    @staticmethod
    def _render_meeting(action_result, response_text):
        """Silent. One compact line on screen — no voice, no card, no distraction."""
        card_data = OutputRouter.extract_card_data(action_result) if action_result else None

        if card_data:
            title, icon, rows = card_data
            # "🔋 Battery Status: 74% · Discharging"
            brief = " · ".join(str(v) for _, v in rows[:2])
            line = f"{icon} {title}: {brief}"
        else:
            raw = (response_text or "").strip()
            clean = re.sub(r"```[\s\S]*?```", "", raw)
            clean = re.sub(r"^#{1,6}\s*", "", clean, flags=re.MULTILINE)
            clean = re.sub(r"\*+", "", clean).strip()
            first_line = (clean.splitlines()[0].strip() if clean else raw)[:100]
            line = first_line

        screen = f"📌 {line}"
        return RenderOutput(screen=screen, voice=None, follow_up=None, mode="meeting")

    # ── Desk ───────────────────────────────────────────────────────────
    @staticmethod
    def _render_desk(action_result, response_text):
        """Full detail. Rich card with action hints + spoken executive summary."""
        card_data = OutputRouter.extract_card_data(action_result) if action_result else None

        if card_data:
            title, icon, rows = card_data
            card = OutputRouter.render_card(title, rows, icon=icon)
            action_hint = "  ↳ Ask a follow-up or say 'details' for more."
            screen = f"{card}\n{action_hint}"
            voice = OutputRouter.card_spoken_summary(title, rows)
        else:
            raw = (response_text or "").strip()
            screen = raw
            voice = OutputRouter.extract_executive_summary(raw) or raw[:150]
            if len(raw) > 300:
                screen += "\n  ↳ Full details above. Ask a follow-up anytime."

        return RenderOutput(screen=screen, voice=voice, follow_up=None, mode="desk")

    # ── Default ────────────────────────────────────────────────────────
    @staticmethod
    def _render_default(action_result, response_text):
        """Adaptive Sprint 21.1 behaviour — card if structured, otherwise classify text."""
        card_data = OutputRouter.extract_card_data(action_result) if action_result else None

        if card_data:
            title, icon, rows = card_data
            screen = OutputRouter.render_card(title, rows, icon=icon)
            voice = OutputRouter.card_spoken_summary(title, rows)
            return RenderOutput(screen=screen, voice=voice, follow_up=None, mode="default")

        raw = (response_text or "").strip()
        mode_class = OutputRouter.classify(raw)

        if mode_class == "speak":
            voice = OutputRouter.format_spoken_sentence(raw)
            return RenderOutput(screen=None, voice=voice, follow_up=None, mode="default")

        notice = OutputRouter.get_spoken_notice(raw)
        return RenderOutput(screen=raw, voice=notice, follow_up=None, mode="default")


# ── RenderOutput ───────────────────────────────────────────────────────────────
class RenderOutput:
    """Structured output decision returned by OutputRouter.render_for_mode().

    Attributes:
        screen    str | None — Content to print on screen.
                               None means the caller should print a minimal ✅ line.
        voice     str | None — Text to speak aloud.
                               None means stay silent (e.g., meeting mode).
        follow_up str | None — An optional second spoken prompt (e.g., driving follow-up).
        mode      str        — The situational mode that produced this output.
    """
    __slots__ = ("screen", "voice", "follow_up", "mode")

    def __init__(self, screen=None, voice=None, follow_up=None, mode="default"):
        self.screen = screen
        self.voice = voice
        self.follow_up = follow_up
        self.mode = mode

    def __repr__(self):
        return (
            f"RenderOutput(mode={self.mode!r}, "
            f"screen={'<text>' if self.screen else None}, "
            f"voice={'<text>' if self.voice else None}, "
            f"follow_up={'<text>' if self.follow_up else None})"
        )
