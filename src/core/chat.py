from memory.memory_manager import MemoryManager


class ChatSession:

    def __init__(self):

        self.memory = MemoryManager()
        self.history = self.memory.load()

    def add_user(self, message):

        self.history.append({
            "role": "user",
            "content": message
        })

        self.memory.save(self.history)

    def add_assistant(self, message):

        self.history.append({
            "role": "assistant",
            "content": message
        })

        self.memory.save(self.history)

    def get_history(self):
        return self.history

    def clear(self):

        self.history = []
        self.memory.clear()