import os
import json
import requests
from typing import Dict, Any, List, Optional
import litellm
from cli_agent.core.llm.llama_cpp import LlamaCppEngine


class _OllamaResponse:
    """Mimics LiteLLM response structure for direct Ollama HTTP calls."""
    def __init__(self, content: str):
        self.content = content
        self.tool_calls = None

class _OllamaChoice:
    def __init__(self, message):
        self.message = message

class _OllamaResult:
    def __init__(self, content: str):
        self.choices = [_OllamaChoice(_OllamaResponse(content))]


class HybridLLMEngine:
    """
    Unified Hybrid LLM Engine Router.
    Seamlessly routes requests between:
    - Native Local llama.cpp (GGUF in-memory execution)
    - Local Ollama Engine (direct HTTP — bypasses LiteLLM's broken Ollama integration)
    - Cloud APIs (OpenAI, Anthropic Claude, Google Gemini) via LiteLLM
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "ollama/qwen3.5:4b")
        self.llama_cpp_engine = LlamaCppEngine()

    def _call_ollama_direct(self, messages: List[Dict[str, Any]], model_tag: str) -> Dict[str, Any]:
        """
        Calls local Ollama HTTP API directly, bypassing LiteLLM entirely.
        Prioritizes localhost:11434 if reachable, then falls back to OLLAMA_API_BASE.
        """
        ollama_key = os.getenv("OLLAMA_API_KEY", "")

        # Determine Ollama base URL: prefer local server, fall back to env var
        local_base = "http://localhost:11434"
        remote_base = os.getenv("OLLAMA_API_BASE", "")

        # Check if local Ollama is running
        try:
            requests.get(f"{local_base}/api/tags", timeout=2)
            ollama_base = local_base
        except Exception:
            ollama_base = remote_base if remote_base else local_base

        headers = {"Content-Type": "application/json"}
        if ollama_key:
            headers["Authorization"] = f"Bearer {ollama_key}"

        # Build the prompt from messages
        payload = {
            "model": model_tag,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        try:
            resp = requests.post(
                f"{ollama_base}/api/chat",
                headers=headers,
                json=payload,
                timeout=120
            )

            if resp.status_code == 404:
                return {
                    "error": f"Model '{model_tag}' was not found on Ollama server at {ollama_base}.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Pull the model: `ollama pull {model_tag}`\n"
                             f"2. Or use `/model` to switch to a different model\n"
                             f"3. Or set a cloud API key (`export GEMINI_API_KEY=...`)"
                }

            resp.raise_for_status()
            data = resp.json()

            content = data.get("message", {}).get("content", "")
            if not content:
                content = data.get("response", "")

            return _OllamaResult(content)

        except requests.exceptions.ConnectionError:
            return {
                "error": f"Cannot connect to Ollama at {ollama_base}.\n\n"
                         f"👉 **Action Required**:\n"
                         f"1. Start Ollama: `ollama serve`\n"
                         f"2. Or set `OLLAMA_API_BASE` to point to a remote Ollama server"
            }
        except requests.exceptions.Timeout:
            return {
                "error": f"Ollama request timed out after 120s for model '{model_tag}'.\n\n"
                         f"The model may be too large for your system. Try a smaller model."
            }
        except Exception as e:
            return {"error": f"Ollama error: {str(e)}"}

    def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Routes completion to local GGUF, local Ollama (direct HTTP), or Cloud provider."""
        # 1. Check if model specifies local GGUF llama.cpp execution
        if self.model_name.startswith("llama-cpp") or self.model_name.endswith(".gguf") or (
            not self.model_name.startswith(("ollama/", "gemini/", "openai/", "anthropic/"))
            and os.path.exists(self.model_name)
        ):
            gguf_engine = LlamaCppEngine(model_path=self.model_name)
            res = gguf_engine.generate_completion(messages, tools)
            if not res.get("error"):
                return res

        # 2. Ollama models → Direct HTTP (bypasses LiteLLM)
        if self.model_name.startswith("ollama/"):
            model_tag = self.model_name.replace("ollama/", "", 1)
            return self._call_ollama_direct(messages, model_tag)

        # Also handle bare model names without provider prefix as Ollama
        if "/" not in self.model_name and not self.model_name.endswith(".gguf"):
            return self._call_ollama_direct(messages, self.model_name)

        # 3. Cloud Providers via LiteLLM (OpenAI, Anthropic, Gemini)
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "timeout": 120
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            return litellm.completion(**kwargs)
        except Exception as e:
            err_str = str(e)
            # If tool calling failed, retry without tools
            if tools and ("tool" in err_str.lower() or "schema" in err_str.lower()):
                try:
                    kwargs.pop("tools", None)
                    kwargs.pop("tool_choice", None)
                    return litellm.completion(**kwargs)
                except Exception:
                    pass

            if "not found" in err_str.lower() or "404" in err_str:
                return {
                    "error": f"Model '{self.model_name}' was not found.\n\n"
                             f"👉 **Action Required**:\n"
                             f"1. Use `/model` to switch to a different model\n"
                             f"2. Or set the correct API key for your provider"
                }
            raise e
