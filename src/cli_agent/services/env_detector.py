import os
import platform
import subprocess
from typing import Dict

def get_system_info() -> Dict[str, str]:
    """Detects system environment details for context injection and UI banners."""
    os_name = platform.system()
    os_release = platform.release()
    arch = platform.machine()
    cwd = os.getcwd()
    
    # Detect shell
    shell = os.getenv("SHELL") or os.getenv("COMSPEC") or "default shell"
    
    # Detect git branch if in a git repository
    git_branch = "None"
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=cwd
        )
        if res.returncode == 0 and res.stdout.strip():
            git_branch = res.stdout.strip()
    except Exception:
        pass

    return {
        "os": f"{os_name} {os_release} ({arch})",
        "shell": shell,
        "cwd": cwd,
        "git_branch": git_branch
    }

def get_env_context_string() -> str:
    """Formats system info into a clean string for agent prompts."""
    info = get_system_info()
    return f"OS: {info['os']} | Shell: {info['shell']} | CWD: {info['cwd']} | Git Branch: {info['git_branch']}"
