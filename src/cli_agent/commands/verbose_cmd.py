from cli_agent.commands.base import ISlashCommand, CommandContext

class VerboseCommand(ISlashCommand):
    """
    Toggles verbose trace mode to view intermediate thinking and tool execution details.
    """
    @property
    def name(self) -> str:
        return "/verbose"

    @property
    def aliases(self) -> list[str]:
        return ["/trace", "/debug"]

    @property
    def description(self) -> str:
        return "Toggle live thinking and tool execution trace mode on/off"

    def execute(self, context: CommandContext, args: list[str]) -> bool:
        current = context.config_manager.config.verbose
        new_state = not current
        context.config_manager.set_verbose(new_state)
        context.engine.set_verbose(new_state)

        if new_state:
            context.console.print("[bold #10b981]✓ Verbose Trace Mode: ENABLED[/bold #10b981]")
            context.console.print("  [dim #94a3b8]Live thinking and tool execution steps will be shown in real time.[/dim #94a3b8]\n")
        else:
            context.console.print("[bold #f59e0b]○ Verbose Trace Mode: DISABLED[/bold #f59e0b]")
            context.console.print("  [dim #94a3b8]Compact output mode restored.[/dim #94a3b8]\n")
            
        return True
