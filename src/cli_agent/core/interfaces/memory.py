from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEpisode:
    id: int
    project_id: str
    user_prompt: str
    solution_summary: str
    tools_used: List[str]
    timestamp: str


@dataclass
class ProjectFact:
    key: str
    value: str
    category: str
    updated_at: str


class IMemoryStore(ABC):
    """
    Abstract interface for Persistent Long-Term Memory Storage (Strategy Pattern).
    Supports partitioned Global, Project-Specific, and Episodic data tiers.
    """

    @abstractmethod
    def get_global_preferences(self) -> Dict[str, str]:
        """Retrieves all global user preferences."""
        pass

    @abstractmethod
    def set_global_preference(self, key: str, value: str) -> None:
        """Sets or updates a global user preference."""
        pass

    @abstractmethod
    def get_project_facts(self, project_id: str) -> List[ProjectFact]:
        """Retrieves all architectural and environment facts for a specific project."""
        pass

    @abstractmethod
    def set_project_fact(
        self, project_id: str, key: str, value: str, category: str = "general"
    ) -> None:
        """Sets or updates a project-specific fact."""
        pass

    @abstractmethod
    def add_episode(
        self,
        project_id: str,
        user_prompt: str,
        solution_summary: str,
        tools_used: Optional[List[str]] = None,
    ) -> int:
        """Records a completed task episode in episodic memory."""
        pass

    @abstractmethod
    def get_recent_episodes(
        self, project_id: str, limit: int = 5
    ) -> List[MemoryEpisode]:
        """Retrieves most recent task episodes for the project."""
        pass

    @abstractmethod
    def search_episodes(
        self, project_id: str, query: str, limit: int = 3
    ) -> List[MemoryEpisode]:
        """Searches past episodes by keyword relevance."""
        pass

    @abstractmethod
    def delete_memory(
        self, tier: str, key_or_id: str, project_id: Optional[str] = None
    ) -> bool:
        """Deletes a memory record from the specified tier."""
        pass

    @abstractmethod
    def clear_project_memory(self, project_id: str) -> None:
        """Clears all project knowledge and episodes for a project."""
        pass
