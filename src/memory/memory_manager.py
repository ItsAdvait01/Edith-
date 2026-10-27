import json


class MemoryManager:

    def __init__(self):
        self.file_path = "data/chat_history.json"

    def load(self):

        try:
            with open(self.file_path, "r") as file:
                return json.load(file)

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save(self, history):

        with open(self.file_path, "w") as file:
            json.dump(history, file, indent=4)

    def clear(self):

        with open(self.file_path, "w") as file:
            json.dump([], file, indent=4)