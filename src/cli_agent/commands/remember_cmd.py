from cli_agent.commands.base import CommandContext, ISlashCommand


class RememberCommand(ISlashCommand):
    """
    Stores an architectural rule, environment convention, or user preference into Long-Term Memory.
    """
    @property
    def name(self) -> str:
        return "/remember"

    @property
    def aliases(self) -> list[str]:
        return ["/learn"]

    @property
    def description(self) -> str:
        return "Teach the agent a persistent fact or preference (/remember [--global] <fact>)"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        memory_mgr = context.tri_tier_memory
        if not memory_mgr:
            console.print("[dim #94a3b8]Long-term memory manager is not initialized.[/dim #94a3b8]\n")
            return True

        args_str = raw_args.strip()
        if not args_str:
            console.print("[bold #ef4444]Usage:[/bold #ef4444] `/remember <fact>` or `/remember --global <preference>`\n")
            console.print("  [dim #94a3b8]Examples:[/dim #94a3b8]")
            console.print("  • [bold #38bdf8]/remember[/bold #38bdf8] [dim]database is DuckDB star-schema[/dim]")
            console.print("  • [bold #38bdf8]/remember[/bold #38bdf8] [dim]virtualenv=./venv[/dim]")
            console.print("  • [bold #38bdf8]/remember --global[/bold #38bdf8] [dim]preferred_shell=bash[/dim]\n")
            return True

        is_global = False
        if args_str.startswith("--global"):
            is_global = True
            args_str = args_str.replace("--global", "", 1).strip()

        if "=" in args_str:
            key, val = args_str.split("=", 1)
            key, val = key.strip(), val.strip()
        elif ":" in args_str:
            key, val = args_str.split(":", 1)
            key, val = key.strip(), val.strip()
        else:
            # Derive key from first few words
            words = args_str.split()
            key = "_".join(words[:3]).lower()
            val = args_str

        if is_global:
            memory_mgr.set_global_preference(key, val)
            console.print(f"[bold #10b981]✓ Global Preference Saved:[/bold #10b981] [bold #38bdf8]{key}[/bold #38bdf8] = [dim #94a3b8]{val}[/dim #94a3b8]\n")
        else:
            memory_mgr.set_project_fact(key, val, category="custom")
            console.print(f"[bold #10b981]✓ Project Fact Saved ({memory_mgr.project_id}):[/bold #10b981] [bold #a855f7]{key}[/bold #a855f7] = [dim #94a3b8]{val}[/dim #94a3b8]\n")

        return True
