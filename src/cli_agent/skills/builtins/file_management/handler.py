import os
from typing import Optional
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
            description="Reads, writes, appends, outlines, or lists files in the workspace with line-range pagination and safety guardrails.",
            requires_approval=False,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "list", "append", "outline"],
                        "description": (
                            "'read': read a file's content. 'write': overwrite a file. "
                            "'append': add to the end of a file. 'list': list a directory's contents. "
                            "'outline': show a Python file's AST skeleton (signatures only)."
                        ),
                    },
                    "path": {"type": "string", "description": "The file or directory to operate on."},
                    "content": {"type": "string", "description": "Text to write/append (for action='write'/'append')."},
                    "start_line": {"type": "integer", "description": "Optional 1-indexed start line for sliced reading."},
                    "end_line": {"type": "integer", "description": "Optional 1-indexed end line for sliced reading."}
                },
                "required": ["action", "path"]
            }
        )

    def execute(
        self,
        action: str = "read",
        path: str = "",
        content: str = "",
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        **kwargs
    ) -> str:
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
        
        if action in ("read", "outline", "skeleton"):
            if not os.path.exists(target_path):
                return f"Error: File '{path}' does not exist."
            if os.path.isdir(target_path):
                return f"Error: '{path}' is a directory, not a file. Use action='list' to view directories."
            
            max_bytes = 1024 * 1024  # 1 MB limit (accommodates large codebases comfortably)
            file_size = os.path.getsize(target_path)
            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    if file_size > max_bytes:
                        content_data = f.read(max_bytes)
                    else:
                        content_data = f.read()

                from cli_agent.core.token_budget import token_budgeter

                # Explicit AST outline requested
                if action in ("outline", "skeleton"):
                    skeleton = token_budgeter.extract_ast_skeleton(content_data, filename=path)
                    return f"[AST Skeleton Outline: {path}]\n{skeleton}"

                # Line-range pagination requested
                if start_line is not None or end_line is not None:
                    lines = content_data.splitlines()
                    total_lines = len(lines)
                    s_idx = max(1, start_line) if start_line is not None else 1
                    e_idx = min(total_lines, end_line) if end_line is not None else total_lines
                    
                    if s_idx > total_lines:
                        return f"Error: start_line {s_idx} exceeds total file lines ({total_lines})."
                    
                    sliced = [f"[L{i+1:>4}] {lines[i]}" for i in range(s_idx - 1, e_idx)]
                    header = f"[Viewing {path} lines {s_idx} to {e_idx} of {total_lines} total lines]\n"
                    return header + "\n".join(sliced)

                # Standard full read with model-aware token budgeting
                from cli_agent.core.config_manager import config_manager
                active_model = config_manager.config.model_name
                return token_budgeter.budget_text(
                    content_data,
                    is_code=path.endswith((".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp")),
                    filename=path,
                    model_name=active_model
                )
            except Exception as e:
                return f"Error reading file: {str(e)}"
                
        elif action == "write":
            try:
                old_content = ""
                if os.path.exists(target_path) and os.path.isfile(target_path):
                    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                        old_content = f.read()

                from cli_agent.core.safety.rollback import rollback_manager
                from cli_agent.ui.diff_preview import diff_renderer
                from cli_agent.core.config_manager import config_manager

                policy = config_manager.config.execution_policy
                if not diff_renderer.request_approval(target_path, old_content, content, policy=policy):
                    return f"Write cancelled: User rejected the file write to '{path}'."

                rollback_manager.record_pre_edit(target_path)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to file '{path}'."
            except Exception as e:
                return f"Error writing file: {str(e)}"
                
        elif action == "append":
            try:
                old_content = ""
                if os.path.exists(target_path) and os.path.isfile(target_path):
                    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                        old_content = f.read()

                new_content = old_content + content

                from cli_agent.core.safety.rollback import rollback_manager
                from cli_agent.ui.diff_preview import diff_renderer
                from cli_agent.core.config_manager import config_manager

                policy = config_manager.config.execution_policy
                if not diff_renderer.request_approval(target_path, old_content, new_content, policy=policy):
                    return f"Append cancelled: User rejected the file append to '{path}'."

                rollback_manager.record_pre_edit(target_path)

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
