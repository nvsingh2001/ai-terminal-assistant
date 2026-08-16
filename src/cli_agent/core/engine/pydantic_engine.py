import os
import json
from typing import Dict, Any, List, Optional, Callable
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.messages import ModelResponse, ThinkingPart

from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.core.llm.resolver import ModelResolver
from cli_agent.skills.registry import SkillRegistry
from cli_agent.services.memory_manager import ConversationMemory
from cli_agent.services.env_detector import get_env_context_string

class PydanticAgentEngine(IAgentEngine):
    """
    Type-Safe Agent Engine powered by PydanticAI (Strategy Pattern implementation).
    Provides native function tool validation, multi-turn reasoning loops,
    real-time execution trace callbacks, and unified execution across LLM providers.
    """
    def __init__(
        self,
        model_name: str,
        skill_registry: SkillRegistry,
        memory_store: ConversationMemory,
        model_resolver: Optional[ModelResolver] = None,
        verbose: bool = False
    ):
        self.model_name = model_name
        self.skill_registry = skill_registry
        self.memory_store = memory_store
        self.model_resolver = model_resolver or ModelResolver()
        self.verbose = verbose
        self.trace_callback: Optional[Callable[[str, Any], None]] = None
        self._rebuild_agent()

    def set_model(self, model_name: str):
        """Updates the active model and rebuilds the underlying PydanticAI Agent."""
        self.model_name = model_name
        self._rebuild_agent()

    def set_verbose(self, verbose: bool):
        """Updates verbose trace mode."""
        self.verbose = verbose

    def set_trace_callback(self, callback: Optional[Callable[[str, Any], None]]):
        """Sets a listener callback for real-time thoughts and tool execution trace events."""
        self.trace_callback = callback

    def _emit_trace(self, event_type: str, data: Any):
        """Emits trace event if verbose is active and callback is set."""
        if self.verbose and self.trace_callback:
            try:
                self.trace_callback(event_type, data)
            except Exception:
                pass

    def _rebuild_agent(self):
        """Builds the configured PydanticAI Agent with typed tool bindings and model settings."""
        pydantic_model = self.model_resolver.resolve_model(self.model_name)
        
        env_ctx = get_env_context_string()
        history_ctx = self.memory_store.get_formatted_context()

        system_prompt = (
            "You are an expert AI Command Line Assistant operating directly in the user's terminal.\n"
            f"Environment Context: {env_ctx}\n"
            f"Prior Conversation Memory:\n{history_ctx}\n\n"
            "Guidelines for tool usage:\n"
            "1. Use `shell_execution` to run terminal commands. On Linux/macOS, commands run in bash.\n"
            "2. When invoking virtual environments or python, execute `./venv/bin/python <script>` or `python3 <script>` (do not attempt to execute non-executable activate scripts directly).\n"
            "3. Use `file_management`, `code_editing`, and `git_operations` as appropriate.\n"
            "4. Format your final answers cleanly in Markdown without echoing raw tool calls."
        )

        self._agent = Agent(
            pydantic_model,
            system_prompt=system_prompt,
            model_settings=ModelSettings(max_tokens=4096)
        )

        # Register Tool 1: Shell Execution
        @self._agent.tool_plain
        def shell_execution(command: str) -> str:
            """Executes a bash shell command on the host terminal."""
            self._emit_trace("tool_call", {"tool": "shell_execution", "args": {"command": command}})
            res = self.skill_registry.execute("shell_execution", command=command)
            self._emit_trace("tool_result", {"tool": "shell_execution", "output": res})
            return res

        # Register Tool 2: File Management
        @self._agent.tool_plain
        def file_management(
            action: str,
            path: str,
            content: Optional[str] = None,
            recursive: bool = False,
            query: Optional[str] = None
        ) -> str:
            """Manages files and directories (actions: read, write, list, search, delete, info)."""
            args = {"action": action, "path": path, "content": content, "recursive": recursive, "query": query}
            clean_args = {k: v for k, v in args.items() if v is not None}
            self._emit_trace("tool_call", {"tool": "file_management", "args": clean_args})
            res = self.skill_registry.execute(
                "file_management",
                action=action,
                path=path,
                content=content,
                recursive=recursive,
                query=query
            )
            self._emit_trace("tool_result", {"tool": "file_management", "output": res})
            return res

        # Register Tool 3: Code Editing
        @self._agent.tool_plain
        def code_editing(
            file_path: str,
            action: str,
            old_string: Optional[str] = None,
            new_string: Optional[str] = None,
            line_number: Optional[int] = None
        ) -> str:
            """Edits code files with exact string replacement or line insertions."""
            args = {"file_path": file_path, "action": action, "old_string": old_string, "new_string": new_string, "line_number": line_number}
            clean_args = {k: v for k, v in args.items() if v is not None}
            self._emit_trace("tool_call", {"tool": "code_editing", "args": clean_args})
            res = self.skill_registry.execute(
                "code_editing",
                file_path=file_path,
                action=action,
                old_string=old_string,
                new_string=new_string,
                line_number=line_number
            )
            self._emit_trace("tool_result", {"tool": "code_editing", "output": res})
            return res

        # Register Tool 4: Git Operations
        @self._agent.tool_plain
        def git_operations(
            action: str,
            branch_name: Optional[str] = None,
            commit_message: Optional[str] = None
        ) -> str:
            """Performs git operations (actions: status, diff, commit, log, branch)."""
            args = {"action": action, "branch_name": branch_name, "commit_message": commit_message}
            clean_args = {k: v for k, v in args.items() if v is not None}
            self._emit_trace("tool_call", {"tool": "git_operations", "args": clean_args})
            res = self.skill_registry.execute(
                "git_operations",
                action=action,
                branch_name=branch_name,
                commit_message=commit_message
            )
            self._emit_trace("tool_result", {"tool": "git_operations", "output": res})
            return res

    def run_task(self, user_request: str) -> Dict[str, str]:
        """
        Executes user request through PydanticAI Agent with multi-turn tool calling and trace extraction.
        """
        skills_count = len(self.skill_registry.list_skills())
        routing_summary = f"**[PydanticAI Engine]** Type-safe multi-turn execution with {skills_count} registered skills."

        try:
            self._rebuild_agent()
            result = self._agent.run_sync(user_request)
            
            # Extract any thinking parts from all messages
            thought_blocks = []
            for msg in result.all_messages():
                if isinstance(msg, ModelResponse):
                    for part in msg.parts:
                        if isinstance(part, ThinkingPart) and part.content:
                            thought_blocks.append(part.content.strip())
                            self._emit_trace("thinking", part.content.strip())

            output_text = str(result.output or "").strip()

            if not output_text:
                output_text = "Task completed successfully."

            self.memory_store.add_turn(user_request, "PydanticAI", output_text)
            return {
                "routing": routing_summary,
                "execution": output_text,
                "thoughts": thought_blocks
            }

        except Exception as e:
            err_str = str(e)
            if "404" in err_str or "not found" in err_str:
                return {
                    "routing": "Model Provider Notice",
                    "execution": f"Model '{self.model_name}' was not found on Ollama.\n\n"
                                 f"👉 **Action Required**:\n"
                                 f"1. Pull the model: `ollama pull {self.model_name.replace('ollama/', '')}`\n"
                                 f"2. Or switch models via `/model` command (e.g. `ollama/gemma4:31b-cloud`)."
                }
            return {
                "routing": "Execution Notice",
                "execution": f"Error executing task: {err_str}"
            }
