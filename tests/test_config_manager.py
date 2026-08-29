"""Config persistence and model auto-discovery, isolated to a tmp_path config
file via the autouse conftest fixture (never touches the real ~/.cli-agent)."""
import os

import pytest

import cli_agent.core.config_manager as config_manager_module
from cli_agent.core.config_manager import AgentConfig, ConfigManager, discover_working_model


@pytest.fixture(autouse=True)
def clear_provider_env(monkeypatch):
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_first_load_creates_default_config_file():
    assert not os.path.exists(config_manager_module.CONFIG_FILE_PATH)
    mgr = ConfigManager()
    assert os.path.exists(config_manager_module.CONFIG_FILE_PATH)
    assert mgr.config.execution_policy == "trusted-read"


def test_set_model_persists_across_instances():
    mgr = ConfigManager()
    mgr.set_model("openai/gpt-4o-mini")

    reloaded = ConfigManager()
    assert reloaded.config.model_name == "openai/gpt-4o-mini"


@pytest.mark.parametrize("policy", ["strict", "trusted-read", "yolo"])
def test_set_execution_policy_accepts_valid_values(policy):
    mgr = ConfigManager()
    mgr.set_execution_policy(policy)
    assert mgr.config.execution_policy == policy


def test_set_execution_policy_rejects_invalid_value():
    mgr = ConfigManager()
    mgr.set_execution_policy("trusted-read")
    mgr.set_execution_policy("yeet-mode")
    assert mgr.config.execution_policy == "trusted-read"


def test_set_api_key_updates_env_config_and_dotenv():
    mgr = ConfigManager()
    mgr.set_api_key("OPENAI_API_KEY", "sk-test-123")

    assert os.environ["OPENAI_API_KEY"] == "sk-test-123"
    assert mgr.config.api_keys["openai"] == "sk-test-123"

    env_path = os.path.join(os.path.expanduser("~/.cli-agent"), ".env")
    assert os.path.exists(env_path)
    with open(env_path) as f:
        assert "OPENAI_API_KEY=sk-test-123" in f.read()


def test_set_api_key_updates_existing_dotenv_line_in_place():
    mgr = ConfigManager()
    mgr.set_api_key("OPENAI_API_KEY", "sk-old")
    mgr.set_api_key("OPENAI_API_KEY", "sk-new")

    env_path = os.path.join(os.path.expanduser("~/.cli-agent"), ".env")
    with open(env_path) as f:
        lines = f.read().splitlines()
    matching = [l for l in lines if l.startswith("OPENAI_API_KEY=")]
    assert matching == ["OPENAI_API_KEY=sk-new"]


# --- discover_working_model ------------------------------------------------

def test_discover_working_model_respects_existing_choice():
    assert discover_working_model("openai/gpt-4o") == "openai/gpt-4o"


def test_discover_working_model_uses_local_ollama_when_available(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen3.5:4b"}, {"name": "nomic-embed-text"}]}

    monkeypatch.setattr(
        config_manager_module.requests, "get", lambda *a, **k: FakeResponse()
    )
    assert discover_working_model(None) == "ollama/qwen3.5:4b"


def test_discover_working_model_skips_embedding_only_models(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "nomic-embed-text"}]}

    monkeypatch.setattr(
        config_manager_module.requests, "get", lambda *a, **k: FakeResponse()
    )
    # No usable generation model locally, no API keys set -> hardcoded fallback.
    assert discover_working_model(None) == "ollama/gemma4:31b-cloud"


def test_discover_working_model_falls_back_to_gemini_key(monkeypatch):
    monkeypatch.setattr(
        config_manager_module.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert discover_working_model(None) == "gemini/gemini-1.5-flash"


def test_discover_working_model_falls_back_to_openai_key(monkeypatch):
    monkeypatch.setattr(
        config_manager_module.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert discover_working_model(None) == "openai/gpt-4o-mini"


def test_discover_working_model_falls_back_to_anthropic_key(monkeypatch):
    monkeypatch.setattr(
        config_manager_module.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert discover_working_model(None) == "anthropic/claude-3-5-sonnet"


def test_discover_working_model_hardcoded_fallback_when_nothing_available(monkeypatch):
    monkeypatch.setattr(
        config_manager_module.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    assert discover_working_model(None) == "ollama/gemma4:31b-cloud"
