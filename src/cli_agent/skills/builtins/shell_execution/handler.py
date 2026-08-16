import subprocess
import os
import sys
from cli_agent.skills.base import BaseSkill, SkillManifest

def truncate_output(output_text: str, max_chars: int = 15000) -> str:
    """Safely truncates command output to avoid blowing LLM context windows."""
    if not output_text:
        return ""
    if len(output_text) > max_chars:
        return output_text[:max_chars] + f"\n\n[... Output truncated to {max_chars} chars ...]"
    return output_text

class ShellExecutionSkill(BaseSkill):
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="shell_execution",
            description="Executes system terminal commands with bash shell support, real-time stderr capture, and safety guardrails.",
            requires_approval=True,
            parameters_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run."}
                },
                "required": ["command"]
            }
        )

    def execute(self, command: str = "", **kwargs) -> str:
        if not command:
            return "Error: Command argument is required."
        try:
            BLOCKED_PATTERNS = [
                "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){ :|:& };:", "chmod -r 777 /", "shutdown", "reboot",
                "rmdir /s /q c:", "rmdir /s /q c:\\", "rd /s /q c:", "rd /s /q c:\\",
                "del /f /s /q c:", "del /f /s /q c:\\",
                "format c:", "format d:", "diskpart",
                "stop-computer", "restart-computer", "remove-item -recurse -force c:"
            ]
            cmd_lower = command.lower().replace("\\", "/").strip()
            for pattern in BLOCKED_PATTERNS:
                pattern_norm = pattern.lower().replace("\\", "/")
                if pattern_norm in cmd_lower:
                    return f"Error: Shell execution blocked by cross-platform guardrail. Command contains dangerous pattern '{pattern}'."

            # Use bash on Linux/macOS to ensure support for 'source', process substitution, and scripts
            executable = "/bin/bash" if sys.platform != "win32" and os.path.exists("/bin/bash") else None

            result = subprocess.run(
                command,
                shell=True,
                executable=executable,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.getcwd()
            )
            
            output_parts = []
            if result.returncode != 0:
                output_parts.append(f"[Process returned exit code {result.returncode}]")

            if result.stdout and result.stdout.strip():
                output_parts.append(f"STDOUT:\n{truncate_output(result.stdout.strip())}")

            if result.stderr and result.stderr.strip():
                output_parts.append(f"STDERR:\n{truncate_output(result.stderr.strip())}")
                
            if not output_parts:
                return f"Command executed successfully (exit code {result.returncode}, no output)."
                
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 120 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"
