import os
import json
import requests
from typing import Dict, Any, List, Optional
import litellm
from cli_agent.core.llm.llama_cpp import LlamaCppEngine


class _OllamaToolCall:
    """Mimics LiteLLM tool_call structure."""
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = type("Function", (), {"name": name, "arguments": arguments})()


class _OllamaResponse:
    """Mimics LiteLLM response message structure for direct Ollama HTTP calls."""
    def __init__(self, content: str, tool_calls: Optional[List] = None):
        self.content = content
        self.tool_calls = tool_calls

    def get(self, key, default=None):
        """Allow dict-style access for compatibility with engine.py message appending."""
        return getattr(self, key, default)


class _OllamaChoice:
    def __init__(self, message):
        self.message = message


class _OllamaResult:
    def __init__(self, content: str, tool_calls: Optional[List] = None):
        self.choices = [_OllamaChoice(_OllamaResponse(content, tool_calls))]


class HybridLLMEngine:
    """
    Unified Hybrid LLM Engine Router.
    Seamlessly routes requests between:
    - Native Local llama.cpp (GGUF in-memory execution)
    - Local Ollama Engine (direct HTTP with tool calling support)
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

    def _call_ollama_direct(self, messages: List[Dict[str, Any]], model_tag: str,
                            tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Calls local Ollama HTTP API directly with full tool calling support.
        Prioritizes localhost:11434 if reachable, then falls back to OLLAMA_API_BASE.
        """
        ollama_base = self._get_ollama_base()
        ollama_key = os.getenv("OLLAMA_API_KEY", "")

        headers = {"Content-Type": "application/json"}
        if ollama_key:
            headers["Authorization"] = f"Bearer {ollama_key}"

        # Serialize messages — convert any _OllamaResponse objects to dicts
        serialized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized_messages.append(msg)
            elif hasattr(msg, "content"):
                m = {"role": getattr(msg, "role", "assistant"), "content": msg.content or ""}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    m["tool_calls"] = [
                        {"function": {"name": tc.function.name, "arguments": json.loads(tc.function.arguments)}}
                        for tc in msg.tool_calls
                    ]
                serialized_messages.append(m)

        payload = {
            "model": model_tag,
            "messages": serialized_messages,
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        # Include tools if provided
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(
                f"{ollama_base}/api/chat",
                headers=headers,
                json=payload,
                timeout=180
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

            message_data = data.get("message", {})
            content = message_data.get("content", "")
            if not content:
                content = data.get("response", "")

            # Parse tool calls from Ollama response
            raw_tool_calls = message_data.get("tool_calls", None)
            parsed_tool_calls = None

            if raw_tool_calls:
                parsed_tool_calls = []
                for i, tc in enumerate(raw_tool_calls):
                    func_data = tc.get("function", {})
                    name = func_data.get("name", "")
                    args = func_data.get("arguments", {})
                    parsed_tool_calls.append(
                        _OllamaToolCall(
                            id=f"call_{i}",
                            name=name,
                            arguments=json.dumps(args) if isinstance(args, dict) else str(args)
                        )
                    )

            return _OllamaResult(content, parsed_tool_calls)

        except requests.exceptions.ConnectionError:
            return {
                "error": f"Cannot connect to Ollama at {ollama_base}.\n\n"
                         f"👉 **Action Required**:\n"
                         f"1. Start Ollama: `ollama serve`\n"
                         f"2. Or set `OLLAMA_API_BASE` to point to a remote Ollama server"
            }
        except requests.exceptions.Timeout:
            return {
                "error": f"Ollama request timed out after 180s for model '{model_tag}'.\n\n"
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

        # 2. Ollama models → Direct HTTP with tool calling (bypasses LiteLLM)
        if self.model_name.startswith("ollama/"):
            model_tag = self.model_name.replace("ollama/", "", 1)
            return self._call_ollama_direct(messages, model_tag, tools)

        # Also handle bare model names without provider prefix as Ollama
        if "/" not in self.model_name and not self.model_name.endswith(".gguf"):
            return self._call_ollama_direct(messages, self.model_name, tools)

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
