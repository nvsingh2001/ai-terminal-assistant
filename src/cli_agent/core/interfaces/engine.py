from abc import ABC, abstractmethod
from typing import Dict, Any

class IAgentEngine(ABC):
    """Abstract interface for agent task execution engines (Strategy Pattern)."""
    
    @abstractmethod
    def run_task(self, user_request: str) -> Dict[str, str]:
        """
        Executes a user request and returns a dictionary with:
        - 'routing': intent summary / active skills info
        - 'execution': final response / tool execution output
        """
        pass
