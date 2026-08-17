from rich.table import Table

from cli_agent.commands.base import CommandContext, ISlashCommand


class SkillsCommand(ISlashCommand):
    """Displays registered skill plugins and tool capabilities."""

    @property
    def name(self) -> str:
        return "/skills"

    @property
    def description(self) -> str:
        return "View active skills and capabilities palette"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        skills = context.skill_registry.list_skills()
        table = Table(
            title="[bold #a855f7]⚡ Registered System Skills[/bold #a855f7]",
            show_header=True,
            header_style="bold #38bdf8"
        )
        table.add_column("Skill Name", style="bold #f8fafc")
        table.add_column("Description", style="dim #94a3b8")
        table.add_column("Version", style="dim #64748b")

        for s in skills:
            table.add_row(s.name, s.description, s.version)

        context.console.print(table)
        context.console.print()
        return True
