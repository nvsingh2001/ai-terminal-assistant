from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class CommandContext:
    """Encapsulates dependencies required by slash commands."""
    prompt_session: Any
    config_manager: Any
    skill_registry: Any
    memory_store: Any
    console: Any
    engine: Optional[Any] = None

class ISlashCommand(ABC):
    """Command Pattern interface for all interactive terminal slash commands."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command trigger name (e.g. '/model')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Command summary shown in help palette."""
        pass

    @abstractmethod
    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        """
        Executes the command logic.
        Returns True if command handled the request and REPL should prompt again.
        """
        pass
