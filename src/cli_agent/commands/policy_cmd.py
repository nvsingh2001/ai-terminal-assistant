from cli_agent.commands.base import CommandContext, ISlashCommand


class PolicyCommand(ISlashCommand):
    """Configures the human-in-the-loop execution safety policy (strict, trusted-read, yolo)."""

    @property
    def name(self) -> str:
        return "/policy"

    @property
    def aliases(self) -> list[str]:
        return ["/mode", "/safety"]

    @property
    def description(self) -> str:
        return "Configure human-in-the-loop safety policy (strict, trusted-read, yolo)"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        cfg = context.config_manager
        current_policy = cfg.config.execution_policy

        args = raw_args.strip().lower()
        if args in ("strict", "trusted-read", "yolo"):
            cfg.set_execution_policy(args)
            console.print(f"[bold #10b981]✓ Execution policy set to: [bold white]{args}[/bold white][/bold #10b981]\n")
            return True

        session = context.prompt_session
        console.print("[bold #38bdf8]Select Safety & Execution Policy:[/bold #38bdf8]")
        console.print(f"  1. [bold white]trusted-read[/bold white] (Auto-run read tools, confirm file edits & shell commands) {'[bold cyan]● Active[/bold cyan]' if current_policy == 'trusted-read' else ''}")
        console.print(f"  2. [bold white]strict[/bold white] (Confirm all file reads, edits, and shell commands) {'[bold cyan]● Active[/bold cyan]' if current_policy == 'strict' else ''}")
        console.print(f"  3. [bold white]yolo[/bold white] (Auto-apply all changes without interactive confirmation) {'[bold cyan]● Active[/bold cyan]' if current_policy == 'yolo' else ''}")

        try:
            choice = session.prompt("Enter choice (1-3) > ").strip()
            if choice == "1":
                cfg.set_execution_policy("trusted-read")
                console.print("[bold #10b981]✓ Execution policy set to: trusted-read[/bold #10b981]\n")
            elif choice == "2":
                cfg.set_execution_policy("strict")
                console.print("[bold #10b981]✓ Execution policy set to: strict[/bold #10b981]\n")
            elif choice == "3":
                cfg.set_execution_policy("yolo")
                console.print("[bold #f59e0b]⚠ Execution policy set to: yolo (Auto-apply enabled)[/bold #f59e0b]\n")
        except (KeyboardInterrupt, EOFError):
            console.print()

        return True
