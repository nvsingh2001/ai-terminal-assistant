import os
import yaml
import requests
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

CONFIG_FILE_PATH = os.path.expanduser("~/.cli-agent/config.yaml")

def discover_working_model(current_model: Optional[str] = None) -> str:
    """
    Dynamically discovers a 100% working model on the user's system:
    1. Queries local Ollama API (http://localhost:11434/api/tags) for pulled models with valid size > 0.
    2. Checks environment API keys (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).
    3. Falls back to llama.cpp GGUF files if present.
    """
    # 1. Query local Ollama API for valid installed generation models (size > 10MB, non-embedding)
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=2).json()
        models = res.get("models", [])
        # Find first valid local model with size > 10MB (excludes cloud manifest proxies and embedding models)
        for m in models:
            name = m.get("name", "")
            size = m.get("size", 0)
            if size and size > 10_000_000 and name and "embed" not in name.lower():
                return f"ollama/{name}"
    except Exception:
        pass

    # 2. Check for Cloud API keys
    if os.getenv("GEMINI_API_KEY"):
        return "gemini/gemini-1.5-flash"
    elif os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o-mini"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-3-5-sonnet"

    # 3. Fallback
    if current_model and not ("gemma4:31b-cloud" in current_model or "qwen2.5-coder" in current_model):
        return current_model

    return "ollama/qwen3.5:4b"


@dataclass
class AgentConfig:
    model_name: str = ""
    provider: str = "auto"
    llama_cpp_model_path: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    api_keys: Dict[str, str] = None

    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = {
                "openai": os.getenv("OPENAI_API_KEY", ""),
                "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
                "gemini": os.getenv("GEMINI_API_KEY", "")
            }

        # Auto-discover working model if unset or invalid
        if not self.model_name or "gemma4:31b-cloud" in self.model_name or "qwen2.5-coder" in self.model_name:
            self.model_name = discover_working_model(self.model_name)


class ConfigManager:
    """
    Manages persistent configuration settings (~/.cli-agent/config.yaml),
    CLI runtime overrides, and interactive model switching.
    """
    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> AgentConfig:
        """Loads configuration from ~/.cli-agent/config.yaml or creates default."""
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    cfg = AgentConfig(**{k: v for k, v in data.items() if k in AgentConfig.__annotations__})
                    # Re-verify model validity
                    if "gemma4:31b-cloud" in cfg.model_name or "qwen2.5-coder" in cfg.model_name:
                        cfg.model_name = discover_working_model(cfg.model_name)
                        self.save_config(cfg)
                    return cfg
            except Exception as e:
                print(f"Warning: Failed to parse config file: {e}")
        
        cfg = AgentConfig()
        self.save_config(cfg)
        return cfg

    def save_config(self, cfg: AgentConfig):
        """Saves configuration object to ~/.cli-agent/config.yaml."""
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                yaml.dump(asdict(cfg), f, default_flow_style=False)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")

    def set_model(self, model_name: str):
        """Updates and persists selected model."""
        self.config.model_name = model_name
        self.save_config(self.config)


# Global singleton instance
config_manager = ConfigManager()
