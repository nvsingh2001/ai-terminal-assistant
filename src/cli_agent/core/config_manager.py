import os
import yaml
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

CONFIG_FILE_PATH = os.path.expanduser("~/.cli-agent/config.yaml")

@dataclass
class AgentConfig:
    model_name: str = "ollama/gemma4:31b-cloud"
    provider: str = "auto"  # auto, ollama, llama-cpp, openai, anthropic, gemini
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
                    return AgentConfig(**{k: v for k, v in data.items() if k in AgentConfig.__annotations__})
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
