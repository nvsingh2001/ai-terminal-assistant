import os
import requests
from typing import Any
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.ollama import OllamaProvider
from cli_agent.core.interfaces.model import IModelResolver

class ModelResolver(IModelResolver):
    """
    Translates user model configurations into Model instances compatible with PydanticAI.
    Smart-routes between local Ollama (if pulled locally), Ollama Cloud, Gemini, OpenAI, and Anthropic.
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
                # Check base name prefix
                base_names = [name.split(":")[0] for name in installed_names]
                if tag_lower.split(":")[0] in base_names:
                    return True
        except Exception:
            pass
        return False

    def resolve_model(self, model_name: str) -> Any:
        """Returns configured PydanticAI Model instance or model string."""
        clean = model_name.strip()

        if clean.startswith("gemini/") or clean.startswith("google/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
            provider = GoogleProvider(api_key=key or "missing-key")
            return GoogleModel(tag, provider=provider)

        elif clean.startswith("openai/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("OPENAI_API_KEY") or ""
            provider = OpenAIProvider(api_key=key or "missing-key")
            return OpenAIChatModel(tag, provider=provider)

        elif clean.startswith("anthropic/"):
            tag = clean.split("/", 1)[1]
            key = os.getenv("ANTHROPIC_API_KEY") or ""
            provider = AnthropicProvider(api_key=key or "missing-key")
            return AnthropicModel(tag, provider=provider)

        else:
            model_tag = clean.replace("ollama/", "")
            
            # If the model is pulled locally in localhost:11434, use local OllamaProvider
            if self._is_locally_installed(model_tag):
                provider = OllamaProvider(base_url="http://localhost:11434/v1")
                return OpenAIChatModel(model_tag, provider=provider)
            
            # Otherwise, route to Ollama Cloud / Remote API Base with auth key
            remote_base = os.getenv("OLLAMA_API_BASE", "https://ollama.com/v1").rstrip("/")
            if not remote_base.endswith("/v1"):
                remote_base = f"{remote_base}/v1"
            api_key = os.getenv("OLLAMA_API_KEY", "ollama")
            provider = OpenAIProvider(base_url=remote_base, api_key=api_key)
            return OpenAIChatModel(model_tag, provider=provider)

    def resolve_model_string(self, model_name: str) -> str:
        """Legacy string resolution."""
        res = self.resolve_model(model_name)
        if isinstance(res, str):
            return res
        return model_name
