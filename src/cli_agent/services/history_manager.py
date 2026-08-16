import os
from typing import List

HISTORY_FILE = os.path.expanduser("~/.cli-agent/history")
MAX_HISTORY_ENTRIES = 200

class HistoryManager:
    """Manages persistent user command prompt history for TUI and CLI input navigation."""
    def __init__(self, filepath: str = HISTORY_FILE, max_entries: int = MAX_HISTORY_ENTRIES):
        self.filepath = filepath
        self.max_entries = max_entries
        self.history: List[str] = []
        self.load_history()

    def load_history(self):
        """Loads command history from persistent storage."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    self.history = lines[-self.max_entries:]
            except Exception:
                self.history = []

    def add(self, command: str):
        """Adds a command to history and persists to disk."""
        cmd = command.strip()
        if not cmd:
            return
            
        # Avoid duplicate consecutive entries
        if self.history and self.history[-1] == cmd:
            return
            
        self.history.append(cmd)
        if len(self.history) > self.max_entries:
            self.history.pop(0)

        # Persist
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(self.history) + "\n")
        except Exception:
            pass

    def get_entries(self) -> List[str]:
        return list(self.history)

# Global history singleton
history_manager = HistoryManager()
