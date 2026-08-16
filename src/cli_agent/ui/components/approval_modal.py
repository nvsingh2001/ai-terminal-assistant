from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label
from textual.containers import Container, Horizontal
from rich.panel import Panel
from rich.text import Text

class ActionApprovalModal(ModalScreen[bool]):
    """
    Floating TUI Modal Dialog for Interactive Action Approval.
    Prompts user for confirmation before executing mutating skills.
    """
    def __init__(self, skill_name: str, action_details: str):
        super().__init__()
        self.skill_name = skill_name
        self.action_details = action_details

    def compose(self):
        with Container(id="modal-dialog"):
            yield Label(f"[bold yellow]⚠️ Action Approval Required[/bold yellow]", id="modal-title")
            yield Static(
                Panel(
                    Text(f"Skill Target: {self.skill_name}\nDetails: {self.action_details}", style="bold white"),
                    title="[bold red]Security Gate[/bold red]",
                    border_style="red"
                )
            )
            with Horizontal(id="modal-buttons"):
                yield Button("Allow Once", variant="success", id="btn-allow")
                yield Button("Deny Action", variant="error", id="btn-deny")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-allow":
            self.dismiss(True)
        else:
            self.dismiss(False)
