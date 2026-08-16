import os
from typing import Dict, Any, List, Optional
import litellm
from cli_agent.core.llm.llama_cpp import LlamaCppEngine

class HybridLLMEngine:
    """
    Unified Hybrid LLM Engine Router.
    Seamlessly routes requests between:
    - Native Local llama.cpp (GGUF in-memory execution)
    - Local Ollama Engine
    - Cloud APIs (OpenAI, Anthropic Claude, Google Gemini)
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "ollama/gemma4:31b-cloud")
        self.llama_cpp_engine = LlamaCppEngine()

    def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Routes completion to local GGUF, local Ollama, or Cloud provider."""
        # 1. Check if model specifies local GGUF llama.cpp execution
        if self.model_name.startswith("llama-cpp") or self.model_name.endswith(".gguf") or os.path.exists(self.model_name):
            gguf_engine = LlamaCppEngine(model_path=self.model_name)
            res = gguf_engine.generate_completion(messages, tools)
            if not res.get("error"):
                return res

        # 2. Ollama & Hybrid Provider Routing
        provider_model = self.model_name
        if not ("/" in provider_model or provider_model.startswith("ollama")):
            provider_model = f"ollama/{provider_model}"

        kwargs = {
            "model": provider_model,
            "messages": messages,
            "timeout": 120
        }

        if provider_model.startswith("ollama/"):
            ollama_base = os.getenv("OLLAMA_API_BASE", "")
            ollama_key = os.getenv("OLLAMA_API_KEY", "")
            
            if ollama_base:
                kwargs["api_base"] = ollama_base
            else:
                kwargs["api_base"] = "http://localhost:11434"
                
            if ollama_key:
                kwargs["api_key"] = ollama_key

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            return litellm.completion(**kwargs)
        except Exception as e:
            err_str = str(e)
            # If tool calling failed on Ollama model, retry without tools
            if tools and ("tool" in err_str.lower() or "schema" in err_str.lower()):
                try:
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    return litellm.completion(**kwargs)
                except Exception:
                    pass

            if "not found" in err_str.lower() or "404" in err_str:
                return {
                    "error": f"Model '{provider_model}' was not found.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Press **Ctrl+M** inside the app to open the Model Selector screen.\n"
                             f"2. Or pull the model locally via `ollama pull {provider_model.replace('ollama/', '')}`\n"
                             f"3. Or set an API key (`export GEMINI_API_KEY=...` or `export OPENAI_API_KEY=...`)"
                }
            raise e
