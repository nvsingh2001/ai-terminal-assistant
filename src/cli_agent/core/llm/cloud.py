import os
from typing import Dict, Any, List, Optional
import litellm

class CloudLLMProvider:
    """Cloud API Provider for OpenAI (gpt-4o), Anthropic (claude-3-5-sonnet), and Gemini (gemini-1.5-pro)."""
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("CLOUD_MODEL_NAME", "openai/gpt-4o")

    def generate_completion(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generates completion via Cloud API providers."""
        return litellm.completion(
            model=self.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
            timeout=120
        )
