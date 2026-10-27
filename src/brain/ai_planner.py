import json
import re
from brain.task import Task
from core.llm import LLM


class AIPlanner:
    """LLM-driven intent parser for the Brain subsystem.

    Converts arbitrary natural language into validated Task objects.
    Uses the universal LLM class so it works with local or cloud models.
    Falls back to an empty list on any failure.
    """

    def __init__(self, capabilities=None, llm=None):
        self.capabilities = capabilities or {}
        self.llm = llm or LLM()
        self._system_prompt = self._build_system_prompt()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, user_input):
        """Return a list of validated Task objects, or [] on any failure."""
        try:
            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_input},
            ]
            raw_response = self.llm.ask_sync(messages)
            parsed = self._extract_json(raw_response)
            return self._validate_tasks(parsed)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self):
        tool_lines = []
        for name, cap in self.capabilities.items():
            actions = ", ".join(sorted(cap["supported_actions"]))
            desc = cap.get("description", "")
            tool_lines.append(f"- {name} (actions: {actions}) — {desc}")

        tools_block = "\n".join(tool_lines)

        return f"""You are EDITH's task planner. Convert the user's request into a JSON task list.

AVAILABLE TOOLS:
{tools_block}

OUTPUT FORMAT:
Respond with ONLY a JSON array. No explanation, no markdown, no commentary.
[{{"tool": "...", "action": "...", "target": "...", "parameters": {{}}}}]

RULES:
- Use ONLY the tools and actions listed above.
- "target" is the primary argument (filename, app name, URL, math expression, shell command, etc.).
- "parameters" is for additional key-value data. For memory remember use {{"value": "the value"}}.
- For terminal commands: {{"tool":"terminal","action":"execute","target":"the shell command"}}.
- CRITICAL FOR BROWSER: Do NOT use the "browser" tool for questions, coding requests, math, explanations, or general knowledge. Return [] so EDITH answers directly in chat.
- Only use "browser" if the user explicitly commands to open a website or explicitly asks to search the web (e.g. "search Google for X", "open github.com").
- If the request is conversation, a coding question, advice, or general knowledge, return: []
- Do NOT invent tools or actions that are not listed.

EXAMPLES:
User: "give me a python code for fibonacci"
[]

User: "explain how black holes work"
[]

User: "make a folder called projects and add a readme"
[{{"tool":"file","action":"create_folder","target":"projects"}},{{"tool":"file","action":"create_file","target":"projects/README.md"}}]

User: "what time is it"
[{{"tool":"datetime","action":"current","target":""}}]

User: "open chrome and vscode"
[{{"tool":"app","action":"open","target":"chrome"}},{{"tool":"app","action":"open","target":"vscode"}}]

User: "remember my name is Tony"
[{{"tool":"memory","action":"remember","target":"my name","parameters":{{"value":"Tony"}}}}]

User: "search for latest space news on google"
[{{"tool":"browser","action":"search","target":"latest space news"}}]

User: "hey how are you"
[]"""

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(raw_text):
        """Extract a JSON array from LLM output, tolerating code fences."""
        text = raw_text.strip()

        # Strip markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Find the outermost JSON array
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []

        candidate = text[start : end + 1]

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        return []

    # ------------------------------------------------------------------
    # Task validation
    # ------------------------------------------------------------------

    def _validate_tasks(self, parsed_list):
        """Filter out any task whose tool or action is not in capabilities."""
        tasks = []
        for item in parsed_list:
            if not isinstance(item, dict):
                continue

            tool = item.get("tool", "")
            action = item.get("action", "")
            target = item.get("target", "")
            parameters = item.get("parameters", {})

            if not isinstance(parameters, dict):
                parameters = {}

            # Reject hallucinated tools or actions
            cap = self.capabilities.get(tool)
            if cap is None:
                continue
            if action not in cap["supported_actions"]:
                continue

            tasks.append(Task(
                tool=tool,
                action=action,
                target=target,
                parameters=parameters,
            ))

        return tasks
