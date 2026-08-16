from cli_agent.commands.base import ISlashCommand, CommandContext

class HelpCommand(ISlashCommand):
    """Displays available interactive commands."""

    @property
    def name(self) -> str:
        return "/help"

    @property
    def description(self) -> str:
        return "Display help and available slash commands"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        console.print("[bold #38bdf8]Available Slash Commands:[/bold #38bdf8]")
        console.print("  [bold #38bdf8]/model[/bold #38bdf8]     - Switch LLM model or cloud provider")
        console.print("  [bold #38bdf8]/skills[/bold #38bdf8]    - View active skill palette and tools")
        console.print("  [bold #38bdf8]/memory[/bold #38bdf8]    - View Tri-Tier Long-Term Memory (/mem)")
        console.print("  [bold #38bdf8]/remember[/bold #38bdf8]  - Store project fact or global preference")
        console.print("  [bold #38bdf8]/forget[/bold #38bdf8]    - Delete a memory record (/forget <key>)")
        console.print("  [bold #38bdf8]/verbose[/bold #38bdf8]   - Toggle live thinking and tool execution trace (/trace)")
        console.print("  [bold #38bdf8]/clear[/bold #38bdf8]     - Clear session memory and buffer")
        console.print("  [bold #38bdf8]/help[/bold #38bdf8]      - Display this help menu")
        console.print("  [bold #38bdf8]/exit[/bold #38bdf8]      - Exit AI Command Line Agent\n")
        return True
