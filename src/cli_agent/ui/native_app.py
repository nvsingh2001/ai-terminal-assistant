import sys
import os
import re
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter

from cli_agent.core.engine import DirectAgentEngine
from cli_agent.core.config_manager import config_manager
from cli_agent.services import (
    try_fast_path_execution, session_memory,
    get_system_info, get_env_context_string, history_manager
)
from cli_agent.skills import skill_registry

# Rich Console instance
console = Console()

# Prompt Toolkit Styling
prompt_style = PTStyle.from_dict({
    'prompt': 'bold #38bdf8',
})

HISTORY_FILE = os.path.expanduser("~/.cli-agent/history.txt")

class NativeCLIAgent:
    """
    Next-Gen Box-Free & Card-Free Native Terminal Interface.
    Inspired by claude-code, antigravity-cli, OpenCode, and hermes agent.
    Runs 100% natively in standard terminal scrollback without screen overlays.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        self.session = PromptSession(
            history=FileHistory(HISTORY_FILE),
            completer=WordCompleter(['/model', '/skills', '/clear', '/help', '/exit', '/quit'])
        )
        self.sys_info = get_system_info()
        self.model_name = config_manager.config.model_name

    def print_header(self):
        """Displays minimalist 1-line startup banner."""
        active_skills_count = len(skill_registry.list_skills())
        branch = self.sys_info.get('git_branch', 'main')
        
        console.print()
        console.print(f"[bold #10b981]✦ AI COMMAND LINE AGENT[/bold #10b981] [dim #94a3b8]v2.0[/dim #94a3b8]")
        console.print(f"  [dim #94a3b8]Model:[/dim #94a3b8] [bold #38bdf8]{self.model_name}[/bold #38bdf8]  │  [dim #94a3b8]Branch:[/dim #94a3b8] [dim #f8fafc]{branch}[/dim #f8fafc]  │  [dim #94a3b8]Skills:[/dim #94a3b8] [bold #a855f7]{active_skills_count} loaded[/bold #a855f7]")
        console.print(f"  [dim #64748b]Type instructions or [/dim #64748b][bold #38bdf8]/help[/bold #38bdf8][dim #64748b] for slash commands, [/dim #64748b][bold #38bdf8]/model[/bold #38bdf8][dim #64748b] to switch models, [/dim #64748b][bold #38bdf8]/skills[/bold #38bdf8][dim #64748b] for palette.[/dim #64748b]")
        console.print()

    def handle_slash_command(self, cmd: str) -> bool:
        """Handles native slash commands (/model, /skills, /clear, /help, /exit)."""
        clean_cmd = cmd.strip().lower()

        if clean_cmd in ['/exit', '/quit', 'exit', 'quit']:
            console.print("[dim #94a3b8]Goodbye! Exiting AI Command Line Agent.[/dim #94a3b8]")
            sys.exit(0)

        elif clean_cmd in ['/clear', 'clear']:
            session_memory.clear()
            console.print("[bold #a855f7]⚡ Session memory cleared.[/bold #a855f7]\n")
            return True

        elif clean_cmd == '/skills':
            skills = skill_registry.list_skills()
            table = Table(title="[bold #a855f7]⚡ Registered Skills[/bold #a855f7]", show_header=True, header_style="bold #38bdf8")
            table.add_column("Skill Name", style="bold #f8fafc")
            table.add_column("Description", style="dim #94a3b8")
            table.add_column("Version", style="dim #64748b")

            for s in skills:
                table.add_row(s.name, s.description, s.version)

            console.print(table)
            console.print()
            return True

        elif clean_cmd == '/model':
            console.print("[bold #38bdf8]Select LLM Provider / Model:[/bold #38bdf8]")
            console.print("  1. ollama/qwen3.5:4b [Local Ollama - Pulled]")
            console.print("  2. Local llama.cpp GGUF file path (e.g. /path/to/model.gguf)")
            console.print("  3. gemini/gemini-1.5-flash [Google Gemini Cloud API]")
            console.print("  4. openai/gpt-4o-mini [OpenAI Cloud API]")
            console.print("  5. Custom model string")
            
            try:
                choice = self.session.prompt("Enter choice (1-5) > ").strip()
                new_model = ""
                if choice == "1":
                    new_model = "ollama/qwen3.5:4b"
                elif choice == "2":
                    gguf_path = self.session.prompt("Enter absolute path to your .gguf file > ").strip()
                    if os.path.exists(gguf_path):
                        new_model = gguf_path
                    else:
                        console.print(f"[bold #ef4444]File not found: {gguf_path}[/bold #ef4444]\n")
                        return True
                elif choice == "3":
                    new_model = "gemini/gemini-1.5-flash"
                    if not os.getenv("GEMINI_API_KEY"):
                        key = self.session.prompt("Enter GEMINI_API_KEY > ").strip()
                        if key:
                            os.environ["GEMINI_API_KEY"] = key
                            config_manager.config.api_keys["gemini"] = key
                            config_manager.save_config(config_manager.config)
                elif choice == "4":
                    new_model = "openai/gpt-4o-mini"
                    if not os.getenv("OPENAI_API_KEY"):
                        key = self.session.prompt("Enter OPENAI_API_KEY > ").strip()
                        if key:
                            os.environ["OPENAI_API_KEY"] = key
                            config_manager.config.api_keys["openai"] = key
                            config_manager.save_config(config_manager.config)
                elif choice == "5":
                    new_model = self.session.prompt("Enter model string or path (e.g. ollama/llama3.2 or /path/model.gguf) > ").strip()

                if new_model:
                    config_manager.set_model(new_model)
                    self.model_name = new_model
                    console.print(f"[bold #10b981]✓ Active model updated to: {new_model}[/bold #10b981]\n")
            except (KeyboardInterrupt, EOFError):
                console.print()
            return True

        elif clean_cmd in ['/help', 'help']:
            console.print("[bold #38bdf8]Available Commands:[/bold #38bdf8]")
            console.print("  [bold #38bdf8]/model[/bold #38bdf8]   - Switch LLM model/provider")
            console.print("  [bold #38bdf8]/skills[/bold #38bdf8]  - View active skill palette")
            console.print("  [bold #38bdf8]/clear[/bold #38bdf8]   - Clear session memory buffer")
            console.print("  [bold #38bdf8]/help[/bold #38bdf8]    - Display this help menu")
            console.print("  [bold #38bdf8]/exit[/bold #38bdf8]    - Exit the assistant\n")
            return True

        return False

    def execute_request(self, user_request: str):
        """Processes user request with fast-path execution and DirectAgentEngine."""
        req_clean = user_request.strip()

        # Check for fast-path execution
        fast_res = try_fast_path_execution(req_clean)
        if fast_res:
            routing_str, exec_output = fast_res
            session_memory.add_turn(req_clean, routing_str, exec_output)
            console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]{routing_str}[/dim #94a3b8]")
            console.print()
            self._render_output(exec_output)
            console.print()
            return

        # Direct Agent Engine execution with live spinner
        engine = DirectAgentEngine()
        with Live(Spinner("dots", text="[bold #38bdf8]Thinking & Executing...[/bold #38bdf8]"), console=console, transient=True):
            res = engine.run_task(req_clean)

        routing_info = res.get("routing", "Direct Routing")
        exec_output = res.get("execution", "")

        console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]{routing_info}[/dim #94a3b8]")
        console.print()
        self._render_output(exec_output)
        console.print()

    def _render_output(self, output: str):
        """Renders execution output using Rich Markdown for proper formatting."""
        if not output:
            return

        try:
            md = Markdown(output)
            console.print(md)
        except Exception:
            # Fallback to plain text if markdown parsing fails
            console.print(output)

    def run(self):
        """Main Native REPL Loop."""
        self.print_header()

        while True:
            try:
                user_input = self.session.prompt([('class:prompt', '❯ ')], style=prompt_style).strip()
                if not user_input:
                    continue

                if user_input.startswith('/') or user_input.lower() in ['exit', 'quit', 'clear', 'help']:
                    if self.handle_slash_command(user_input):
                        continue
                    # Unknown slash command — show hint instead of sending to LLM
                    if user_input.startswith('/'):
                        known = ['/model', '/skills', '/clear', '/help', '/exit', '/quit']
                        # Simple fuzzy match: find closest command
                        close = [c for c in known if c.startswith(user_input[:3])]
                        hint = f" Did you mean {close[0]}?" if close else ""
                        console.print(f"[bold #ef4444]Unknown command:[/bold #ef4444] [dim]{user_input}[/dim].{hint} Type [bold #38bdf8]/help[/bold #38bdf8] for available commands.\n")
                        continue

                self.execute_request(user_input)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim #94a3b8]Exiting AI Command Line Agent.[/dim #94a3b8]")
                sys.exit(0)


def run_native_app():
    agent = NativeCLIAgent()
    agent.run()
