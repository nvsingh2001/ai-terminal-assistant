import sys
from cli_agent.commands.base import ISlashCommand, CommandContext

class ExitCommand(ISlashCommand):
    """Exits the interactive agent REPL session."""

    @property
    def name(self) -> str:
        return "/exit"

    @property
    def description(self) -> str:
        return "Exit the AI Command Line Agent"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        context.console.print("[dim #94a3b8]Goodbye! Exiting AI Command Line Agent.[/dim #94a3b8]")
        sys.exit(0)
