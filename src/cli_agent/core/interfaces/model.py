from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IModelResolver(ABC):
    """Abstract interface for mapping configuration model strings to provider URIs."""
    
    @abstractmethod
    def resolve_model_string(self, model_name: str) -> str:
        """Translates user model string to underlying framework provider model string."""
        pass
