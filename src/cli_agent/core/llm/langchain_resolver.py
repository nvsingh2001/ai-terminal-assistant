import os
import requests
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from cli_agent.core.interfaces.model import IModelResolver


class LangChainModelResolver(IModelResolver):
    """
    Translates model configurations into LangChain BaseChatModel instances for LangGraph.
    Supports Ollama Local/Cloud, Google Gemini, OpenAI, and Anthropic.
    """

    def _is_locally_installed(self, model_tag: str) -> bool:
        """Checks if a model is installed in the local Ollama instance."""
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=1)
            if r.status_code == 200:
                installed = r.json().get("models", [])
                installed_names = [m.get("name", "").lower() for m in installed]
                tag_lower = model_tag.lower()
                if tag_lower in installed_names or f"{tag_lower}:latest" in installed_names:
                    return True
                base_names = [name.split(":")[0] for name in installed_names]
                if tag_lower.split(":")[0] in base_names:
                    return True
        except Exception:
            pass
        return False

    def resolve_model(self, model_name: str) -> BaseChatModel:
        """Returns configured LangChain BaseChatModel instance."""
        clean = model_name.strip()

        if clean.startswith("gemini/") or clean.startswith("google/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "missing-key"
            return ChatGoogleGenerativeAI(
                model=tag,
                google_api_key=key,
                temperature=0.1,
            )

        elif clean.startswith("openai/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("OPENAI_API_KEY") or "missing-key"
            return ChatOpenAI(
                model=tag,
                api_key=key,
                temperature=0.1,
            )

        elif clean.startswith("anthropic/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("ANTHROPIC_API_KEY") or "missing-key"
            return ChatAnthropic(
                model=tag,
                api_key=key,
                temperature=0.1,
            )

        else:
            model_tag = clean.replace("ollama/", "")

            # If local Ollama
            if self._is_locally_installed(model_tag):
                return ChatOpenAI(
                    model=model_tag,
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                    temperature=0.1,
                )

            # Ollama Cloud / Remote API Base
            remote_base = os.getenv("OLLAMA_API_BASE", "https://ollama.com/v1").rstrip("/")
            if not remote_base.endswith("/v1"):
                remote_base = f"{remote_base}/v1"
            api_key = os.getenv("OLLAMA_API_KEY", "ollama")

            return ChatOpenAI(
                model=model_tag,
                base_url=remote_base,
                api_key=api_key,
                temperature=0.1,
                request_timeout=120.0,
            )

    def resolve_model_string(self, model_name: str) -> str:
        """Returns raw model name string."""
        return model_name
