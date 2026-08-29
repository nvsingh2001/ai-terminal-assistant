"""LangChainModelResolver prefix dispatch. Constructing these LangChain chat
model clients does not itself make a network call (confirmed locally), so
these run with no API keys and no network access."""
import pytest
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from cli_agent.core.llm.langchain_resolver import LangChainModelResolver


@pytest.fixture(autouse=True)
def clear_provider_env(monkeypatch):
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_API_KEY", "OLLAMA_API_BASE"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def resolver():
    return LangChainModelResolver()


def test_gemini_prefix_resolves_to_chat_google_genai(resolver):
    model = resolver.resolve_model("gemini/gemini-2.0-flash")
    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model == "gemini-2.0-flash"


def test_google_prefix_is_equivalent_to_gemini_prefix(resolver):
    model = resolver.resolve_model("google/gemini-2.0-flash")
    assert isinstance(model, ChatGoogleGenerativeAI)


def test_openai_prefix_resolves_to_chat_openai(resolver):
    model = resolver.resolve_model("openai/gpt-4o-mini")
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"


def test_anthropic_prefix_resolves_to_chat_anthropic(resolver):
    model = resolver.resolve_model("anthropic/claude-3-5-sonnet")
    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-3-5-sonnet"


def test_bare_model_name_probes_local_ollama_first(resolver, monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen3.5:4b"}]}

    monkeypatch.setattr(
        "cli_agent.core.llm.langchain_resolver.requests.get",
        lambda *a, **k: FakeResponse(),
    )
    model = resolver.resolve_model("qwen3.5:4b")
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "qwen3.5:4b"
    assert model.openai_api_base == "http://localhost:11434/v1"


def test_ollama_prefix_is_stripped_before_local_probe(resolver, monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen3.5:4b"}]}

    monkeypatch.setattr(
        "cli_agent.core.llm.langchain_resolver.requests.get",
        lambda *a, **k: FakeResponse(),
    )
    model = resolver.resolve_model("ollama/qwen3.5:4b")
    assert model.model_name == "qwen3.5:4b"


def test_not_installed_locally_falls_back_to_remote_ollama_cloud(resolver, monkeypatch):
    monkeypatch.setattr(
        "cli_agent.core.llm.langchain_resolver.requests.get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    model = resolver.resolve_model("gemma4:31b-cloud")
    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "https://ollama.com/v1"


def test_remote_ollama_base_env_var_is_respected(resolver, monkeypatch):
    monkeypatch.setattr(
        "cli_agent.core.llm.langchain_resolver.requests.get",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()),
    )
    monkeypatch.setenv("OLLAMA_API_BASE", "https://custom.example.com")
    model = resolver.resolve_model("gemma4:31b-cloud")
    assert model.openai_api_base == "https://custom.example.com/v1"


def test_resolve_model_string_returns_raw_name(resolver):
    assert resolver.resolve_model_string("openai/gpt-4o-mini") == "openai/gpt-4o-mini"
