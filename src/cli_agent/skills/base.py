from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SkillManifest:
    """Metadata definition for a system or user skill."""

    name: str
    description: str
    version: str = "1.0.0"
    requires_approval: bool = False
    parameters_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Execution output result of a skill handler."""

    success: bool
    output: str
    error: Optional[str] = None


class BaseSkill(ABC):
    """Abstract Base Class for all CLI Agent Skills."""

    @property
    @abstractmethod
    def manifest(self) -> SkillManifest:
        """Returns the skill manifest definition."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Executes the skill action with the provided parameters."""
        pass
