from rich.console import Console

AEGIS_ANSI_LOGO = """
[bold #38bdf8]   █████╗ ███████╗ ██████╗ ██╗███████╗[/bold #38bdf8]
[bold #60a5fa]  ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝[/bold #60a5fa]
[bold #818cf8]  ███████║█████╗  ██║  ███╗██║███████╗[/bold #818cf8]
[bold #a855f7]  ██╔══██║██╔══╝  ██║   ██║██║╚════██║[/bold #a855f7]
[bold #c084fc]  ██║  ██║███████╗╚██████╔╝██║███████║[/bold #c084fc]
[dim #64748b]  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝[/dim #64748b]"""

def print_aegis_banner(
    console: Console,
    model_name: str,
    git_branch: str,
    skills_count: int,
    verbose_enabled: bool,
    project_id: str
):
    """Renders the aesthetic Aegis ANSI art logo and structured status dashboard."""
    trace_badge = "[bold #10b981]ON[/bold #10b981]" if verbose_enabled else "[dim #64748b]OFF[/dim #64748b]"
    
    console.print(AEGIS_ANSI_LOGO)
    console.print(f"  [dim #94a3b8]Autonomous AI Terminal Agent[/dim #94a3b8] [dim #64748b]v2.0[/dim #64748b]  │  [bold #10b981]● System Ready[/bold #10b981]\n")
    
    console.print(f"  [bold #38bdf8]Model:[/bold #38bdf8]    [bold #f8fafc]{model_name}[/bold #f8fafc]")
    console.print(f"  [bold #a855f7]Runtime:[/bold #a855f7]  Branch: [dim #f8fafc]{git_branch}[/dim #f8fafc]  │  Skills: [bold #a855f7]{skills_count} active[/bold #a855f7]  │  Trace: {trace_badge}")
    console.print(f"  [bold #10b981]Memory:[/bold #10b981]   Tri-Tier SQLite WAL  │  Project: [dim #f8fafc]{project_id}[/dim #f8fafc]\n")

    console.print("  [dim #64748b]Quick Commands:[/dim #64748b]")
    console.print("    [bold #38bdf8]/model[/bold #38bdf8]    [dim #94a3b8]Switch LLM model[/dim #94a3b8]       [bold #38bdf8]/memory[/bold #38bdf8]   [dim #94a3b8]Inspect persistent knowledge[/dim #94a3b8]")
    console.print("    [bold #38bdf8]/verbose[/bold #38bdf8]  [dim #94a3b8]Toggle live trace[/dim #94a3b8]      [bold #38bdf8]/help[/bold #38bdf8]     [dim #94a3b8]Show full command palette[/dim #94a3b8]\n")
