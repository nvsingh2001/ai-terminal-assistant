from cli_agent.commands.base import CommandContext, ISlashCommand
from cli_agent.core.safety.rollback import rollback_manager


class UndoCommand(ISlashCommand):
    """Reverts the most recent AI modification, restoring affected files to their exact pre-edit state."""

    @property
    def name(self) -> str:
        return "/undo"

    @property
    def aliases(self) -> list[str]:
        return ["/revert", "/rollback"]

    @property
    def description(self) -> str:
        return "Instantly revert the most recent AI file modification (/undo)"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        restored = rollback_manager.rollback_last_transaction()

        if not restored:
            console.print("[bold #f59e0b]○ No previous edit transactions found to undo.[/bold #f59e0b]\n")
            return True

        console.print("[bold #10b981]✓ Rollback Successful: Reverted the following file(s):[/bold #10b981]")
        for f in restored:
            console.print(f"  • [dim #94a3b8]{f}[/dim #94a3b8]")
        console.print()

        return True
