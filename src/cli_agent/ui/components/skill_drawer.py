from textual.widgets import Static
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from cli_agent.skills import skill_registry

class SkillPaletteWidget(Static):
    """Interactive Skill Palette Popup Widget listing all registered skills."""
    def __init__(self):
        super().__init__(id="skill-palette")
        self.refresh_skills()

    def refresh_skills(self):
        manifests = skill_registry.list_skills()
        table = Table(title="[bold magenta]⚡ Active Skill Registry[/bold magenta]", show_header=True, header_style="bold cyan")
        table.add_column("Skill Name", style="bold yellow")
        table.add_column("Approval Gate", style="bold red")
        table.add_column("Description", style="dim white")

        for m in manifests:
            approval_str = "Required" if m.requires_approval else "Auto"
            table.add_column if False else None
            table.add_row(m.name, approval_str, m.description)

        panel = Panel(table, border_style="purple", title="[bold white]Skill Registry Palette (Press Ctrl+S to toggle)[/bold white]")
        self.update(panel)
