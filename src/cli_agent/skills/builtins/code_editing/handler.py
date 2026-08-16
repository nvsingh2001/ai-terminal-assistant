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

    def execute(self, action: str = "search", path: str = "", target: str = "", replacement: str = "", **kwargs) -> str:
        action = action.lower().strip()
        target_path = os.path.abspath(path)
        
        if is_ignored_path(target_path):
            return "Skipping this dependency file or directory."
        
        if not os.path.exists(target_path):
            return f"Error: Code path '{path}' does not exist."
            
        if action == "search":
            try:
                matches = []
                if os.path.isdir(target_path):
                    for root, dirs, files in os.walk(target_path):
                        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                    for idx, line in enumerate(f):
                                        if target in line:
                                            rel_path = os.path.relpath(file_path, target_path)
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
                            if target in line:
                                matches.append(f"Line {idx+1}: {line.strip()}")
                if not matches:
                    return f"No matches found for '{target}' in '{path}'."
                return f"Found {len(matches)} match(es):\n" + "\n".join(matches)
            except Exception as e:
                return f"Error searching code: {str(e)}"
                
        elif action == "edit":
            if not target:
                return "Error: You must specify a target string/code block to replace."
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if target not in content:
                    return f"Error: Target code block to replace was not found exactly in '{path}'."
                    
                new_content = content.replace(target, replacement, 1)
                
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
                return f"Successfully updated code in '{path}'."
            except Exception as e:
                return f"Error editing code: {str(e)}"
                
        elif action == "check_syntax":
            if not path.endswith(".py"):
                return f"Syntax check is only supported for Python (.py) files. '{path}' is not a Python file."
            try:
                py_compile.compile(target_path, doraise=True)
                return f"Syntax check passed: '{path}' is syntactically valid Python."
            except py_compile.PyCompileError as e:
                return f"Syntax Error in '{path}':\n{str(e)}"
            except Exception as e:
                return f"Error checking syntax: {str(e)}"
                
        else:
            return f"Error: Unknown action '{action}'."
