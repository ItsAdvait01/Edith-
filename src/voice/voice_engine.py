import subprocess
import re


class VoiceEngine:
    """macOS native text-to-speech engine using the built-in `say` command.

    Zero dependencies, zero extra RAM. Uses the system voice synthesizer.
    Speech runs in a non-blocking subprocess so EDITH stays responsive.
    """

    DEFAULT_VOICE = "Tara"
    DEFAULT_RATE = 190  # words per minute

    def __init__(self, voice=None, rate=None):
        self.voice = voice or self.DEFAULT_VOICE
        self.rate = rate or self.DEFAULT_RATE
        self._process = None

    def speak(self, text, rate=None):
        """Speak text aloud (non-blocking). EDITH stays responsive."""
        self.stop()

        clean_text = self._sanitize(text)
        if not clean_text:
            return

        speech_rate = rate or self.rate
        try:
            self._process = subprocess.Popen(
                ["say", "-v", self.voice, "-r", str(speech_rate), clean_text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    def speak_sync(self, text, rate=None):
        """Speak text aloud (blocking). Waits until speech finishes."""
        self.stop()

        clean_text = self._sanitize(text)
        if not clean_text:
            return

        speech_rate = rate or self.rate
        try:
            subprocess.run(
                ["say", "-v", self.voice, "-r", str(speech_rate), clean_text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def stop(self):
        """Kill any currently running speech process."""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        self._process = None

    @property
    def is_speaking(self):
        return self._process is not None and self._process.poll() is None

    @staticmethod
    def _sanitize(text):
        """Strip code, markdown, emoji, and special characters for clean speech."""
        if not text or not text.strip():
            return ""

        # Remove code blocks entirely
        cleaned = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline code backticks
        cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)

        # Remove markdown bold/italic
        cleaned = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", cleaned)
        cleaned = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", cleaned)

        # Remove markdown headers
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)

        # Remove markdown links, keep label
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

        # Remove bullet markers
        cleaned = re.sub(r"^[\s]*[-*•]\s+", "", cleaned, flags=re.MULTILINE)

        # Remove emoji and special unicode symbols
        cleaned = re.sub(
            r"[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
            r"\U0000200D\U00002600-\U000026FF\U00002700-\U000027BF"
            r"⚙️✅❌🔊🔇🧠👋💬💻🔗]", "", cleaned
        )

        # Remove EDITH system prefixes
        cleaned = re.sub(r"EDITH\s*>\s*", "", cleaned)
        cleaned = re.sub(r"\[EDITH SYSTEM ERROR\]", "", cleaned)

        # Collapse whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        return cleaned
