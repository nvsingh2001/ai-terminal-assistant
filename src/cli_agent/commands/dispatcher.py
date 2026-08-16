from typing import Dict, List
from cli_agent.commands.base import ISlashCommand, CommandContext

class CommandDispatcher:
    """
    Invoker in the Command Pattern.
    Routes user input to registered command handlers with fuzzy typo matching.
    """
    def __init__(self, context: CommandContext):
        self.context = context
        self._commands: Dict[str, ISlashCommand] = {}
        self._aliases: Dict[str, str] = {
            "exit": "/exit",
            "quit": "/exit",
            "/quit": "/exit",
            "clear": "/clear",
            "help": "/help"
        }

    def register(self, command: ISlashCommand):
        """Registers a slash command handler."""
        self._commands[command.name.lower()] = command

    def get_command_names(self) -> List[str]:
        """Returns list of registered command names for auto-completer."""
        return list(self._commands.keys()) + list(self._aliases.keys())

    def dispatch(self, user_input: str) -> bool:
        """
        Dispatches input to appropriate command.
        Returns True if handled as a command, False if it should be sent to the LLM.
        """
        clean_input = user_input.strip()
        if not clean_input:
            return False

        # Split command name and arguments
        parts = clean_input.split(maxsplit=1)
        raw_cmd = parts[0].lower()
        raw_args = parts[1] if len(parts) > 1 else ""

        # Check aliases
        if raw_cmd in self._aliases:
            target_name = self._aliases[raw_cmd]
            if target_name in self._commands:
                return self._commands[target_name].execute(self.context, raw_args)

        # Check exact command match
        if raw_cmd in self._commands:
            return self._commands[raw_cmd].execute(self.context, raw_args)

        # If starts with '/', it was intended as a command -> fuzzy suggestion
        if raw_cmd.startswith('/'):
            known = list(self._commands.keys())
            matches = [c for c in known if c.startswith(raw_cmd[:3])]
            hint = f" Did you mean '{matches[0]}'?" if matches else ""
            self.context.console.print(
                f"[bold #ef4444]Unknown command:[/bold #ef4444] [dim]{raw_cmd}[/dim].{hint} "
                f"Type [bold #38bdf8]/help[/bold #38bdf8] for available commands.\n"
            )
            return True

        return False
