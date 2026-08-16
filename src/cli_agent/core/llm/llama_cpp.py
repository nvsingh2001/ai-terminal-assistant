import os
from typing import Dict, Any, List, Optional

class LlamaCppEngine:
    """
    Native llama.cpp GGUF local model engine.
    Supports in-memory C++ GGUF inference via llama-cpp-python or HTTP server fallback.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("LLAMA_CPP_MODEL_PATH", "")
        self.llm_instance = None
        self._init_llama_cpp()

    def _init_llama_cpp(self):
        if self.model_path and os.path.exists(self.model_path):
            try:
                from llama_cpp import Llama
                # Initialize in-memory GGUF model with GPU acceleration if available
                self.llm_instance = Llama(
                    model_path=self.model_path,
                    n_ctx=8192,
                    n_gpu_layers=-1, # Auto GPU offloading
                    verbose=False
                )
                print(f"[SYSTEM] Loaded llama.cpp GGUF model: {os.path.basename(self.model_path)}")
            except Exception as e:
                print(f"[WARNING] Could not initialize native llama_cpp: {e}")

    def generate_completion(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generates tool calls or chat completion via local llama.cpp GGUF engine."""
        if self.llm_instance:
            try:
                response = self.llm_instance.create_chat_completion(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None
                )
                return response
            except Exception as e:
                return {"error": str(e)}

        return {"error": "llama.cpp GGUF model not loaded. Specify LLAMA_CPP_MODEL_PATH."}
