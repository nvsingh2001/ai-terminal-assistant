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
        if self.model_name.startswith("llama-cpp") or self.model_name.endswith(".gguf"):
            res = self.llama_cpp_engine.generate_completion(messages, tools)
            if not res.get("error"):
                return res

        # 2. Hybrid fallback to LiteLLM provider (Ollama / OpenAI / Anthropic / Gemini)
        provider_model = self.model_name
        if not ("/" in provider_model or provider_model.startswith("ollama")):
            provider_model = f"ollama/{provider_model}"

        try:
            response = litellm.completion(
                model=provider_model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                timeout=120
            )
            return response
        except Exception as e:
            err_str = str(e)
            if "not found" in err_str.lower() or "404" in err_str:
                return {
                    "error": f"Model '{provider_model}' was not found.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Press **Ctrl+M** inside the app to open the Model Selector screen.\n"
                             f"2. Or pull the model locally via `ollama pull {provider_model.replace('ollama/', '')}`\n"
                             f"3. Or set an API key (`export GEMINI_API_KEY=...` or `export OPENAI_API_KEY=...`)"
                }
            raise e
