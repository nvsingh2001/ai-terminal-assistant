import os
from cli_agent.skills.base import BaseSkill, SkillManifest

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".idea", ".vscode"}

def is_ignored_path(target_path: str) -> bool:
    parts = set(os.path.normpath(target_path).lower().split(os.sep))
    for ignored in IGNORE_DIRS:
        if ignored.lower() in parts:
            return True
    return False

class FileManagementSkill(BaseSkill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="file_management",
            description="Reads, writes, appends, or lists files in the workspace with credential protection.",
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write", "list", "append"]},
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["action", "path"]
            }
        )

    def execute(self, action: str = "read", path: str = "", content: str = "", **kwargs) -> str:
        action = action.lower().strip()
        target_path = os.path.abspath(path)
        
        if is_ignored_path(target_path):
            return "Skipping this dependency file or directory."

        SENSITIVE_PATHS = [
            "/etc/shadow", "/etc/sudoers", "/etc/passwd",
            "system32/config/sam", "system32/config/system",
            ".ssh/id_rsa", ".ssh/id_ed25519", ".ssh/id_dsa", ".ssh/id_ecdsa",
            ".aws/credentials", ".azure/azureprofile.json", ".config/gcloud/"
        ]
        target_norm = target_path.lower().replace("\\", "/")
        for sens in SENSITIVE_PATHS:
            if sens.lower().replace("\\", "/") in target_norm:
                return f"Error: File access blocked by cross-platform guardrail. Access to sensitive path '{sens}' is prohibited."
        
        if action == "read":
            if not os.path.exists(target_path):
                return f"Error: File '{path}' does not exist."
            if os.path.isdir(target_path):
                return f"Error: '{path}' is a directory, not a file. Use action='list' to view directories."
            
            max_bytes = 200 * 1024  # 200 KB limit
            file_size = os.path.getsize(target_path)
            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    if file_size > max_bytes:
                        content_data = f.read(max_bytes)
                    else:
                        content_data = f.read()
                from cli_agent.core.token_budget import token_budgeter
                return token_budgeter.budget_text(content_data, max_tokens=3000, is_code=path.endswith((".py", ".js", ".ts", ".go", ".rs")), filename=path)
            except Exception as e:
                return f"Error reading file: {str(e)}"
                
        elif action == "write":
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to file '{path}'."
            except Exception as e:
                return f"Error writing file: {str(e)}"
                
        elif action == "append":
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully appended content to file '{path}'."
            except Exception as e:
                return f"Error appending to file: {str(e)}"
                
        elif action == "list":
            if not os.path.exists(target_path):
                return f"Error: Directory '{path}' does not exist."
            if not os.path.isdir(target_path):
                return f"Error: '{path}' is a file, not a directory. Use action='read' to view file contents."
            try:
                items = os.listdir(target_path)
                result = []
                for item in items:
                    if item in IGNORE_DIRS:
                        continue
                    item_path = os.path.join(target_path, item)
                    is_dir = os.path.isdir(item_path)
                    item_type = "DIR " if is_dir else "FILE"
                    size = os.path.getsize(item_path) if not is_dir else "-"
                    result.append(f"[{item_type}] {item:<30} (Size: {size})")
                if not result:
                    return f"Directory '{path}' is empty."
                return "\n".join(result)
            except Exception as e:
                return f"Error listing directory: {str(e)}"
                
        else:
            return f"Error: Unknown action '{action}'."
