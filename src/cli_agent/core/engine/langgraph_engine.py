import asyncio
import os
from typing import Annotated, Any, Callable, Dict, List, Optional, Sequence, TypedDict

import nest_asyncio
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.core.llm.langchain_resolver import LangChainModelResolver
from cli_agent.memory.manager import TriTierMemoryManager
from cli_agent.services.env_detector import get_env_context_string
from cli_agent.services.memory_manager import ConversationMemory
from cli_agent.skills.registry import SkillRegistry


class AgentState(TypedDict):
    """LangGraph state schema maintaining the message history sequence."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class LangGraphAgentEngine(IAgentEngine):
    """
    Next-Generation Agent Execution Engine built on LangGraph StateGraph.
    Provides cyclic orchestration, type-safe tool execution, Tri-Tier Long-Term Memory
    integration, and real-time execution trace streaming.
    """

    def __init__(
        self,
        model_name: str,
        skill_registry: SkillRegistry,
        memory_store: ConversationMemory,
        long_term_memory: Optional[TriTierMemoryManager] = None,
        verbose: bool = False,
    ):
        self.model_name = model_name
        self.skill_registry = skill_registry
        self.memory_store = memory_store
        self.long_term_memory = long_term_memory
        self.verbose = verbose
        self.trace_callback: Optional[Callable[[str, Any], None]] = None

        self.model_resolver = LangChainModelResolver()
        self._tools_invoked_in_turn: List[str] = []
        self._compiled_graph = None
        self._rebuild_graph()

    def set_trace_callback(self, callback: Callable[[str, Any], None]):
        """Registers external trace listener callback for live terminal streaming."""
        self.trace_callback = callback

    def _emit_trace(self, event_type: str, data: Any):
        """Emits real-time trace events if verbose mode is enabled."""
        if self.verbose and self.trace_callback:
            try:
                self.trace_callback(event_type, data)
            except Exception:
                pass

    def set_model(self, model_name: str):
        """Updates active model and recompiles LangGraph StateGraph."""
        self.model_name = model_name
        self._rebuild_graph()

    def set_verbose(self, verbose: bool):
        """Toggles verbose trace mode."""
        self.verbose = verbose

    def _build_tools(self) -> list:
        """Constructs LangChain tools wrapping Aegis's SkillRegistry with real-time trace hooks."""
        engine_self = self

        @tool
        def shell_execution(command: str) -> str:
            """Executes a bash shell command on the host terminal."""
            engine_self._tools_invoked_in_turn.append("shell_execution")
            engine_self._emit_trace("tool_call", {"tool": "shell_execution", "args": {"command": command}})
            res = engine_self.skill_registry.execute("shell_execution", command=command)
            engine_self._emit_trace("tool_result", {"tool": "shell_execution", "output": res})
            return res

        @tool
        def file_management(
            action: str,
            path: str,
            content: Optional[str] = None,
            start_line: Optional[int] = None,
            end_line: Optional[int] = None,
            recursive: bool = False,
            query: Optional[str] = None,
        ) -> str:
            """Manages files and directories (actions: read, write, list, append, outline; supports start_line and end_line pagination)."""
            engine_self._tools_invoked_in_turn.append("file_management")
            args = {
                "action": action,
                "path": path,
                "content": content,
                "start_line": start_line,
                "end_line": end_line,
                "recursive": recursive,
                "query": query,
            }
            clean_args = {k: v for k, v in args.items() if v is not None}
            engine_self._emit_trace("tool_call", {"tool": "file_management", "args": clean_args})
            res = engine_self.skill_registry.execute(
                "file_management",
                action=action,
                path=path,
                content=content,
                start_line=start_line,
                end_line=end_line,
                recursive=recursive,
                query=query,
            )
            engine_self._emit_trace("tool_result", {"tool": "file_management", "output": res})
            return res

        @tool
        def code_editing(
            file_path: str,
            action: str,
            old_string: Optional[str] = None,
            new_string: Optional[str] = None,
            line_number: Optional[int] = None,
        ) -> str:
            """Searches, edits, and checks the syntax of code files.

            action: one of "search", "edit", "check_syntax".
            - "search": find occurrences of `old_string` in `file_path` (a file or directory).
            - "edit": replace the first exact match of `old_string` with `new_string` in `file_path`.
            - "check_syntax": validate that `file_path` (a .py file) is syntactically valid Python.
              Always use this action for syntax-check requests instead of reasoning about the
              code yourself or shelling out to a compiler.
            """
            engine_self._tools_invoked_in_turn.append("code_editing")
            args = {
                "file_path": file_path,
                "action": action,
                "old_string": old_string,
                "new_string": new_string,
                "line_number": line_number,
            }
            clean_args = {k: v for k, v in args.items() if v is not None}
            engine_self._emit_trace("tool_call", {"tool": "code_editing", "args": clean_args})
            res = engine_self.skill_registry.execute(
                "code_editing",
                file_path=file_path,
                action=action,
                old_string=old_string,
                new_string=new_string,
                line_number=line_number,
            )
            engine_self._emit_trace("tool_result", {"tool": "code_editing", "output": res})
            return res

        @tool
        def git_operations(
            action: str,
            message: Optional[str] = None,
            branch: Optional[str] = None,
            target: Optional[str] = None,
        ) -> str:
            """Handles Git version control actions (status, diff, add, commit, checkout, branch, log)."""
            engine_self._tools_invoked_in_turn.append("git_operations")
            args = {"action": action, "message": message, "branch": branch, "target": target}
            clean_args = {k: v for k, v in args.items() if v is not None}
            engine_self._emit_trace("tool_call", {"tool": "git_operations", "args": clean_args})
            res = engine_self.skill_registry.execute(
                "git_operations",
                action=action,
                message=message,
                branch=branch,
                target=target,
            )
            engine_self._emit_trace("tool_result", {"tool": "git_operations", "output": res})
            return res

        return [shell_execution, file_management, code_editing, git_operations]

    def _rebuild_graph(self):
        """Constructs and compiles the LangGraph StateGraph with tools bound."""
        chat_model = self.model_resolver.resolve_model(self.model_name)
        tools = self._build_tools()
        tools_by_name = {t.name: t for t in tools}
        model_with_tools = chat_model.bind_tools(tools)

        def agent_node(state: AgentState) -> dict:
            response = model_with_tools.invoke(state["messages"])
            
            # Extract reasoning/thinking from all potential model metadata locations
            reasoning = None
            if hasattr(response, "response_metadata") and response.response_metadata:
                reasoning = (
                    response.response_metadata.get("reasoning_content")
                    or response.response_metadata.get("thought")
                    or response.response_metadata.get("message", {}).get("reasoning_content")
                )

            if not reasoning and hasattr(response, "additional_kwargs") and response.additional_kwargs:
                reasoning = (
                    response.additional_kwargs.get("reasoning_content")
                    or response.additional_kwargs.get("thought")
                )

            # If model produced textual content alongside tool calls, that content is its thinking/rationale
            if not reasoning and hasattr(response, "tool_calls") and response.tool_calls and response.content:
                text_content = str(response.content).strip()
                if text_content:
                    reasoning = text_content

            if reasoning:
                # Strip <think>...</think> tags if present
                clean_thought = str(reasoning).replace("<think>", "").replace("</think>", "").strip()
                if clean_thought:
                    self._emit_trace("thinking", clean_thought)

            return {"messages": [response]}

        def tool_node(state: AgentState) -> dict:
            last_message = state["messages"][-1]
            tool_messages = []
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    t_name = tool_call["name"]
                    t_args = tool_call.get("args", {})
                    t_id = tool_call.get("id", "call_id")
                    
                    if t_name in tools_by_name:
                        tool_func = tools_by_name[t_name]
                        try:
                            res = tool_func.invoke(t_args)
                        except Exception as e:
                            res = f"Error executing tool {t_name}: {e}"
                    else:
                        res = f"Error: Tool '{t_name}' is not registered."

                    tool_messages.append(ToolMessage(content=str(res), tool_call_id=t_id, name=t_name))
            return {"messages": tool_messages}

        def should_continue(state: AgentState) -> str:
            last_msg = state["messages"][-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                return "tools"
            return END

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")

        self._compiled_graph = workflow.compile()

    def _build_system_prompt(self, user_request: str) -> str:
        """Constructs system prompt with OS/shell context, Tri-Tier Long-Term Memory, and session history."""
        env_ctx = get_env_context_string()

        long_term_ctx = ""
        if self.long_term_memory:
            long_term_ctx = self.long_term_memory.get_formatted_prompt_memory(user_request)

        session_ctx = self.memory_store.get_formatted_context()

        prompt_parts = [
            "You are Aegis, an expert autonomous AI Command Line Assistant operating directly in the user's terminal.",
            f"Environment Context:\n{env_ctx}",
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
            "4. Briefly state your concise thinking or plan before calling tools.\n"
            "5. Format final answers cleanly in Markdown."
        )

        return "\n\n".join(prompt_parts)

    def run_task(self, user_request: str) -> Dict[str, str]:
        """Executes task via LangGraph StateGraph, capturing trace and updating memory."""
        self._tools_invoked_in_turn = []
        system_prompt = self._build_system_prompt(user_request)

        initial_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request),
        ]

        nest_asyncio.apply()

        async def _execute():
            # Invoke StateGraph execution
            final_state = await self._compiled_graph.ainvoke({"messages": initial_messages})
            messages = final_state.get("messages", [])
            last_message = messages[-1] if messages else None
            output_content = last_message.content if last_message else ""
            if isinstance(output_content, list):
                output_str = "".join(str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in output_content)
            else:
                output_str = str(output_content)
            return output_str.strip()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    output_str = pool.submit(asyncio.run, _execute()).result()
            else:
                output_str = asyncio.run(_execute())
        except Exception as e:
            output_str = f"Error during LangGraph execution: {e}"

        # Determine routing / tools summary
        if self._tools_invoked_in_turn:
            unique_tools = list(dict.fromkeys(self._tools_invoked_in_turn))
            routing_info = f"[LangGraph Engine] Routed to skills: {', '.join(unique_tools)}"
        else:
            routing_info = "[LangGraph Engine] Direct completion (No tool execution needed)"

        # Save to Session Memory & Tri-Tier Long-Term Memory
        self.memory_store.add_turn(user_request, routing_info, output_str)
        if self.long_term_memory:
            self.long_term_memory.record_episode(
                user_prompt=user_request,
                solution_summary=output_str,
                tools_used=self._tools_invoked_in_turn,
            )

        return {"routing": routing_info, "execution": output_str}
