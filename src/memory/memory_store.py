import json
from pathlib import Path

class MemoryStore:
    """In-memory store for session state and durable facts.
    
    Uses a local JSON file to persist facts across EDITH reboots,
    keeping the system lightweight as per EDITH_OS_ENGINEERING_RULES.md.
    """

    def __init__(self, storage_path="~/.edith_memory.json"):
        self.storage_path = Path(storage_path).expanduser()
        self._facts = {}
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._facts = json.load(f)
            except Exception:
                self._facts = {}

    def _save(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self._facts, f, indent=4)
        except Exception:
            pass

    def set(self, key, value):
        """Store a fact."""
        self._facts[key.lower()] = value
        self._save()

    def get(self, key):
        """Retrieve a fact."""
        return self._facts.get(key.lower())

    def delete(self, key):
        """Delete a fact."""
        if key.lower() in self._facts:
            del self._facts[key.lower()]
            self._save()
            return True
        return False

    def list_all(self):
        """Return a copy of all facts."""
        return dict(self._facts)
