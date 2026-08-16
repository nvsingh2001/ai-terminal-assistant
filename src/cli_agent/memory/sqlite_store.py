import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from cli_agent.core.interfaces.memory import IMemoryStore, MemoryEpisode, ProjectFact

DEFAULT_DB_PATH = os.path.expanduser("~/.cli-agent/memory.db")

class SQLiteMemoryStore(IMemoryStore):
    """
    High-Performance Production Long-Term Memory Store powered by SQLite with WAL mode.
    Manages Global, Project-Scoped, and Episodic Memory partitions.
    """
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # Tier 1: Global Preferences
            conn.execute("""
                CREATE TABLE IF NOT EXISTS global_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Tier 2: Project Knowledge & Facts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_facts (
                    project_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, key)
                )
            """)

            # Tier 3: Episodic Task History
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    user_prompt TEXT NOT NULL,
                    solution_summary TEXT NOT NULL,
                    tools_used TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_project ON episodic_history(project_id)")
            conn.commit()

    def get_global_preferences(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM global_preferences ORDER BY key")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def set_global_preference(self, key: str, value: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO global_preferences (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key.strip(), value.strip(), now)
            )
            conn.commit()

    def get_project_facts(self, project_id: str) -> List[ProjectFact]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT key, value, category, updated_at FROM project_facts WHERE project_id = ? ORDER BY category, key",
                (project_id,)
            )
            return [
                ProjectFact(
                    key=row["key"],
                    value=row["value"],
                    category=row["category"],
                    updated_at=row["updated_at"]
                )
                for row in cursor.fetchall()
            ]

    def set_project_fact(self, project_id: str, key: str, value: str, category: str = "general") -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO project_facts (project_id, key, value, category, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(project_id, key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at",
                (project_id, key.strip(), value.strip(), category.strip(), now)
            )
            conn.commit()

    def add_episode(
        self,
        project_id: str,
        user_prompt: str,
        solution_summary: str,
        tools_used: Optional[List[str]] = None
    ) -> int:
        now = datetime.utcnow().isoformat()
        tools_json = json.dumps(tools_used or [])
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO episodic_history (project_id, user_prompt, solution_summary, tools_used, timestamp) VALUES (?, ?, ?, ?, ?)",
                (project_id, user_prompt.strip(), solution_summary.strip(), tools_json, now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_episodes(self, project_id: str, limit: int = 5) -> List[MemoryEpisode]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, project_id, user_prompt, solution_summary, tools_used, timestamp "
                "FROM episodic_history WHERE project_id = ? ORDER BY id DESC LIMIT ?",
                (project_id, limit)
            )
            episodes = []
            for row in cursor.fetchall():
                try:
                    tools = json.loads(row["tools_used"])
                except Exception:
                    tools = []
                episodes.append(
                    MemoryEpisode(
                        id=row["id"],
                        project_id=row["project_id"],
                        user_prompt=row["user_prompt"],
                        solution_summary=row["solution_summary"],
                        tools_used=tools,
                        timestamp=row["timestamp"]
                    )
                )
            return episodes

    def search_episodes(self, project_id: str, query: str, limit: int = 3) -> List[MemoryEpisode]:
        keywords = [w.lower() for w in query.split() if len(w) > 3][:5]
        if not keywords:
            return self.get_recent_episodes(project_id, limit=limit)

        with self._get_connection() as conn:
            # Build simple SQL LIKE matching
            clauses = ["(LOWER(user_prompt) LIKE ? OR LOWER(solution_summary) LIKE ?)" for _ in keywords]
            sql = f"SELECT id, project_id, user_prompt, solution_summary, tools_used, timestamp FROM episodic_history WHERE project_id = ? AND ({' OR '.join(clauses)}) ORDER BY id DESC LIMIT ?"
            params = [project_id]
            for kw in keywords:
                pattern = f"%{kw}%"
                params.extend([pattern, pattern])
            params.append(limit)

            cursor = conn.execute(sql, params)
            episodes = []
            for row in cursor.fetchall():
                try:
                    tools = json.loads(row["tools_used"])
                except Exception:
                    tools = []
                episodes.append(
                    MemoryEpisode(
                        id=row["id"],
                        project_id=row["project_id"],
                        user_prompt=row["user_prompt"],
                        solution_summary=row["solution_summary"],
                        tools_used=tools,
                        timestamp=row["timestamp"]
                    )
                )
            return episodes

    def delete_memory(self, tier: str, key_or_id: str, project_id: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            if tier == "global":
                cursor = conn.execute("DELETE FROM global_preferences WHERE key = ?", (key_or_id,))
            elif tier == "project" and project_id:
                cursor = conn.execute("DELETE FROM project_facts WHERE project_id = ? AND key = ?", (project_id, key_or_id))
            elif tier == "episode":
                cursor = conn.execute("DELETE FROM episodic_history WHERE id = ?", (int(key_or_id),))
            else:
                return False
            conn.commit()
            return cursor.rowcount > 0

    def clear_project_memory(self, project_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM project_facts WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM episodic_history WHERE project_id = ?", (project_id,))
            conn.commit()
