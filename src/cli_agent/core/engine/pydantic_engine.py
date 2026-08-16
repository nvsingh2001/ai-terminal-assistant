import os
import json
from typing import Dict, Any, List, Optional, Callable
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.messages import ModelResponse, ThinkingPart

from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.core.llm.resolver import ModelResolver
from cli_agent.skills.registry import SkillRegistry
from cli_agent.services.memory_manager import ConversationMemory
from cli_agent.memory.manager import TriTierMemoryManager, tri_tier_memory
from cli_agent.services.env_detector import get_env_context_string

class PydanticAgentEngine(IAgentEngine):
    """
    Type-Safe Agent Engine powered by PydanticAI (Strategy Pattern implementation).
    Provides native function tool validation, multi-turn reasoning loops,
    real-time execution trace callbacks, and integrated Tri-Tier Long-Term Memory.
    """
    def __init__(
        self,
        model_name: str,
        skill_registry: SkillRegistry,
        memory_store: ConversationMemory,
        model_resolver: Optional[ModelResolver] = None,
        long_term_memory: Optional[TriTierMemoryManager] = None,
        verbose: bool = False
    ):
        self.model_name = model_name
        self.skill_registry = skill_registry
        self.memory_store = memory_store
        self.model_resolver = model_resolver or ModelResolver()
        self.long_term_memory = long_term_memory or tri_tier_memory
        self.verbose = verbose
        self.trace_callback: Optional[Callable[[str, Any], None]] = None
        self._tools_invoked_in_turn: List[str] = []
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

    def _rebuild_agent(self, user_query: Optional[str] = None):
        """Builds the configured PydanticAI Agent with typed tool bindings and memory context."""
        pydantic_model = self.model_resolver.resolve_model(self.model_name)
        
        env_ctx = get_env_context_string()
        session_ctx = self.memory_store.get_formatted_context()
        long_term_ctx = self.long_term_memory.get_formatted_prompt_memory(user_query) if self.long_term_memory else ""

        prompt_parts = [
            "You are an expert AI Command Line Assistant operating directly in the user's terminal.",
            f"Environment Context: {env_ctx}"
        ]

        if long_term_ctx:
            prompt_parts.append(f"Long-Term Memory & Project Knowledge:\n{long_term_ctx}")

        if session_ctx and session_ctx != "No prior conversation history.":
            prompt_parts.append(f"Current Session Conversation:\n{session_ctx}")

        prompt_parts.append(
            "Guidelines for tool usage:\n"
            "1. Use `shell_execution` to run terminal commands in bash.\n"
            "2. When invoking python in a virtualenv, execute `./venv/bin/python <script>` or `python3 <script>`.\n"
            "3. Use `file_management`, `code_editing`, and `git_operations` as appropriate.\n"
            "4. Format final answers cleanly in Markdown."
        )

        system_prompt = "\n\n".join(prompt_parts)

        self._agent = Agent(
            pydantic_model,
            system_prompt=system_prompt,
            model_settings=ModelSettings(max_tokens=4096)
        )

        # Register Tool 1: Shell Execution
        @self._agent.tool_plain
        def shell_execution(command: str) -> str:
            """Executes a bash shell command on the host terminal."""
            self._tools_invoked_in_turn.append("shell_execution")
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
            self._tools_invoked_in_turn.append("file_management")
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
            self._tools_invoked_in_turn.append("code_editing")
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
            self._tools_invoked_in_turn.append("git_operations")
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

    def run_task(self, user_request: str) -> Dict[str, Any]:
        """
        Executes user request through PydanticAI Agent with real-time chronological
        thought streaming, multi-turn tool calling, and memory persistence.
        """
        import asyncio
        self._tools_invoked_in_turn = []
        skills_count = len(self.skill_registry.list_skills())
        routing_summary = f"**[PydanticAI Engine]** Type-safe execution with {skills_count} skills & Tri-Tier Memory."

        async def _execute():
            thought_blocks = []
            async with self._agent.iter(user_request) as runner:
                async for node in runner:
                    if hasattr(node, "model_response") and node.model_response:
                        for part in node.model_response.parts:
                            if isinstance(part, ThinkingPart) and part.content:
                                thought_text = part.content.strip()
                                thought_blocks.append(thought_text)
                                self._emit_trace("thinking", thought_text)

            result = runner.result
            output_str = str(result.output or "").strip()
            return output_str, thought_blocks

        try:
            self._rebuild_agent(user_query=user_request)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                output_text, thought_blocks = loop.run_until_complete(_execute())
            else:
                output_text, thought_blocks = asyncio.run(_execute())

            if not output_text:
                output_text = "Task completed successfully."

            # Update Short-Term Session Memory
            self.memory_store.add_turn(user_request, "PydanticAI", output_text)

            # Persist to Tier 3 Episodic Long-Term Memory
            if self.long_term_memory and len(user_request) > 3:
                tools_used = list(dict.fromkeys(self._tools_invoked_in_turn))
                self.long_term_memory.record_episode(
                    user_prompt=user_request,
                    solution_summary=output_text[:300],
                    tools_used=tools_used
                )

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

