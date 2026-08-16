import subprocess
import os
from cli_agent.skills.base import BaseSkill, SkillManifest

class GitOperationsSkill(BaseSkill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="git_operations",
            description="Executes Git operations (status, diff, add, commit, log, branch).",
            requires_approval=True,
            parameters_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["status", "diff", "add", "commit", "log", "branch"]},
                    "args": {"type": "string"}
                },
                "required": ["operation"]
            }
        )

    def execute(self, operation: str = "status", args: str = "", **kwargs) -> str:
        operation = operation.lower().strip()
        allowed_ops = ["status", "diff", "add", "commit", "log", "branch"]
        if operation not in allowed_ops:
            return f"Error: Operation '{operation}' is not allowed."

        command = f"git {operation} {args}".strip()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(result.stderr)
            if not output:
                return f"Git operation executed successfully with code {result.returncode}."
            return "\n".join(output)
        except subprocess.TimeoutExpired:
            return "Error: Git command timed out."
        except Exception as e:
            return f"Error executing git command: {str(e)}"
