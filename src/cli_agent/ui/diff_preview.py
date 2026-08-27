import difflib
import os
from typing import Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class DiffPreviewRenderer:
    """
    Renders colorized unified diff previews in the terminal and prompts for developer approval.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._session_always_accept = False

    @property
    def always_accept(self) -> bool:
        return self._session_always_accept

    def set_always_accept(self, value: bool = True):
        self._session_always_accept = value

    def generate_diff_lines(self, file_path: str, old_content: str, new_content: str) -> list[str]:
        """Generates unified diff lines between original and modified content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        rel_path = os.path.relpath(file_path, os.getcwd()) if os.path.isabs(file_path) else file_path

        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm="",
            )
        )
        return diff

    def render_diff(self, file_path: str, old_content: str, new_content: str):
        """Displays formatted and colorized unified diff in a Rich Panel."""
        diff_lines = self.generate_diff_lines(file_path, old_content, new_content)
        if not diff_lines:
            return

        formatted_text = Text()
        for line in diff_lines:
            if line.startswith("+++") or line.startswith("---"):
                formatted_text.append(line + "\n", style="bold yellow")
            elif line.startswith("@@"):
                formatted_text.append(line + "\n", style="bold cyan")
            elif line.startswith("+"):
                formatted_text.append(line + "\n", style="bold green")
            elif line.startswith("-"):
                formatted_text.append(line + "\n", style="bold red")
            else:
                formatted_text.append(line + "\n", style="dim #94a3b8")

        rel_path = os.path.relpath(file_path, os.getcwd()) if os.path.isabs(file_path) else file_path
        panel = Panel(
            formatted_text,
            title=f"[bold #38bdf8]Diff Preview: [bold white]{rel_path}[/bold white][/bold #38bdf8]",
            subtitle="[dim #94a3b8]Review proposed changes before applying to disk[/dim #94a3b8]",
            border_style="#38bdf8",
            expand=False,
        )
        self.console.print(panel)

    def request_approval(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        prompt_session: Optional[Any] = None,
        policy: str = "trusted-read",
    ) -> bool:
        """
        Presents diff to user and requests approval based on execution policy.
        Returns True if accepted, False if rejected.
        """
        # If yolo mode or developer chose always-accept in this session
        if policy == "yolo" or self._session_always_accept:
            return True

        # Render visual diff
        self.render_diff(file_path, old_content, new_content)

        # Prompt developer
        rel_path = os.path.relpath(file_path, os.getcwd()) if os.path.isabs(file_path) else file_path
        prompt_text = f"Apply changes to [bold white]{rel_path}[/bold white]? [[bold green]y[/bold green]=yes, [bold red]n[/bold red]=no, [bold cyan]a[/bold cyan]=always accept in session] > "

        try:
            if prompt_session and hasattr(prompt_session, "prompt"):
                self.console.print(prompt_text, end="")
                choice = prompt_session.prompt("").strip().lower()
            else:
                self.console.print(prompt_text, end="")
                choice = input().strip().lower()

            if choice in ("y", "yes", ""):
                return True
            elif choice in ("a", "always"):
                self._session_always_accept = True
                self.console.print("[bold #10b981]✓ Auto-accept enabled for remainder of this session.[/bold #10b981]\n")
                return True
            else:
                self.console.print("[bold #ef4444]✗ Changes rejected by user.[/bold #ef4444]\n")
                return False
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[bold #ef4444]✗ Operation cancelled.[/bold #ef4444]\n")
            return False


# Global singleton instance
diff_renderer = DiffPreviewRenderer()
