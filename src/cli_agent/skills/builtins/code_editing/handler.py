import os
import py_compile
from cli_agent.skills.base import BaseSkill, SkillManifest

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".idea", ".vscode"}

def is_ignored_path(target_path: str) -> bool:
    parts = set(os.path.normpath(target_path).lower().split(os.sep))
    for ignored in IGNORE_DIRS:
        if ignored.lower() in parts:
            return True
    return False

class CodeEditingSkill(BaseSkill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="code_editing",
            description="Searches, edits, and checks syntax of code files.",
            requires_approval=True,
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["search", "edit", "check_syntax"]},
                    "path": {"type": "string"},
                    "target": {"type": "string"},
                    "replacement": {"type": "string"}
                },
                "required": ["action", "path"]
            }
        )

    def execute(
        self,
        action: str = "search",
        path: str = "",
        target: str = "",
        replacement: str = "",
        file_path: str = "",
        old_string: str = "",
        new_string: str = "",
        **kwargs
    ) -> str:
        action = action.lower().strip()
        actual_path = file_path or path
        actual_target = old_string or target
        actual_replacement = new_string if new_string is not None else replacement

        if not actual_path:
            return "Error: File path is required for code editing."

        target_path = os.path.abspath(actual_path)
        
        if is_ignored_path(target_path):
            return "Skipping this dependency file or directory."
        
        if not os.path.exists(target_path):
            return f"Error: Code path '{actual_path}' does not exist."
            
        if action == "search":
            try:
                matches = []
                if os.path.isdir(target_path):
                    for root, dirs, files in os.walk(target_path):
                        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                        for file in files:
                            f_path = os.path.join(root, file)
                            try:
                                with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                                    for idx, line in enumerate(f):
                                        if actual_target in line:
                                            rel_path = os.path.relpath(f_path, target_path)
                                            matches.append(f"{rel_path}:L{idx+1}: {line.strip()}")
                                            if len(matches) >= 50:
                                                break
                            except Exception:
                                continue
                            if len(matches) >= 50:
                                break
                else:
                    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f):
                            if actual_target in line:
                                matches.append(f"Line {idx+1}: {line.strip()}")
                if not matches:
                    return f"No matches found for '{actual_target}' in '{actual_path}'."
                return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
            except Exception as e:
                return f"Error searching code: {str(e)}"
                
        elif action == "edit":
            if not actual_target:
                return "Error: You must specify a target string/code block to replace."
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if actual_target not in content:
                    return f"Error: Target code block to replace was not found exactly in '{actual_path}'."
                    
                new_content = content.replace(actual_target, actual_replacement, 1)

                from cli_agent.core.safety.rollback import rollback_manager
                from cli_agent.ui.diff_preview import diff_renderer
                from cli_agent.core.config_manager import config_manager

                # Request developer approval with unified diff preview
                policy = config_manager.config.execution_policy
                if not diff_renderer.request_approval(target_path, content, new_content, policy=policy):
                    return f"Edit cancelled: User rejected the proposed diff in '{actual_path}'."

                # Create shadow backup snapshot before writing
                rollback_manager.record_pre_edit(target_path)
                
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
                return f"Successfully updated code in '{actual_path}'."
            except Exception as e:
                return f"Error editing code: {str(e)}"
                
        elif action == "check_syntax":
            if not actual_path.endswith(".py"):
                return f"Syntax check is only supported for Python (.py) files. '{actual_path}' is not a Python file."
            try:
                py_compile.compile(target_path, doraise=True)
                return f"Syntax check passed: '{actual_path}' is syntactically valid Python."
            except py_compile.PyCompileError as e:
                return f"Syntax Error in '{actual_path}':\n{str(e)}"
            except Exception as e:
                return f"Error checking syntax: {str(e)}"
                
        else:
            return f"Error: Unknown action '{action}'."
