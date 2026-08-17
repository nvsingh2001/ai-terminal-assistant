from cli_agent.commands.base import CommandContext, ISlashCommand


class ForgetCommand(ISlashCommand):
    """
    Deletes a memory record or clears active project knowledge.
    """
    @property
    def name(self) -> str:
        return "/forget"

    @property
    def description(self) -> str:
        return "Delete a persistent memory record (/forget <key|id> or /forget --all)"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        memory_mgr = context.tri_tier_memory
        if not memory_mgr:
            console.print("[dim #94a3b8]Long-term memory manager is not initialized.[/dim #94a3b8]\n")
            return True

        args_str = raw_args.strip()
        if not args_str:
            console.print("[bold #ef4444]Usage:[/bold #ef4444] `/forget <key|id>` or `/forget --all`\n")
            return True

        if args_str == "--all":
            memory_mgr.clear_project()
            console.print(f"[bold #f59e0b]○ Cleared all project memory for {memory_mgr.project_id}.[/bold #f59e0b]\n")
            return True

        # Try deleting as project fact
        if memory_mgr.delete_memory("project", args_str):
            console.print(f"[bold #10b981]✓ Deleted project fact:[/bold #10b981] [dim #94a3b8]{args_str}[/dim #94a3b8]\n")
            return True

        # Try deleting as global preference
        if memory_mgr.delete_memory("global", args_str):
            console.print(f"[bold #10b981]✓ Deleted global preference:[/bold #10b981] [dim #94a3b8]{args_str}[/dim #94a3b8]\n")
            return True

        # Try deleting as episode ID
        if args_str.isdigit():
            if memory_mgr.delete_memory("episode", args_str):
                console.print(f"[bold #10b981]✓ Deleted episodic record ID:[/bold #10b981] [dim #94a3b8]{args_str}[/dim #94a3b8]\n")
                return True

        console.print(f"[bold #ef4444]Memory record '{args_str}' not found.[/bold #ef4444] Type `/memory` to view active records.\n")
        return True
