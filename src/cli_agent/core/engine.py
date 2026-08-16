import os
import json
from typing import Dict, Any, List, Optional, AsyncIterator
import litellm
from cli_agent.skills import skill_registry
from cli_agent.services.memory_manager import session_memory
from cli_agent.services.env_detector import get_env_context_string

from cli_agent.core.config_manager import config_manager

class DirectAgentEngine:
    """
    High-performance native agent execution engine operating directly via LiteLLM / Ollama / llama.cpp
    without CrewAI framework overhead.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config_manager.config.model_name
        # Ensure litellm provider prefix if ollama
        if not ("/" in self.model_name or self.model_name.startswith("ollama")):
            self.model_name = f"ollama/{self.model_name}"

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Converts registered skills into OpenAI-compatible tool calling schemas."""
        tools = []
        for manifest in skill_registry.list_skills():
            tools.append({
                "type": "function",
                "function": {
                    "name": manifest.name,
                    "description": manifest.description,
                    "parameters": manifest.parameters_schema
                }
            })
        return tools

    def run_task(self, user_request: str) -> Dict[str, str]:
        """
        Executes a user request directly using function calling and skill invocation loops.
        Returns a dict containing 'routing' intent summary and 'execution' result.
        """
        env_ctx = get_env_context_string()
        history_ctx = session_memory.get_formatted_context()

        system_prompt = (
            "You are an expert AI Command Line Assistant operating on the user's terminal.\n"
            f"Environment Context: {env_ctx}\n"
            f"Prior Conversation Memory:\n{history_ctx}\n\n"
            "Use available skills (tools) to fulfill the user's request. "
            "Never execute destructive actions without user intent. Keep final answers concise and formatted in Markdown."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]

        tools_schema = self.get_tool_schemas()
        routing_summary = f"**[Direct Engine Routing]** Processing via native function calling schema with {len(tools_schema)} active skills."
        
        max_turns = 10
        turn_count = 0
        final_output = ""

        from cli_agent.core.llm import HybridLLMEngine
        hybrid_llm = HybridLLMEngine(self.model_name)

        while turn_count < max_turns:
            turn_count += 1
            try:
                response = hybrid_llm.complete(
                    messages=messages,
                    tools=tools_schema if tools_schema else None
                )

                response_message = response.choices[0].message
                messages.append(response_message)

                # Check if model invoked tool calls
                if hasattr(response_message, "tool_calls") and response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except Exception:
                            function_args = {}

                        # Execute skill via SkillRegistry
                        skill_output = skill_registry.execute(function_name, **function_args)

                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(skill_output)
                        })
                else:
                    # Model returned final answer
                    final_output = response_message.content or "Task completed."
                    break

            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "not found" in err_msg:
                    err_msg = f"Model '{self.model_name}' not found. Please check OLLAMA_MODEL_NAME setting."
                return {
                    "routing": "Routing error encountered.",
                    "execution": f"Error executing task: {err_msg}"
                }

        if not final_output and messages:
            final_output = messages[-1].get("content", "Task executed successfully.")

        session_memory.add_turn(user_request, "DirectEngine", final_output)
        return {
            "routing": routing_summary,
            "execution": final_output
        }
