import os
import yaml
import requests
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

CONFIG_FILE_PATH = os.path.expanduser("~/.cli-agent/config.yaml")

def discover_working_model(current_model: Optional[str] = None) -> str:
    """
    Dynamically discovers a working model on the user's system:
    1. If user already has a configured model, respects it.
    2. Queries local Ollama API for installed generation models.
    3. Checks environment API keys (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).
    4. Falls back to ollama/gemma4:31b-cloud or ollama/qwen3.5:4b.
    """
    if current_model and current_model.strip():
        return current_model.strip()

    # Query local Ollama API for valid installed generation models (non-embedding)
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=2).json()
        models = res.get("models", [])
        for m in models:
            name = m.get("name", "")
            if name and "embed" not in name.lower():
                return f"ollama/{name}"
    except Exception:
        pass

    # Check for Cloud API keys
    if os.getenv("GEMINI_API_KEY"):
        return "gemini/gemini-1.5-flash"
    elif os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o-mini"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-3-5-sonnet"

    return "ollama/gemma4:31b-cloud"


@dataclass
class AgentConfig:
    model_name: str = ""
    provider: str = "auto"
    llama_cpp_model_path: str = ""
    verbose: bool = False
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

        # Auto-discover working model if unset
        if not self.model_name:
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
                    if not cfg.model_name:
                        cfg.model_name = discover_working_model()
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

    def set_verbose(self, verbose: bool):
        """Updates and persists verbose/trace mode."""
        self.config.verbose = verbose
        self.save_config(self.config)


# Global singleton instance
config_manager = ConfigManager()
