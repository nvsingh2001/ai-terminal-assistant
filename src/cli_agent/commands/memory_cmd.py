from rich.table import Table
from rich.panel import Panel
from cli_agent.commands.base import ISlashCommand, CommandContext

class MemoryCommand(ISlashCommand):
    """
    Displays the active Tri-Tier Long-Term Memory (Global Preferences, Project Knowledge, Episodic History).
    """
    @property
    def name(self) -> str:
        return "/memory"

    @property
    def aliases(self) -> list[str]:
        return ["/mem", "/knowledge"]

    @property
    def description(self) -> str:
        return "Display active Tri-Tier Long-Term Memory store"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        memory_mgr = context.tri_tier_memory
        if not memory_mgr:
            console.print("[dim #94a3b8]Long-term memory manager is not initialized.[/dim #94a3b8]\n")
            return True

        memory_mgr.update_project_context()
        proj_id = memory_mgr.project_id

        console.print()
        console.print(f"[bold #10b981]✦ TRI-TIER LONG-TERM MEMORY STORE[/bold #10b981]  [dim #94a3b8](Project: {proj_id})[/dim #94a3b8]")
        console.print()

        # Tier 1: Global Preferences Table
        global_prefs = memory_mgr.get_global_preferences()
        g_table = Table(title="[bold #38bdf8]Tier 1: Global User Preferences[/bold #38bdf8]", show_header=True, header_style="bold #38bdf8")
        g_table.add_column("Key", style="bold #f8fafc", width=25)
        g_table.add_column("Preference Value", style="dim #94a3b8")
        if global_prefs:
            for k, v in global_prefs.items():
                g_table.add_row(k, v)
        else:
            g_table.add_row("(No global preferences set)", "Use /remember --global key=value")
        console.print(g_table)
        console.print()

        # Tier 2: Project Knowledge Table
        project_facts = memory_mgr.get_project_facts()
        p_table = Table(title=f"[bold #a855f7]Tier 2: Project Knowledge & Architectural Rules[/bold #a855f7]", show_header=True, header_style="bold #a855f7")
        p_table.add_column("Category", style="bold #f8fafc", width=15)
        p_table.add_column("Fact Key", style="dim #f8fafc", width=25)
        p_table.add_column("Fact Details", style="dim #94a3b8")
        if project_facts:
            for f in project_facts:
                p_table.add_row(f.category, f.key, f.value)
        else:
            p_table.add_row("general", "(No project facts stored)", "Use /remember <fact> to record")
        console.print(p_table)
        console.print()

        # Tier 3: Recent Episodic History
        episodes = memory_mgr.get_recent_episodes(limit=5)
        e_table = Table(title="[bold #f59e0b]Tier 3: Recent Episodic Solutions[/bold #f59e0b]", show_header=True, header_style="bold #f59e0b")
        e_table.add_column("ID", style="bold #f8fafc", width=6)
        e_table.add_column("User Task", style="dim #f8fafc", width=30)
        e_table.add_column("Tools", style="dim #38bdf8", width=20)
        e_table.add_column("Solution Summary", style="dim #94a3b8")
        if episodes:
            for ep in episodes:
                tools_str = ", ".join(ep.tools_used) if ep.tools_used else "none"
                summary = ep.solution_summary[:80] + ("..." if len(ep.solution_summary) > 80 else "")
                e_table.add_row(str(ep.id), ep.user_prompt[:30], tools_str, summary)
        else:
            e_table.add_row("-", "(No episodic history yet)", "-", "Completed tasks are automatically indexed")
        console.print(e_table)
        console.print()

        console.print("[dim #64748b]Manage memory: [/dim #64748b][bold #38bdf8]/remember <fact>[/bold #38bdf8][dim #64748b] or [/dim #64748b][bold #38bdf8]/forget <id|key>[/bold #38bdf8]\n")
        return True
