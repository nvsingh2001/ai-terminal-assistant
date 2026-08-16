import sys
import os
from typing import Optional, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter

from cli_agent.container import ServiceContainer
from cli_agent.services import try_fast_path_execution, get_system_info
from cli_agent.ui.banner import print_aegis_banner

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
    Architected with clean Dependency Injection, Command Pattern, and PydanticAI.
    Supports real-time thinking, tool execution trace (/verbose), and Tri-Tier Long-Term Memory (/memory).
    """

    def __init__(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        self.sys_info = get_system_info()
        
        # Initialize PromptSession
        self.session = PromptSession(
            history=FileHistory(HISTORY_FILE),
            completer=WordCompleter([
                '/model', '/skills', '/memory', '/remember', '/forget',
                '/verbose', '/trace', '/clear', '/help', '/exit', '/quit'
            ])
        )

        # Wire all dependencies through DI Container
        self.container = ServiceContainer.create_default(
            console=console,
            prompt_session=self.session
        )

        # Connect real-time trace callback for live thinking & tool invocation inspection
        self.container.engine.set_trace_callback(self._handle_trace_event)

        # Update completer with all registered commands and aliases
        self.session.completer = WordCompleter(self.container.dispatcher.get_command_names())

    @property
    def model_name(self) -> str:
        return self.container.config_manager.config.model_name

    @property
    def verbose_enabled(self) -> bool:
        return self.container.config_manager.config.verbose

    def _handle_trace_event(self, event_type: str, data: Any):
        """Displays real-time thinking and tool execution steps when verbose mode is active."""
        if not self.verbose_enabled:
            return

        if event_type == "thinking":
            console.print(f"[bold #a78bfa]💭 Thinking:[/bold #a78bfa] [dim italic #e2e8f0]{data}[/dim italic #e2e8f0]\n")

        elif event_type == "tool_call":
            tool_name = data.get("tool", "tool")
            args = data.get("args", {})
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
            console.print(f"[bold #38bdf8]⚙ Executing:[/bold #38bdf8] [bold yellow]{tool_name}[/bold yellow]([dim #94a3b8]{args_str}[/dim #94a3b8])")

        elif event_type == "tool_result":
            output = str(data.get("output", "")).strip()
            preview = output[:300].replace("\n", " ") + ("..." if len(output) > 300 else "")
            console.print(f"  [dim #94a3b8]↳ Result: {preview}[/dim #94a3b8]\n")

    def print_header(self):
        """Displays Aegis ANSI art logo and startup status bar."""
        active_skills_count = len(self.container.skill_registry.list_skills())
        branch = self.sys_info.get('git_branch', 'main')
        proj_id = self.container.tri_tier_memory.project_id
        print_aegis_banner(
            console=console,
            model_name=self.model_name,
            git_branch=branch,
            skills_count=active_skills_count,
            verbose_enabled=self.verbose_enabled,
            project_id=proj_id
        )

    def execute_request(self, user_request: str):
        """Processes user request with fast-path execution and PydanticAgentEngine."""
        req_clean = user_request.strip()

        # Check for fast-path execution
        fast_res = try_fast_path_execution(req_clean)
        if fast_res:
            routing_str, exec_output = fast_res
            self.container.memory_store.add_turn(req_clean, routing_str, exec_output)
            console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]{routing_str}[/dim #94a3b8]\n")
            self._render_output(exec_output)
            console.print()
            return

        # PydanticAI Agent execution
        if self.verbose_enabled:
            console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]**[PydanticAI Engine]** Trace mode active with Long-Term Memory[/dim #94a3b8]\n")
            res = self.container.engine.run_task(req_clean)
        else:
            with Live(Spinner("dots", text="[bold #38bdf8]Thinking & Executing...[/bold #38bdf8]"), console=console, transient=True):
                res = self.container.engine.run_task(req_clean)
            routing_info = res.get("routing", "PydanticAI Routing")
            console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]{routing_info}[/dim #94a3b8]\n")

        exec_output = res.get("execution", "")
        self._render_output(exec_output)
        console.print()

    def _render_output(self, output: str):
        """Renders execution output using Rich Markdown for high-quality terminal formatting."""
        if not output:
            return

        try:
            md = Markdown(output)
            console.print(md)
        except Exception:
            console.print(output)

    def run(self):
        """Main Native REPL Loop."""
        self.print_header()

        while True:
            try:
                user_input = self.session.prompt([('class:prompt', '❯ ')], style=prompt_style).strip()
                if not user_input:
                    continue

                # Delegate slash commands to CommandDispatcher
                if user_input.startswith('/') or user_input.lower() in ['exit', 'quit', 'clear', 'help', 'verbose', 'trace', 'memory', 'remember']:
                    if self.container.dispatcher.dispatch(user_input):
                        continue

                self.execute_request(user_input)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim #94a3b8]Exiting AI Command Line Agent.[/dim #94a3b8]")
                sys.exit(0)


def run_native_app():
    agent = NativeCLIAgent()
    agent.run()
