import os
import json
import re
from typing import Dict, Any, List, Optional
from cli_agent.skills import skill_registry
from cli_agent.services.memory_manager import session_memory
from cli_agent.services.env_detector import get_env_context_string
from cli_agent.core.config_manager import config_manager
from cli_agent.core.llm import HybridLLMEngine

def extract_raw_json_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    Extracts raw JSON tool calls emitted in plain text by open-source models like Gemma, Qwen, Mistral.
    Matches formats like:
    - {"name": "file_management", "arguments": {"action": "read", "path": "..."}}
    - ```json {"name": "file_management", "arguments": {...}} ```
    """
    if not text:
        return []

    clean_text = text.strip()
    # Remove markdown code blocks if wrapped in ```json ... ```
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)

    # Check direct JSON dictionary
    try:
        data = json.loads(clean_text)
        if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
            args = data.get("arguments", data.get("parameters", {}))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            return [{"name": data["name"], "arguments": args}]
        if isinstance(data, list):
            calls = []
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    calls.append({"name": item["name"], "arguments": item.get("arguments", item.get("parameters", {}))})
            if calls:
                return calls
    except Exception:
        pass

    # Regex search for embedded JSON tool call objects
    matches = re.findall(r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"(?:arguments|parameters)"\s*:\s*\{.*?\}\s*\}', text, re.DOTALL)
    calls = []
    for m in matches:
        try:
            parsed = json.loads(m)
            if "name" in parsed:
                calls.append({"name": parsed["name"], "arguments": parsed.get("arguments", parsed.get("parameters", {}))})
        except Exception:
            continue

    return calls


class DirectAgentEngine:
    """
    High-performance native agent execution engine operating directly via LiteLLM / Ollama / llama.cpp
    with robust function calling, raw JSON tool call parsing, and fallback synthesis.
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
        registered_skill_names = {s.name for s in skill_registry.list_skills()}
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

                # 1. Check formal OpenAI-style tool calls
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

                # 2. Check for raw JSON tool calls emitted in content by open-source models
                raw_calls = extract_raw_json_tool_calls(content)
                valid_raw_calls = [c for c in raw_calls if c["name"] in registered_skill_names]

                if valid_raw_calls:
                    messages.append({"role": "assistant", "content": content})
                    for call in valid_raw_calls:
                        function_name = call["name"]
                        function_args = call.get("arguments", {})
                        if not isinstance(function_args, dict):
                            function_args = {}

                        skill_output = skill_registry.execute(function_name, **function_args)
                        executed_tool_results.append(f"**[{function_name}]**\n{skill_output}")

                        messages.append({
                            "role": "tool",
                            "name": function_name,
                            "content": str(skill_output)
                        })
                    continue

                # 3. Model returned real final answer content
                if content:
                    final_output = content
                    break

                # 4. If tools were executed in previous turns, synthesize output
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
