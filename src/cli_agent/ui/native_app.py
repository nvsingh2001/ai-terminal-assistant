import sys
import os
from typing import Optional

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
    """

    def __init__(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        self.sys_info = get_system_info()
        
        # Initialize PromptSession
        self.session = PromptSession(
            history=FileHistory(HISTORY_FILE),
            completer=WordCompleter(['/model', '/skills', '/clear', '/help', '/exit', '/quit'])
        )

        # Wire all dependencies through DI Container
        self.container = ServiceContainer.create_default(
            console=console,
            prompt_session=self.session
        )

        # Update completer with all registered commands and aliases
        self.session.completer = WordCompleter(self.container.dispatcher.get_command_names())

    @property
    def model_name(self) -> str:
        return self.container.config_manager.config.model_name

    def print_header(self):
        """Displays minimalist 1-line startup banner."""
        active_skills_count = len(self.container.skill_registry.list_skills())
        branch = self.sys_info.get('git_branch', 'main')
        
        console.print()
        console.print(f"[bold #10b981]✦ AI COMMAND LINE AGENT[/bold #10b981] [dim #94a3b8]v2.0[/dim #94a3b8]")
        console.print(f"  [dim #94a3b8]Model:[/dim #94a3b8] [bold #38bdf8]{self.model_name}[/bold #38bdf8]  │  [dim #94a3b8]Branch:[/dim #94a3b8] [dim #f8fafc]{branch}[/dim #f8fafc]  │  [dim #94a3b8]Skills:[/dim #94a3b8] [bold #a855f7]{active_skills_count} loaded[/bold #a855f7]")
        console.print(f"  [dim #64748b]Type instructions or [/dim #64748b][bold #38bdf8]/help[/bold #38bdf8][dim #64748b] for slash commands, [/dim #64748b][bold #38bdf8]/model[/bold #38bdf8][dim #64748b] to switch models, [/dim #64748b][bold #38bdf8]/skills[/bold #38bdf8][dim #64748b] for palette.[/dim #64748b]")
        console.print()

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

        # PydanticAI Agent execution with live spinner
        with Live(Spinner("dots", text="[bold #38bdf8]Thinking & Executing...[/bold #38bdf8]"), console=console, transient=True):
            res = self.container.engine.run_task(req_clean)

        routing_info = res.get("routing", "PydanticAI Routing")
        exec_output = res.get("execution", "")

        console.print(f"[bold #a855f7]⚡ Skill Routing:[/bold #a855f7] [dim #94a3b8]{routing_info}[/dim #94a3b8]\n")
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
                if user_input.startswith('/') or user_input.lower() in ['exit', 'quit', 'clear', 'help']:
                    if self.container.dispatcher.dispatch(user_input):
                        continue

                self.execute_request(user_input)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim #94a3b8]Exiting AI Command Line Agent.[/dim #94a3b8]")
                sys.exit(0)


def run_native_app():
    agent = NativeCLIAgent()
    agent.run()
