from cli_agent.commands.base import CommandContext, ISlashCommand


class ClearCommand(ISlashCommand):
    """Clears conversation buffer and session memory."""

    @property
    def name(self) -> str:
        return "/clear"

    @property
    def description(self) -> str:
        return "Clear active conversation history and session memory"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        context.memory_store.clear()
        context.console.print("[bold #a855f7]⚡ Session memory cleared.[/bold #a855f7]\n")
        return True
