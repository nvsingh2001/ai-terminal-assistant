from rich.console import Console
from rich.markdown import Markdown

console = Console()


class CLIFormatter:
    """Utility formatter for Rich terminal outputs."""

    @staticmethod
    def print_markdown(content: str):
        """Renders GitHub Flavored Markdown cleanly."""
        if content:
            console.print(Markdown(content))

    @staticmethod
    def print_error(error_msg: str):
        """Displays error messages in styled text."""
        console.print(f"[bold #ef4444]Error:[/bold #ef4444] {error_msg}")

    @staticmethod
    def print_info(info_msg: str):
        """Displays informational message."""
        console.print(
            f"[bold #38bdf8]ℹ[/bold #38bdf8] [dim #94a3b8]{info_msg}[/dim #94a3b8]"
        )
