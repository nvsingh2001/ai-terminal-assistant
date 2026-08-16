from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

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

    @abstractmethod
    def set_model(self, model_name: str):
        """Updates the active model for the engine."""
        pass

    @abstractmethod
    def set_verbose(self, verbose: bool):
        """Sets verbose trace mode."""
        pass
