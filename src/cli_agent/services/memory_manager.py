import os
from typing import List, Dict

MAX_MEMORY_TURNS = 5      # Maximum turns kept in sliding window
MAX_SUMMARY_CHARS = 350   # Capped length per turn summary to avoid memory bloat

class ConversationMemory:
    """
    Managed multi-turn conversation memory with sliding window limits
    and summary compaction to prevent token window overload.
    """
    def __init__(self, max_turns: int = MAX_MEMORY_TURNS):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def add_turn(self, user_request: str, category: str, execution_output: str):
        """Adds a compact summary of a conversation turn to the sliding window."""
        # Clean and truncate execution output to keep memory lightweight
        summary_text = execution_output.replace("\n", " ").strip()
        if len(summary_text) > MAX_SUMMARY_CHARS:
            summary_text = summary_text[:MAX_SUMMARY_CHARS] + "..."

        turn_entry = {
            "user": user_request,
            "category": category,
            "summary": summary_text or "Task executed."
        }
        self.history.append(turn_entry)

        # Enforce sliding window cap
        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def get_formatted_context(self) -> str:
        """Returns a formatted, lightweight context string of recent turns."""
        if not self.history:
            return "No prior conversation history."

        lines = []
        for idx, turn in enumerate(self.history, start=1):
            lines.append(f"- Turn {idx}: User asked \"{turn['user']}\" | Category: {turn['category']} | Summary: {turn['summary']}")
        return "\n".join(lines)

    def clear(self):
        """Resets conversation memory."""
        self.history.clear()

# Global memory singleton for active CLI session
session_memory = ConversationMemory()
