from textual.widgets import Static
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

class UserMessage(Static):
    """OpenCode-inspired Developer Prompt Line."""
    def __init__(self, message: str):
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='replace')
        text = Text()
        text.append("❯ ", style="bold #38bdf8")
        text.append(message, style="bold #f0f6fc")
        super().__init__(text, classes="agent-user")


class RouterCard(Static):
    """Developer-centric Intent & Skill Routing Card."""
    def __init__(self, routing_output: str):
        if isinstance(routing_output, bytes):
            routing_output = routing_output.decode('utf-8', errors='replace')
        routing_str = str(routing_output) if routing_output else "Direct routing completed."
        text = Text()
        text.append("  ⚡ Intent Routing: ", style="bold #a855f7")
        text.append(routing_str, style="dim #8b949e")
        super().__init__(text, classes="agent-router")


class ExecutionCard(Static):
    """Developer-centric Inline Terminal Code Block."""
    def __init__(self, execution_output: str):
        if isinstance(execution_output, bytes):
            execution_output = execution_output.decode('utf-8', errors='replace')
        execution_str = str(execution_output) if execution_output else "Task executed successfully."
        
        # Format as terminal code block if output contains multiple lines
        panel = Panel(
            Markdown(execution_str),
            title="[bold #7ee787]┌─ Output ────────────────────────┐[/bold #7ee787]",
            title_align="left",
            border_style="#30363d"
        )
        super().__init__(panel, classes="agent-execution")
