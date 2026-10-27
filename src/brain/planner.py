import re

from brain.task import Task


class Planner:

    def __init__(self, task_queue=None, capabilities=None, context_manager=None):

        self.task_queue = task_queue
        self.capabilities = capabilities
        self.context_manager = context_manager

    _CONFIRMATION_PHRASES = frozenset({"yes", "y", "confirm"})

    @staticmethod
    def is_confirmation(user_input):
        """Return True only when the entire input is an exact confirmation phrase."""
        return user_input.strip().lower() in Planner._CONFIRMATION_PHRASES

    def plan(self, user_input):

        text = user_input.lower()
        
        if self.context_manager:
            if r"\bthis\b" not in text and " this " in f" {text} ":
                context_result = self.context_manager.get_active_context()
                if context_result.success:
                    window_title = context_result.data.get("window_title")
                    app_name = context_result.data.get("application")
                    replacement = window_title if window_title else app_name
                    if replacement:
                        text = re.sub(r"\bthis\b", replacement, text)
                        user_input = re.sub(r"(?i)\bthis\b", replacement, user_input)
                        
            if r"\bclipboard\b" not in text and " clipboard " in f" {text} ":
                clipboard_result = self.context_manager.get_clipboard()
                if clipboard_result.success and clipboard_result.data.get("clipboard"):
                    # Only substitute if there's actual text
                    clipboard_text = clipboard_result.data.get("clipboard").strip()
                    if clipboard_text:
                        text = re.sub(r"\bclipboard\b", clipboard_text, text)
                        user_input = re.sub(r"(?i)\bclipboard\b", clipboard_text, user_input)

        tasks = []

        if text.startswith("run command "):
            tasks.append(Task("terminal", "execute", user_input[12:].strip()))

        elif text.startswith("create python project"):
            project_name = self._project_name(user_input)

            if project_name:
                tasks.extend(
                    [
                        Task("file", "create_folder", project_name),
                        Task("file", "create_file", f"{project_name}/README.md"),
                        Task("file", "create_file", f"{project_name}/main.py"),
                    ]
                )

        elif text.startswith("open http"):
            url = user_input[5:].strip()
            tasks.append(Task("browser", "open_url", url))
            
        elif text.startswith("search for "):
            query = user_input[11:].strip()
            tasks.append(Task("browser", "search", query))
            
        elif text.startswith("search "):
            query = user_input[7:].strip()
            tasks.append(Task("browser", "search", query))
            
        elif text.startswith("take screenshot") or text.startswith("capture screen"):
            tasks.append(Task("perception", "capture_screen"))

        elif text in [
            "analyze screen", "analyse screen",
            "what's on my screen", "what is on my screen",
            "what's on my screen?", "what is on my screen?",
            "read my screen", "inspect screen",
            "explain the error on my screen",
            "explain error on screen",
        ]:
            tasks.append(Task("perception", "analyze_screen"))

        elif re.match(r"^(?:what(?:'s| is) (?:on )?my screen|analyze screen|analyse screen|read (?:my )?screen)\??$", text):
            tasks.append(Task("perception", "analyze_screen"))

        elif re.match(r"^(?:explain|describe|read|what(?:'s| is) in).*(?:screen|display|window|monitor)\??$", text):
            # e.g. "explain what's on my screen", "describe my screen", "what is on my display"
            tasks.append(Task("perception", "analyze_screen", parameters={"prompt": user_input}))

        # System controls (Sprint 19.0 & Battery-Aware Intelligence)
        elif text in ["battery", "battery?", "check battery", "battery status", "battery level", "what is my battery", "what is my battery?", "what's my battery", "what's my battery?", "how much battery do i have", "how much battery?"]:
            tasks.append(Task("system", "battery_status"))

        elif text in ["/power", "/eco", "power", "power mode", "power status", "check power", "battery profile", "eco mode", "thermal status", "power profile"]:
            tasks.append(Task("system", "power_profile"))

        elif text in ["/eco on", "enable eco mode", "turn on eco mode", "eco on"]:
            tasks.append(Task("system", "set_power_profile", parameters={"profile": "eco"}))

        elif text in ["/eco off", "disable eco mode", "turn off eco mode", "eco off"]:
            tasks.append(Task("system", "set_power_profile", parameters={"profile": "auto"}))

        elif text in ["mute", "mute volume", "mute audio", "mute sound"]:
            tasks.append(Task("system", "volume_mute"))

        elif text in ["unmute", "unmute volume", "unmute audio", "unmute sound"]:
            tasks.append(Task("system", "volume_unmute"))

        elif text in ["what is the volume", "what is the volume?", "what's the volume", "what's the volume?", "volume status", "get volume"]:
            tasks.append(Task("system", "volume_get"))

        elif re.match(r"^(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?$", text):
            match = re.match(r"^(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?$", text)
            level = int(match.group(1))
            tasks.append(Task("system", "volume_set", parameters={"level": level}))

        elif text in ["volume up", "increase volume", "turn volume up", "louder"]:
            tasks.append(Task("system", "volume_set", parameters={"relative": 10}))

        elif text in ["volume down", "decrease volume", "turn volume down", "lower volume", "softer"]:
            tasks.append(Task("system", "volume_set", parameters={"relative": -10}))

        elif text in ["turn on dark mode", "enable dark mode", "set dark mode on", "dark mode on"]:
            tasks.append(Task("system", "dark_mode_set", parameters={"enabled": True}))

        elif text in ["turn off dark mode", "disable dark mode", "set dark mode off", "dark mode off"]:
            tasks.append(Task("system", "dark_mode_set", parameters={"enabled": False}))

        elif text in ["toggle dark mode", "switch dark mode"]:
            tasks.append(Task("system", "dark_mode_toggle"))

        elif text in ["is dark mode on", "is dark mode on?", "dark mode status", "check dark mode"]:
            tasks.append(Task("system", "dark_mode_get"))

        elif text in ["lock screen", "lock mac", "lock the screen", "lock computer"]:
            tasks.append(Task("system", "lock_screen"))

        # Reminders, Timers & Notifications (Sprint 20.0)
        elif text in ["/timers", "timers", "list timers", "active timers", "show timers"]:
            tasks.append(Task("notification", "list_timers"))

        elif re.match(r"^(?:/cancel-timer|cancel\s+timer)\s+#?(\d+)$", text):
            match = re.match(r"^(?:/cancel-timer|cancel\s+timer)\s+#?(\d+)$", text)
            tasks.append(Task("notification", "cancel_timer", parameters={"timer_id": int(match.group(1))}))

        elif re.match(r"^remind\s+me\s+in\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)(?:\s+to|\s*:)?\s*(.+)$", text):
            match = re.match(r"^remind\s+me\s+in\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)(?:\s+to|\s*:)?\s*(.+)$", user_input, re.IGNORECASE)
            amount = float(match.group(1))
            unit = match.group(2).lower()
            reminder_msg = match.group(3).strip()
            secs = amount if unit.startswith("s") else (amount * 3600 if unit.startswith("h") else amount * 60)
            tasks.append(Task("notification", "set_timer", parameters={"seconds": secs, "message": reminder_msg}))

        elif re.match(r"^(?:set\s+(?:a\s+)?)?timer(?:\s+for)?\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)(?:\s+(?:to|for)?\s*(.*))?$", text):
            match = re.match(r"^(?:set\s+(?:a\s+)?)?timer(?:\s+for)?\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)(?:\s+(?:to|for)?\s*(.*))?$", user_input, re.IGNORECASE)
            amount = float(match.group(1))
            unit = match.group(2).lower()
            timer_msg = (match.group(3) or "").strip() or "Timer alert"
            secs = amount if unit.startswith("s") else (amount * 3600 if unit.startswith("h") else amount * 60)
            tasks.append(Task("notification", "set_timer", parameters={"seconds": secs, "message": timer_msg}))

        elif re.match(r"^(?:notify\s+me|show\s+notification|notification:?)\s+(.+)$", text):
            match = re.match(r"^(?:notify\s+me|show\s+notification|notification:?)\s+(.+)$", user_input, re.IGNORECASE)
            tasks.append(Task("notification", "notify", parameters={"message": match.group(1).strip()}))

        elif text.startswith("open "):
            
            # Use original text case for matching but lower for the prefix
            open_in_match = re.match(r"^open\s+(.+)\s+in\s+(.+)$", user_input, re.IGNORECASE)
            if open_in_match:
                target = open_in_match.group(1).strip()
                app = open_in_match.group(2).strip()
                tasks.append(Task("terminal", "execute", f'open -a "{app}" "{target}"'))
            else:
                apps = self._split_targets(user_input[5:])
                for app in apps:
                    tasks.append(Task("app", "open", app))

        elif text.startswith("remember "):
            parts = user_input[9:].split(" is ", 1)
            # Check if there is an " is " (case insensitive)
            if len(parts) == 1:
                # Fallback in case they typed " IS "
                parts = re.split(r"(?i)\s+is\s+", user_input[9:], 1)
            if len(parts) == 2:
                tasks.append(Task("memory", "remember", parts[0].strip(), parameters={"value": parts[1].strip()}))
                
        elif text in ["what is my name", "what is my name?", "what's my name", "what's my name?", "who am i", "who am i?"]:
            tasks.append(Task("memory", "recall", "my name"))

        elif text.startswith("recall "):
            tasks.append(Task("memory", "recall", user_input[7:].strip()))
            
        elif text.startswith("forget "):
            tasks.append(Task("memory", "forget", user_input[7:].strip()))

        elif text.startswith("read file "):
            tasks.append(Task("file", "read", user_input[10:].strip()))
            
        elif text.startswith("read "):
            tasks.append(Task("file", "read", user_input[5:].strip()))

        elif text.startswith("create folder"):
            
            # Use multi-target parsing (Sprint 14.3)
            folders = self._split_targets(user_input[13:])
            for folder in folders:
                tasks.append(Task("file", "create_folder", folder))

        elif text.startswith("create file"):

            files = self._split_targets(user_input[11:])
            for file in files:
                tasks.append(Task("file", "create_file", file))
                
        elif text.startswith("delete "):
            
            # e.g., "delete file X and Y" or "delete X, Y"
            # Strip out "file " or "folder " if the user specified it to ensure target is just the path
            target_str = user_input[7:].strip()
            if target_str.lower().startswith("file "):
                target_str = target_str[5:].strip()
            elif target_str.lower().startswith("folder "):
                target_str = target_str[7:].strip()
                
            targets = self._split_targets(target_str)
            for target in targets:
                tasks.append(Task("file", "delete", target))

        if self.task_queue is not None:
            for task in tasks:
                if self._is_supported(task):
                    self.task_queue.enqueue(task)

        return tasks

    def _split_targets(self, text):
        """Split the small supported grammar: 'open A and B' or 'open A, B'."""
        return [target.strip() for target in re.split(r"\s*(?:,|\band\b)\s*", text) if target.strip()]

    def _is_supported(self, task):
        """Validate actions against a metadata snapshot when one is provided."""
        if self.capabilities is None:
            return True

        capability = self.capabilities.get(task.tool)
        return capability is not None and task.action in capability["supported_actions"]

    def _project_name(self, user_input):
        match = re.match(r"^create python project(?:\s+called)?\s+(.+)$", user_input, re.IGNORECASE)
        return match.group(1).strip() if match else ""
