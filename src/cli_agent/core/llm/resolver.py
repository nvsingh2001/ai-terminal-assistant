import os
import requests
from typing import Any, Union
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from cli_agent.core.interfaces.model import IModelResolver

class ModelResolver(IModelResolver):
    """
    Translates user model configurations into Model instances compatible with PydanticAI.
    Ensures Ollama connects to localhost:11434/v1 with direct OllamaProvider.
    """
    def _get_ollama_base(self) -> str:
        """Determines reachable Ollama base URL with /v1 suffix."""
        local_base = "http://localhost:11434"
        remote_base = os.getenv("OLLAMA_API_BASE", "")

        try:
            requests.get(f"{local_base}/api/tags", timeout=2)
            chosen_base = local_base
        except Exception:
            chosen_base = remote_base if remote_base else local_base

        if not chosen_base.endswith("/v1"):
            chosen_base = f"{chosen_base.rstrip('/')}/v1"

        return chosen_base

    def resolve_model(self, model_name: str) -> Any:
        """Returns configured PydanticAI Model instance or model string."""
        clean = model_name.strip()

        if clean.startswith("gemini/") or clean.startswith("google/"):
            return f"google-gla:{clean.split('/', 1)[1]}"

        elif clean.startswith("openai/"):
            return f"openai:{clean.split('/', 1)[1]}"

        elif clean.startswith("anthropic/"):
            return f"anthropic:{clean.split('/', 1)[1]}"

        elif clean.startswith("ollama/"):
            model_tag = clean.replace("ollama/", "")
            base_url = self._get_ollama_base()
            provider = OllamaProvider(base_url=base_url)
            return OpenAIChatModel(model_tag, provider=provider)

        else:
            base_url = self._get_ollama_base()
            provider = OllamaProvider(base_url=base_url)
            return OpenAIChatModel(clean, provider=provider)

    def resolve_model_string(self, model_name: str) -> str:
        """Legacy string resolution."""
        res = self.resolve_model(model_name)
        if isinstance(res, str):
            return res
        return model_name
