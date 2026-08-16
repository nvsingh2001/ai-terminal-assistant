import os
import litellm

# Suppress LiteLLM verbose logging and feedback spam
litellm.suppress_debug_info = True
litellm.set_verbose = False
os.environ.setdefault("LITELLM_LOG", "ERROR")

from cli_agent.core.llm.resolver import ModelResolver
from cli_agent.core.llm.llama_cpp import LlamaCppEngine
from cli_agent.core.llm.ollama import OllamaProvider
from cli_agent.core.llm.cloud import CloudLLMProvider
from cli_agent.core.llm.provider_manager import HybridLLMEngine

__all__ = [
    "ModelResolver",
    "LlamaCppEngine",
    "OllamaProvider",
    "CloudLLMProvider",
    "HybridLLMEngine"
]
