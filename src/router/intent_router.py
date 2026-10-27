class IntentRouter:

    def route(self, user_input):

        text = user_input.lower()

        operators = ["+", "-", "*", "/", "%", "**"]

        if any(op in text for op in operators):
            return "calculator"

        if any(
            word in text
            for word in [
                "create",
                "delete",
                "list",
                "rename",
                "move",
                "copy"
            ]
        ):
            return "file"

        if "time" in text or "date" in text:
            return "datetime"

        return "llm"