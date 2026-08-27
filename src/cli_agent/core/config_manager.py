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
    execution_policy: str = "trusted-read"  # Options: strict, trusted-read, yolo
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

    def set_execution_policy(self, policy: str):
        """Updates and persists execution policy mode (strict, trusted-read, yolo)."""
        clean_policy = policy.strip().lower()
        if clean_policy in ("strict", "trusted-read", "yolo"):
            self.config.execution_policy = clean_policy
            self.save_config(self.config)

    def set_api_key(self, key_name: str, key_value: str):
        """
        Updates and persists an API key globally in ~/.cli-agent/.env and ~/.cli-agent/config.yaml.
        Ensures keys remain accessible across all project repositories without project .env collisions.
        """
        key_name = key_name.strip().upper()
        key_value = key_value.strip()
        os.environ[key_name] = key_value

        # 1. Update config.yaml api_keys dict
        provider_map = {
            "OPENAI_API_KEY": "openai",
            "ANTHROPIC_API_KEY": "anthropic",
            "GEMINI_API_KEY": "gemini",
            "GOOGLE_API_KEY": "gemini",
            "OLLAMA_API_KEY": "ollama",
            "OLLAMA_API_BASE": "ollama_base"
        }
        provider = provider_map.get(key_name, key_name.lower())
        if self.config.api_keys is None:
            self.config.api_keys = {}
        self.config.api_keys[provider] = key_value
        self.save_config(self.config)

        # 2. Persist to global ~/.cli-agent/.env
        config_dir = os.path.expanduser("~/.cli-agent")
        global_env_path = os.path.join(config_dir, ".env")
        os.makedirs(config_dir, exist_ok=True)
        
        lines = []
        if os.path.exists(global_env_path):
            try:
                with open(global_env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                lines = []

        found = False
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{key_name}=") or stripped.startswith(f"export {key_name}="):
                new_lines.append(f"{key_name}={key_value}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{key_name}={key_value}\n")

        try:
            with open(global_env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Warning: Could not persist key to {global_env_path}: {e}")


# Global singleton instance
config_manager = ConfigManager()
