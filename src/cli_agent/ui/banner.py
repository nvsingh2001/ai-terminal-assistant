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
    """Renders the aesthetic Aegis ANSI art logo and status bar."""
    trace_status = "[bold #10b981]ON[/bold #10b981]" if verbose_enabled else "[dim #64748b]OFF[/dim #64748b]"
    
    console.print(AEGIS_ANSI_LOGO)
    console.print(f"  [dim #94a3b8]Autonomous Terminal Agent v2.0[/dim #94a3b8]  │  [bold #10b981]● System Ready[/bold #10b981]")
    console.print(f"  [dim #64748b]Model:[/dim #64748b] [bold #38bdf8]{model_name}[/bold #38bdf8]  │  [dim #64748b]Branch:[/dim #64748b] [dim #f8fafc]{git_branch}[/dim #f8fafc]  │  [dim #64748b]Skills:[/dim #64748b] [bold #a855f7]{skills_count} loaded[/bold #a855f7]  │  [dim #64748b]Trace:[/dim #64748b] {trace_status}")
    console.print(f"  [dim #64748b]Type instructions or [/dim #64748b][bold #38bdf8]/help[/bold #38bdf8][dim #64748b], [/dim #64748b][bold #38bdf8]/memory[/bold #38bdf8][dim #64748b] for facts, [/dim #64748b][bold #38bdf8]/verbose[/bold #38bdf8][dim #64748b] to toggle trace, [/dim #64748b][bold #38bdf8]/model[/bold #38bdf8][dim #64748b] to switch models.[/dim #64748b]")
    console.print()
