import os
from typing import Dict, Any, List, Optional
import litellm

class OllamaProvider:
    """Direct Ollama REST API Provider for local Ollama models."""
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "gemma4:31b-cloud")
        if not (self.model_name.startswith("ollama/") or "/" in self.model_name):
            self.model_name = f"ollama/{self.model_name}"

    def generate_completion(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generates tool calls or chat completion via local Ollama API."""
        return litellm.completion(
            model=self.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
            timeout=120
        )
