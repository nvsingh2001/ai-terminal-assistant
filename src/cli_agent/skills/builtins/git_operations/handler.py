import subprocess
import os
from cli_agent.skills.base import BaseSkill, SkillManifest

class GitOperationsSkill(BaseSkill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="git_operations",
            description="Executes Git operations (status, diff, add, commit, log, branch, checkout, stash).",
            requires_approval=True,
            parameters_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["status", "diff", "add", "commit", "log", "branch", "checkout", "stash"],
                    },
                    "args": {
                        "type": "string",
                        "description": (
                            "Raw arguments appended after `git <operation>`, e.g. '-m \"message\"' for "
                            "commit or a branch name for branch/checkout."
                        ),
                    },
                },
                "required": ["operation"],
            }
        )

    def execute(
        self,
        operation: str = "status",
        args: str = "",
        action: str = "",
        branch_name: str = "",
        commit_message: str = "",
        **kwargs
    ) -> str:
        op = (action or operation or "status").lower().strip()
        allowed_ops = ["status", "diff", "add", "commit", "log", "branch", "checkout", "stash"]
        if op not in allowed_ops:
            return f"Error: Operation '{op}' is not allowed."

        cmd_args = args.strip()
        if op == "commit" and commit_message and "-m" not in cmd_args:
            cmd_args = f'-m "{commit_message}" {cmd_args}'.strip()
        elif op == "branch" and branch_name and branch_name not in cmd_args:
            cmd_args = f"{branch_name} {cmd_args}".strip()

        command = f"git {op} {cmd_args}".strip()
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
                output.append(result.stdout.strip())
            if result.stderr:
                output.append(result.stderr.strip())
            if not output:
                return f"Git operation '{op}' executed successfully with code {result.returncode}."
            return "\n".join(output)
        except subprocess.TimeoutExpired:
            return "Error: Git command timed out."
        except Exception as e:
            return f"Error executing git command: {str(e)}"
