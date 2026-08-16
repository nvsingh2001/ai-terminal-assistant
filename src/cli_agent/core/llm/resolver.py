import os
from typing import Dict, Any, Optional
from cli_agent.core.interfaces.model import IModelResolver

class ModelResolver(IModelResolver):
    """
    Translates user model configurations into provider URIs compatible with PydanticAI.
    Sets necessary environment variables for local/remote endpoints.
    """
    def resolve_model_string(self, model_name: str) -> str:
        clean = model_name.strip()
        
        if clean.startswith("gemini/") or clean.startswith("google/"):
            return f"google-gla:{clean.split('/', 1)[1]}"
            
        elif clean.startswith("openai/"):
            return f"openai:{clean.split('/', 1)[1]}"
            
        elif clean.startswith("anthropic/"):
            return f"anthropic:{clean.split('/', 1)[1]}"
            
        elif clean.startswith("ollama/"):
            # Set Ollama base URL to localhost /v1
            ollama_base = os.getenv("OLLAMA_API_BASE", "")
            if not ollama_base:
                os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
            elif "/v1" not in ollama_base:
                os.environ["OLLAMA_BASE_URL"] = f"{ollama_base.rstrip('/')}/v1"
            else:
                os.environ["OLLAMA_BASE_URL"] = ollama_base
                
            return f"ollama:{clean.replace('ollama/', '')}"
            
        else:
            # Default to local Ollama
            os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            return f"ollama:{clean}"
