import os
import sys
import importlib.util
from typing import Dict, List, Optional
from cli_agent.skills.base import BaseSkill, SkillManifest

USER_SKILLS_DIR = os.path.expanduser("~/.cli-agent/skills")

class SkillRegistry:
    """
    Dynamic discovery and execution engine for built-in and user-custom skills.
    """
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self.discover_skills()

    def register(self, skill: BaseSkill):
        """Registers a skill instance in the registry."""
        manifest = skill.manifest
        self._skills[manifest.name] = skill

    def discover_skills(self):
        """Discovers built-in skills and user skills from ~/.cli-agent/skills/."""
        # 1. Load Built-in Skills (Direct Import Guarantee)
        try:
            from cli_agent.skills.builtins.shell_execution.handler import ShellExecutionSkill
            from cli_agent.skills.builtins.file_management.handler import FileManagementSkill
            from cli_agent.skills.builtins.code_editing.handler import CodeEditingSkill
            from cli_agent.skills.builtins.git_operations.handler import GitOperationsSkill

            self.register(ShellExecutionSkill())
            self.register(FileManagementSkill())
            self.register(CodeEditingSkill())
            self.register(GitOperationsSkill())
        except Exception as e:
            builtins_dir = os.path.join(os.path.dirname(__file__), "builtins")
            if os.path.exists(builtins_dir):
                self._load_skills_from_dir(builtins_dir)

        # 2. Load User Custom Skills
        if os.path.exists(USER_SKILLS_DIR):
            self._load_skills_from_dir(USER_SKILLS_DIR)

    def _load_skills_from_dir(self, base_dir: str):
        """Recursively loads skill modules containing handler.py."""
        for item in os.listdir(base_dir):
            skill_folder = os.path.join(base_dir, item)
            handler_path = os.path.join(skill_folder, "handler.py")
            if os.path.isdir(skill_folder) and os.path.exists(handler_path):
                try:
                    module_name = f"skill_{item}"
                    spec = importlib.util.spec_from_file_location(module_name, handler_path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        # Instantiate skill class if present
                        for attr_name in dir(mod):
                            attr = getattr(mod, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                                instance = attr()
                                self.register(instance)
                except Exception as e:
                    print(f"Warning: Failed to load skill from {handler_path}: {e}")

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Returns a registered skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillManifest]:
        """Returns manifests of all registered skills."""
        return [skill.manifest for skill in self._skills.values()]

    def execute(self, skill_name: str, **kwargs) -> str:
        """Executes a registered skill by name."""
        skill = self.get_skill(skill_name)
        if not skill:
            return f"Error: Skill '{skill_name}' is not registered."
        try:
            return skill.execute(**kwargs)
        except Exception as e:
            return f"Error executing skill '{skill_name}': {str(e)}"

# Global singleton SkillRegistry instance
skill_registry = SkillRegistry()
