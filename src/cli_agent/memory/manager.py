import hashlib
import os
import subprocess
from typing import Any, Dict, List, Optional

from cli_agent.core.interfaces.memory import IMemoryStore, MemoryEpisode, ProjectFact
from cli_agent.memory.sqlite_store import SQLiteMemoryStore


def get_project_identifier() -> str:
    """
    Derives a consistent, human-readable yet unique project identifier.
    Uses Git root directory name or current working directory.
    """
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if git_root:
            proj_name = os.path.basename(git_root)
            path_hash = hashlib.sha256(git_root.encode()).hexdigest()[:6]
            return f"{proj_name}_{path_hash}"
    except Exception:
        pass

    cwd = os.getcwd()
    proj_name = os.path.basename(cwd)
    path_hash = hashlib.sha256(cwd.encode()).hexdigest()[:6]
    return f"{proj_name}_{path_hash}"


class TriTierMemoryManager:
    """
    Production Tri-Tier Memory Manager.
    - Tier 1: Global User Preferences (~/.cli-agent/memory.db)
    - Tier 2: Project-Scoped Architectural & Environment Knowledge
    - Tier 3: Episodic Task Recall & Solution History
    """

    def __init__(self, store: Optional[IMemoryStore] = None):
        self.store: IMemoryStore = store or SQLiteMemoryStore()
        self.project_id: str = get_project_identifier()

    def update_project_context(self):
        """Refreshes active project ID based on current directory."""
        self.project_id = get_project_identifier()

    # Tier 1: Global
    def get_global_preferences(self) -> Dict[str, str]:
        return self.store.get_global_preferences()

    def set_global_preference(self, key: str, value: str):
        self.store.set_global_preference(key, value)

    # Tier 2: Project
    def get_project_facts(self) -> List[ProjectFact]:
        return self.store.get_project_facts(self.project_id)

    def set_project_fact(self, key: str, value: str, category: str = "general"):
        self.store.set_project_fact(self.project_id, key, value, category)

    # Tier 3: Episodic
    def record_episode(
        self,
        user_prompt: str,
        solution_summary: str,
        tools_used: Optional[List[str]] = None,
    ) -> int:
        return self.store.add_episode(
            self.project_id, user_prompt, solution_summary, tools_used
        )

    def get_recent_episodes(self, limit: int = 5) -> List[MemoryEpisode]:
        return self.store.get_recent_episodes(self.project_id, limit=limit)

    def search_episodes(self, query: str, limit: int = 3) -> List[MemoryEpisode]:
        return self.store.search_episodes(self.project_id, query, limit=limit)

    def delete_memory(self, tier: str, key_or_id: str) -> bool:
        return self.store.delete_memory(tier, key_or_id, self.project_id)

    def clear_project(self):
        self.store.clear_project_memory(self.project_id)

    def get_formatted_prompt_memory(self, current_query: Optional[str] = None) -> str:
        """
        Generates a token-compact (< 300 tokens) prompt block containing:
        - Active global preferences
        - Project architectural facts
        - Relevant past episodic solutions
        """
        sections = []

        # 1. Global Preferences
        global_prefs = self.get_global_preferences()
        if global_prefs:
            pref_lines = [f"  • {k}: {v}" for k, v in global_prefs.items()]
            sections.append("Global User Preferences:\n" + "\n".join(pref_lines))

        # 2. Project Knowledge
        project_facts = self.get_project_facts()
        if project_facts:
            fact_lines = [
                f"  • [{f.category}] {f.key}: {f.value}" for f in project_facts
            ]
            sections.append(
                f"Project Architecture & Rules ({self.project_id}):\n"
                + "\n".join(fact_lines)
            )

        # 3. Relevant Past Episodes
        if current_query:
            episodes = self.search_episodes(current_query, limit=2)
            if episodes:
                ep_lines = []
                for ep in episodes:
                    tools_str = (
                        f" (Tools: {', '.join(ep.tools_used)})" if ep.tools_used else ""
                    )
                    summary = ep.solution_summary[:150].replace("\n", " ")
                    ep_lines.append(
                        f"  • Prior task '{ep.user_prompt[:60]}'{tools_str} -> {summary}"
                    )
                sections.append("Relevant Past Solutions:\n" + "\n".join(ep_lines))

        if not sections:
            return ""

        return "\n\n".join(sections)


# Global default instance
tri_tier_memory = TriTierMemoryManager()
