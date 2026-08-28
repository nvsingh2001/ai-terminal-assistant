"""Isolation + real-agent fixtures for the opt-in DeepEval suite.

This directory is intentionally NOT under tests/, so pytest's conftest.py
discovery (same-directory-and-subdirectories only) does not share fixtures
with tests/conftest.py - the isolation pattern is duplicated here on purpose
to keep this suite fully self-contained and independently runnable via
`deepeval test run evals/`.
"""
import os
import subprocess

import pytest
from rich.console import Console

from cli_agent.container import ServiceContainer
from cli_agent.core.config_manager import AgentConfig, config_manager
from cli_agent.core.safety.rollback import rollback_manager
from cli_agent.memory.manager import tri_tier_memory
from cli_agent.memory.sqlite_store import SQLiteMemoryStore
from cli_agent.services.memory_manager import session_memory

EVAL_MODEL_NAME = os.getenv("EVAL_MODEL_NAME", "openai/gpt-4o-mini")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    import cli_agent.core.config_manager as config_manager_module

    monkeypatch.setattr(
        config_manager_module, "CONFIG_FILE_PATH", str(tmp_path / ".cli-agent" / "config.yaml")
    )

    original_config = config_manager.config
    config_manager.config = AgentConfig(model_name=EVAL_MODEL_NAME, execution_policy="yolo")

    original_base_dir = rollback_manager.base_dir
    original_session_dir = rollback_manager.session_dir
    isolated_snapshot_dir = str(tmp_path / ".cli-agent" / "snapshots")
    rollback_manager.base_dir = isolated_snapshot_dir
    rollback_manager.session_dir = os.path.join(isolated_snapshot_dir, rollback_manager.session_id)
    os.makedirs(rollback_manager.session_dir, exist_ok=True)
    rollback_manager.transaction_stack = []
    rollback_manager._current_transaction = None

    original_store = tri_tier_memory.store
    tri_tier_memory.store = SQLiteMemoryStore(db_path=str(tmp_path / ".cli-agent" / "memory.db"))

    original_history = session_memory.history
    session_memory.history = []

    yield

    config_manager.config = original_config
    rollback_manager.base_dir = original_base_dir
    rollback_manager.session_dir = original_session_dir
    tri_tier_memory.store = original_store
    session_memory.history = original_history


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """A throwaway git repo the agent can operate on for file/shell/git scenarios."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "eval@aegis.local"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Aegis Eval"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Scratch repo for Aegis evals\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.fixture
def container(scratch_repo):
    """A real ServiceContainer pointed at EVAL_MODEL_NAME, ready to run real tasks."""
    return ServiceContainer.create_default(console=Console(), prompt_session=None)
