from textual.widgets import Static
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

class UserMessage(Static):
    """Sleek Pill Widget for displaying User Prompts."""
    def __init__(self, message: str):
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='replace')
        panel = Panel(
            Text(f"User > {message}", style="bold #38bdf8"),
            border_style="#38bdf8",
            title="[bold #f8fafc]User Prompt[/bold #f8fafc]",
            title_align="left"
        )
        super().__init__(panel)


class RouterCard(Static):
    """Widget for displaying Router & Skill Intent Decision."""
    def __init__(self, routing_output: str):
        if isinstance(routing_output, bytes):
            routing_output = routing_output.decode('utf-8', errors='replace')
        routing_str = str(routing_output) if routing_output else "Direct routing completed."
        panel = Panel(
            Markdown(routing_str),
            title="[bold #a855f7]⚡ Intent & Skill Selection Path[/bold #a855f7]",
            title_align="left",
            border_style="#a855f7"
        )
        super().__init__(panel)


class ExecutionCard(Static):
    """Widget for displaying Skill Execution Output."""
    def __init__(self, execution_output: str):
        if isinstance(execution_output, bytes):
            execution_output = execution_output.decode('utf-8', errors='replace')
        execution_str = str(execution_output) if execution_output else "Task executed successfully."
        panel = Panel(
            Markdown(execution_str),
            title="[bold #10b981]🎯 Skill Execution Output[/bold #10b981]",
            title_align="left",
            border_style="#10b981"
        )
        super().__init__(panel)
