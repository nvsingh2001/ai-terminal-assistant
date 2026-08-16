from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table

console = Console()

class CLIFormatter:
    @staticmethod
    def print_welcome():
        """Prints a premium welcome banner for the CLI Agent."""
        console.print()
        console.print(Panel(
            "[bold cyan]=== AI COMMAND LINE AGENT ===[/bold cyan]\n"
            "[dim]Powered by CrewAI - Built for Seamless Shell, File, Code, & Git Automation[/dim]",
            border_style="cyan",
            expand=False
        ))
        console.print("[dim]Type your command in plain English (or 'exit' to quit).[/dim]")
        console.print()

    @staticmethod
    def print_routing(routing_output: str):
        """Displays the router agent's intent analysis and execution plan."""
        console.print(Rule("[bold magenta]>> Router Agent: Intent & Pathing Decision[/bold magenta]", style="magenta"))
        console.print(Panel(
            routing_output,
            title="[bold]Routing Decision[/bold]",
            title_align="left",
            border_style="magenta"
        ))
        console.print()

    @staticmethod
    def print_execution(execution_output: str):
        """Displays the executor agent's final execution results."""
        console.print(Rule("[bold green]>> Executor Agent: Tool Execution Output[/bold green]", style="green"))
        console.print(Panel(
            Markdown(execution_output) if execution_output else "No execution output returned.",
            title="[bold]Execution Output[/bold]",
            title_align="left",
            border_style="green"
        ))
        console.print()

    @staticmethod
    def print_error(error_msg: str):
        """Displays errors in a clean red panel."""
        console.print(Panel(
            f"[bold red]Error:[/bold red] {error_msg}",
            border_style="red",
            title="[bold red]System Failure[/bold red]"
        ))

    @staticmethod
    def print_info(info_msg: str):
        """Displays informational logs."""
        console.print(f"[bold blue][i][/bold blue] [dim]{info_msg}[/dim]")
        
    @staticmethod
    def print_result_summary(result):
        """Prints a comprehensive summary of the CrewAI run."""
        console.print(Rule("[bold cyan]*** Run Completed ***[/bold cyan]", style="cyan"))
        
        # Display tasks output if available
        if hasattr(result, 'tasks_output') and result.tasks_output:
            table = Table(title="Task Run Summary", show_header=True, header_style="bold cyan")
            table.add_column("Task Description Summary", style="dim")
            table.add_column("Status", justify="center")
            
            for task_out in result.tasks_output:
                desc = task_out.description[:60] + "..." if len(task_out.description) > 60 else task_out.description
                table.add_row(desc, "[bold green]Success[/bold green]")
            console.print(table)
        
        console.print()
