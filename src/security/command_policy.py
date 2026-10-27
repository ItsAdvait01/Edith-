import re


class CommandPolicy:
    """Stateless command-risk classifier for terminal safety.

    Classifies shell commands into four risk levels and provides
    formatted confirmation previews.  Extracted from TerminalTool's
    hardcoded allowlist in Sprint 12.2.
    """

    RISK_NONE = "none"
    RISK_LOW = "low"
    RISK_HIGH = "high"
    RISK_DESTRUCTIVE = "destructive"

    _READ_ONLY_PREFIXES = (
        "pwd",
        "ls",
        "cat ",
        "echo ",
        "which ",
        "python --version",
        "git status",
        "git log",
        "git diff",
    )

    _DESTRUCTIVE_PREFIXES = (
        "rm ",
        "rm\t",
        "rmdir ",
        "kill ",
        "killall ",
        "shutdown",
        "reboot",
        "mkfs",
        "dd ",
    )

    _SHELL_OPERATOR_PATTERN = re.compile(r"[;&|><`$()\n]")

    def classify(self, command):
        """Return the risk level for a shell command string."""
        normalized = command.strip().lower()

        if not normalized:
            return self.RISK_HIGH

        # Shell operators can turn any prefix into something dangerous.
        if self._SHELL_OPERATOR_PATTERN.search(normalized):
            return self.RISK_HIGH

        if normalized.startswith(self._READ_ONLY_PREFIXES):
            return self.RISK_NONE

        if normalized.startswith(self._DESTRUCTIVE_PREFIXES):
            return self.RISK_DESTRUCTIVE

        return self.RISK_HIGH

    def requires_confirmation(self, command):
        """Return True if the command should not run without user consent."""
        return self.classify(command) != self.RISK_NONE

    def format_preview(self, command, risk=None, working_directory=None):
        """Build a human-readable confirmation preview string."""
        risk = risk or self.classify(command)
        cwd_label = working_directory or "current directory"

        risk_labels = {
            self.RISK_LOW: "Low risk",
            self.RISK_HIGH: "High risk",
            self.RISK_DESTRUCTIVE: "⚠ Destructive",
        }
        risk_text = risk_labels.get(risk, risk)

        return (
            f"[{risk_text}] Confirmation required before running:\n"
            f"  $ {command}\n"
            f"  in: {cwd_label}"
        )
