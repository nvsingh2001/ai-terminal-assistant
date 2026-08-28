"""
Shared test isolation fixtures.

The production code uses several module-level singletons (config_manager,
rollback_manager, tri_tier_memory, session_memory) that are constructed once
at import time and resolve `~/.cli-agent/...` paths eagerly. Left unpatched,
tests would read/write the developer's or CI runner's real home directory
config, snapshots, and memory DB. Every fixture below resets those singletons
onto tmp_path-scoped state before each test and restores the originals after.
"""
import os
import tempfile

import pytest

from cli_agent.core.config_manager import AgentConfig, config_manager
from cli_agent.core.safety.rollback import rollback_manager
from cli_agent.memory.manager import tri_tier_memory
from cli_agent.memory.sqlite_store import SQLiteMemoryStore
from cli_agent.services.memory_manager import session_memory


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Redirects HOME/USERPROFILE and every singleton's on-disk state to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    # config_manager.py resolves CONFIG_FILE_PATH as a module-level constant at
    # import time, so patching HOME alone does not reach it - patch the
    # resolved constant directly. It is read fresh from the module namespace
    # on every load_config()/save_config() call, so this works.
    import cli_agent.core.config_manager as config_manager_module

    isolated_config_path = str(tmp_path / ".cli-agent" / "config.yaml")
    monkeypatch.setattr(config_manager_module, "CONFIG_FILE_PATH", isolated_config_path)

    # Reset the config singleton to a fresh in-memory config, with model_name
    # pre-set so AgentConfig.__post_init__ skips discover_working_model()'s
    # network probe to localhost:11434 on every single test.
    original_config = config_manager.config
    config_manager.config = AgentConfig(model_name="ollama/qwen3.5:4b")

    # rollback_manager and tri_tier_memory are singletons already constructed
    # at import time with real ~/.cli-agent paths baked in - swap their
    # instance state directly rather than relying on env/module patches that
    # only affect objects constructed after this point.
    original_base_dir = rollback_manager.base_dir
    original_session_dir = rollback_manager.session_dir
    original_stack = rollback_manager.transaction_stack
    original_current_tx = rollback_manager._current_transaction

    isolated_snapshot_dir = str(tmp_path / ".cli-agent" / "snapshots")
    rollback_manager.base_dir = isolated_snapshot_dir
    rollback_manager.session_dir = os.path.join(isolated_snapshot_dir, rollback_manager.session_id)
    os.makedirs(rollback_manager.session_dir, exist_ok=True)
    rollback_manager.transaction_stack = []
    rollback_manager._current_transaction = None

    original_store = tri_tier_memory.store
    isolated_db_path = str(tmp_path / ".cli-agent" / "memory.db")
    tri_tier_memory.store = SQLiteMemoryStore(db_path=isolated_db_path)

    original_history = session_memory.history
    session_memory.history = []

    yield

    config_manager.config = original_config
    rollback_manager.base_dir = original_base_dir
    rollback_manager.session_dir = original_session_dir
    rollback_manager.transaction_stack = original_stack
    rollback_manager._current_transaction = original_current_tx
    tri_tier_memory.store = original_store
    session_memory.history = original_history


@pytest.fixture
def yolo_policy():
    """Sets execution_policy='yolo' for tests exercising write/edit skill paths
    that would otherwise block on an interactive approval prompt."""
    original = config_manager.config.execution_policy
    config_manager.config.execution_policy = "yolo"
    yield
    config_manager.config.execution_policy = original


@pytest.fixture
def work_dir(tmp_path, monkeypatch):
    """A throwaway cwd for skills that operate relative to os.getcwd()."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
