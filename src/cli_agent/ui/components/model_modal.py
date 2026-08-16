from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, Input, Select
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from cli_agent.core.config_manager import config_manager

PRESET_MODELS = [
    ("Ollama: Gemma 4 31B (Cloud)", "ollama/gemma4:31b-cloud"),
    ("Ollama: Qwen 2.5 Coder 14B", "ollama/qwen2.5-coder:14b"),
    ("Ollama: Llama 3.1 8B", "ollama/llama3.1:8b"),
    ("Cloud: OpenAI GPT-4o", "openai/gpt-4o"),
    ("Cloud: Anthropic Claude 3.5 Sonnet", "anthropic/claude-3-5-sonnet"),
    ("Cloud: Google Gemini 1.5 Pro", "gemini/gemini-1.5-pro"),
    ("Local GGUF: Custom Path", "llama-cpp/custom.gguf")
]

class ModelSelectorModal(ModalScreen[str]):
    """
    Floating TUI Modal Dialog for Interactive Model Selection & Configuration.
    """
    def compose():
        pass

    def __init__(self):
        super().__init__()
        self.current_model = config_manager.config.model_name

    def compose(self):
        with Container(id="modal-dialog"):
            yield Label(f"[bold cyan]⚙️ Interactive Model & Provider Selector[/bold cyan]", id="modal-title")
            with Vertical():
                yield Label("Select Preset Model Engine:", classes="field-label")
                yield Select(
                    options=[(label, val) for label, val in PRESET_MODELS],
                    value=self.current_model if any(v == self.current_model for _, v in PRESET_MODELS) else "ollama/gemma4:31b-cloud",
                    id="model-select"
                )
                yield Label("Or Enter Custom Model Identifier:", classes="field-label")
                yield Input(value=self.current_model, placeholder="e.g. openai/gpt-4o or ollama/mistral", id="custom-model-input")
            
            with Horizontal(id="modal-buttons"):
                yield Button("Save & Apply", variant="success", id="btn-save")
                yield Button("Cancel", variant="error", id="btn-cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK:
            input_widget = self.query_one("#custom-model-input", Input)
            input_widget.value = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            custom_val = self.query_one("#custom-model-input", Input).value.strip()
            selected_model = custom_val or self.current_model
            config_manager.set_model(selected_model)
            self.dismiss(selected_model)
        else:
            self.dismiss(self.current_model)
