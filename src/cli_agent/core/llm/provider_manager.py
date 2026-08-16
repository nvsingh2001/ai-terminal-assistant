import os
import requests
from typing import Dict, Any, List, Optional
import litellm
from cli_agent.core.llm.llama_cpp import LlamaCppEngine


class HybridLLMEngine:
    """
    Unified Hybrid LLM Engine Router.
    Routes requests between:
    - Native Local llama.cpp (GGUF in-memory execution)
    - Local/Remote Ollama via LiteLLM (with explicit localhost override)
    - Cloud APIs (OpenAI, Anthropic Claude, Google Gemini) via LiteLLM
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "ollama/qwen3.5:4b")
        self.llama_cpp_engine = LlamaCppEngine()
        self._ollama_base = None  # Cached after first probe

    def _get_ollama_base(self) -> str:
        """Determines Ollama base URL. Prefers localhost, falls back to OLLAMA_API_BASE."""
        if self._ollama_base:
            return self._ollama_base

        local_base = "http://localhost:11434"
        remote_base = os.getenv("OLLAMA_API_BASE", "")

        try:
            requests.get(f"{local_base}/api/tags", timeout=2)
            self._ollama_base = local_base
        except Exception:
            self._ollama_base = remote_base if remote_base else local_base

        return self._ollama_base

    def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Routes completion to local GGUF, Ollama via LiteLLM, or Cloud provider."""
        # 1. Check if model specifies local GGUF llama.cpp execution
        if self.model_name.startswith("llama-cpp") or self.model_name.endswith(".gguf") or (
            not self.model_name.startswith(("ollama/", "gemini/", "openai/", "anthropic/"))
            and os.path.exists(self.model_name)
        ):
            gguf_engine = LlamaCppEngine(model_path=self.model_name)
            res = gguf_engine.generate_completion(messages, tools)
            if not res.get("error"):
                return res

        # 2. Build LiteLLM kwargs
        provider_model = self.model_name
        if "/" not in provider_model and not provider_model.endswith(".gguf"):
            provider_model = f"ollama/{provider_model}"

        kwargs = {
            "model": provider_model,
            "messages": messages,
            "timeout": 180
        }

        # 3. Ollama models: explicitly override api_base to localhost
        #    This bypasses the OLLAMA_API_BASE env var (which may point to cloud)
        if provider_model.startswith("ollama/"):
            kwargs["api_base"] = self._get_ollama_base()
            ollama_key = os.getenv("OLLAMA_API_KEY", "")
            if ollama_key:
                kwargs["api_key"] = ollama_key

        # 4. Add tools if provided
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 5. Execute via LiteLLM
        try:
            return litellm.completion(**kwargs)
        except Exception as e:
            err_str = str(e)

            # If tool calling failed, retry without tools
            if tools and ("tool" in err_str.lower() or "schema" in err_str.lower() or "not support" in err_str.lower()):
                try:
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    return litellm.completion(**kwargs)
                except Exception:
                    pass

            # Connection errors
            if "connection" in err_str.lower() or "timeout" in err_str.lower():
                base = kwargs.get("api_base", "unknown")
                return {
                    "error": f"Cannot connect to model server at {base}.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Start Ollama: `ollama serve`\n"
                             f"2. Or use `/model` to switch to a different model"
                }

            # Model not found
            if "not found" in err_str.lower() or "404" in err_str:
                model_tag = provider_model.replace("ollama/", "")
                return {
                    "error": f"Model '{provider_model}' was not found.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Pull the model: `ollama pull {model_tag}`\n"
                             f"2. Or use `/model` to switch to a different model\n"
                             f"3. Or set a cloud API key (`export GEMINI_API_KEY=...`)"
                }

            raise e
