import asyncio
import os
from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, Sequence, Type, TypedDict

import nest_asyncio
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, create_model

from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.core.llm.langchain_resolver import LangChainModelResolver
from cli_agent.memory.manager import TriTierMemoryManager
from cli_agent.services.env_detector import get_env_context_string
from cli_agent.services.memory_manager import ConversationMemory
from cli_agent.skills.base import BaseSkill
from cli_agent.skills.registry import SkillRegistry

_JSON_SCHEMA_TYPES: Dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def _schema_to_pydantic_model(skill_name: str, schema: Optional[Dict[str, Any]]) -> Type[BaseModel]:
    """Converts a SkillManifest's JSON-schema `parameters_schema` into a Pydantic
    model for use as a LangChain tool's `args_schema`.

    The manifest is each skill's single source of truth for what it does and
    accepts - deriving the tool schema from it (instead of a hand-typed
    function signature) keeps what the LLM sees permanently in sync with what
    the skill actually implements, and covers user-custom skills too.
    """
    properties = (schema or {}).get("properties", {})
    required = set((schema or {}).get("required", []))
    fields: Dict[str, Any] = {}
    for field_name, field_schema in properties.items():
        base_type = _JSON_SCHEMA_TYPES.get(field_schema.get("type", "string"), str)
        if "enum" in field_schema:
            base_type = Literal[tuple(field_schema["enum"])]
        description = field_schema.get("description", "")
        if field_name in required:
            fields[field_name] = (base_type, Field(..., description=description))
        else:
            fields[field_name] = (Optional[base_type], Field(default=None, description=description))
    model_name = "".join(part.title() for part in skill_name.split("_")) + "Args"
    return create_model(model_name, **fields)


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

    def _make_tool(self, skill: BaseSkill) -> StructuredTool:
        """Wraps a single skill as a LangChain StructuredTool, deriving its name,
        description, and argument schema from the skill's own SkillManifest."""
        manifest = skill.manifest
        skill_name = manifest.name
        args_model = _schema_to_pydantic_model(skill_name, manifest.parameters_schema)
        engine_self = self

        def _run(**kwargs) -> str:
            clean_args = {k: v for k, v in kwargs.items() if v is not None}
            engine_self._tools_invoked_in_turn.append(skill_name)
            engine_self._emit_trace("tool_call", {"tool": skill_name, "args": clean_args})
            res = engine_self.skill_registry.execute(skill_name, **clean_args)
            engine_self._emit_trace("tool_result", {"tool": skill_name, "output": res})
            return res

        return StructuredTool.from_function(
            func=_run,
            name=skill_name,
            description=manifest.description,
            args_schema=args_model,
        )

    def _build_tools(self) -> list:
        """Builds one LangChain tool per skill registered in the SkillRegistry -
        built-in and user-custom alike - instead of a fixed, hand-maintained set."""
        return [self._make_tool(skill) for skill in self.skill_registry.get_all_skills()]

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
