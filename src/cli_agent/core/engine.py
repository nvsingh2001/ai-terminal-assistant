import os
import json
from typing import Dict, Any, List, Optional
from cli_agent.skills import skill_registry
from cli_agent.services.memory_manager import session_memory
from cli_agent.services.env_detector import get_env_context_string
from cli_agent.core.config_manager import config_manager
from cli_agent.core.llm import HybridLLMEngine

class DirectAgentEngine:
    """
    High-performance native agent execution engine operating directly via LiteLLM / Ollama / llama.cpp
    with robust function calling and fallback synthesis.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config_manager.config.model_name
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
        
        max_turns = 8
        turn_count = 0
        final_output = ""
        executed_tool_results = []

        hybrid_llm = HybridLLMEngine(self.model_name)

        while turn_count < max_turns:
            turn_count += 1
            try:
                response = hybrid_llm.complete(
                    messages=messages,
                    tools=tools_schema if tools_schema else None
                )

                if isinstance(response, dict) and response.get("error"):
                    return {
                        "routing": "Model Provider Notice",
                        "execution": response["error"]
                    }

                response_message = response.choices[0].message
                content = (response_message.content or "").strip()
                tool_calls = getattr(response_message, "tool_calls", None)

                # Case 1: Model executed function tool calls
                if tool_calls:
                    messages.append(response_message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except Exception:
                            function_args = {}

                        # Execute skill via SkillRegistry
                        skill_output = skill_registry.execute(function_name, **function_args)
                        executed_tool_results.append(f"**[{function_name}]**\n{skill_output}")

                        messages.append({
                            "tool_call_id": getattr(tool_call, "id", f"call_{len(messages)}"),
                            "role": "tool",
                            "name": function_name,
                            "content": str(skill_output)
                        })
                    continue

                # Case 2: Model returned non-empty content
                if content:
                    final_output = content
                    break

                # Case 3: Model returned empty content and no tool calls
                # Fallback: Retry with direct prompt completion without tool schema
                retry_res = hybrid_llm.complete(messages=messages, tools=None)
                if not (isinstance(retry_res, dict) and retry_res.get("error")):
                    retry_content = (retry_res.choices[0].message.content or "").strip()
                    if retry_content:
                        final_output = retry_content
                        break

                # If tools were executed, return their combined output
                if executed_tool_results:
                    final_output = "\n\n".join(executed_tool_results)
                    break

                final_output = "I was unable to generate a response. Please check your model connection or try a different model."
                break

            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "not found" in err_msg:
                    err_msg = f"Model '{self.model_name}' not found. Please check your model configuration."
                return {
                    "routing": "Routing error encountered.",
                    "execution": f"Error executing task: {err_msg}"
                }

        if not final_output:
            if executed_tool_results:
                final_output = "\n\n".join(executed_tool_results)
            else:
                final_output = "Task executed successfully."

        session_memory.add_turn(user_request, "DirectEngine", final_output)
        return {
            "routing": routing_summary,
            "execution": final_output
        }
