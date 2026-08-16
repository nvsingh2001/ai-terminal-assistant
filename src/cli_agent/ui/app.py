import sys
import os
import re
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, LoadingIndicator, Collapsible, Log, Label
from textual.binding import Binding
from textual import work
from textual.worker import Worker, WorkerState

from cli_agent.core.engine import DirectAgentEngine
from cli_agent.core.config_manager import config_manager
from cli_agent.services import (
    try_fast_path_execution, session_memory,
    get_system_info, get_env_context_string, history_manager
)
from cli_agent.skills import skill_registry
from cli_agent.ui.stream import StreamRedirector
from cli_agent.ui.styles import APP_CSS
from cli_agent.ui.components import UserMessage, RouterCard, ExecutionCard, SkillPaletteWidget


class CLIAgentApp(App):
    """OpenCode-Inspired Minimalist Full-Screen TUI for the AI CLI Agent."""

    TITLE = "AI CLI Agent"
    SUB_TITLE = "Skill-Based AI CLI Assistant"
    CSS = APP_CSS

    BINDINGS = [
        Binding("ctrl+s", "toggle_skills", "Skills Palette", show=True),
        Binding("ctrl+m", "switch_model", "Model Switcher", show=True),
        Binding("ctrl+k", "clear_memory", "Clear Memory", show=True),
        Binding("ctrl+d", "toggle_debug", "Debug Logs", show=True),
        Binding("ctrl+q", "quit", "Exit", show=True),
    ]

    def __init__(self):
        super().__init__()
        os.environ["CREWAI_TRACING_ENABLED"] = "false"
        os.environ["OTEL_SDK_DISABLED"] = "true"
        os.environ["LITELLM_LOG"] = "ERROR"
        
        self.model_name = config_manager.config.model_name
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        self.sys_info = get_system_info()
        self.history_index = -1

    def compose(self) -> ComposeResult:
        active_skills_count = len(skill_registry.list_skills())
        os_short = self.sys_info['os'].split()[0] if self.sys_info.get('os') else "Linux"
        header_str = f"[bold #7ee787]●[/bold #7ee787] [bold #f0f6fc]AI COMMAND LINE AGENT[/bold #f0f6fc]  │  [dim #8b949e]{self.model_name}[/dim #8b949e]  │  [dim #8b949e]Branch: {self.sys_info['git_branch']}[/dim #8b949e]  │  [dim #8b949e]Skills: {active_skills_count}[/dim #8b949e]"
        yield Label(header_str, id="header-info")
        
        with ScrollableContainer(id="chat-container"):
            yield Static(f"[dim #38bdf8]● AI COMMAND LINE AGENT READY.[/dim #38bdf8]\n[dim #8b949e]Type instructions in plain English or press Ctrl+S for Skills Palette, Ctrl+M for Model Switcher.[/dim #8b949e]")
            
        yield SkillPaletteWidget()

        with Container(id="spinner-container"):
            yield LoadingIndicator()

        with Collapsible(title="Debug Logs (Ctrl+D)", collapsed=True, id="debug-drawer"):
            yield Log(id="debug-log")

        with Container(id="input-container"):
            yield Input(placeholder="❯ Enter prompt or command here... (Ctrl+S for skills)", id="cmd-input")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize background dependencies and redirect streams."""
        log_widget = self.query_one("#debug-log", Log)
        sys.stdout = StreamRedirector(log_widget, self.orig_stdout)
        sys.stderr = StreamRedirector(log_widget, self.orig_stderr)

        try:
            self.agent_engine = DirectAgentEngine()
            log_widget.write_line(f"[SYSTEM] Skill-based Direct Agent Engine Initialized. Env: {get_env_context_string()}")
        except Exception as e:
            log_widget.write_line(f"[ERROR] Failed to initialize Agent system: {str(e)}")

    def on_unmount(self) -> None:
        """Restore stdout and stderr on exit."""
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr

    def action_toggle_skills(self) -> None:
        """Toggle the Skill Palette Popup Modal."""
        palette = self.query_one("#skill-palette", SkillPaletteWidget)
        palette.styles.display = "none" if palette.styles.display == "block" else "block"

    def action_switch_model(self) -> None:
        """Launches the interactive Model & Provider Selector modal screen."""
        from cli_agent.ui.components import ModelSelectorModal
        def handle_model_selected(new_model: str) -> None:
            if new_model:
                self.model_name = new_model
                header_info = self.query_one("#header-info", Label)
                active_skills_count = len(skill_registry.list_skills())
                header_info.update(f"[bold #7ee787]●[/bold #7ee787] [bold #f0f6fc]CLI AGENT[/bold #f0f6fc]  │  [dim #8b949e]{new_model}[/dim #8b949e]  │  [dim #8b949e]Branch: {self.sys_info['git_branch']}[/dim #8b949e]  │  [dim #8b949e]Skills: {active_skills_count}[/dim #8b949e]")
        self.push_screen(ModelSelectorModal(), handle_model_selected)

    def action_clear_memory(self) -> None:
        """Clears session memory buffer."""
        session_memory.clear()
        chat_container = self.query_one("#chat-container", ScrollableContainer)
        chat_container.mount(RouterCard("**[Memory System]** Session memory buffer cleared."))

    def action_toggle_debug(self) -> None:
        """Toggle the collapsible debug log drawer."""
        drawer = self.query_one("#debug-drawer", Collapsible)
        drawer.collapsed = not drawer.collapsed

    def on_key(self, event) -> None:
        """Handle Up/Down arrow key navigation for command history."""
        input_widget = self.query_one("#cmd-input", Input)
        if not input_widget.has_focus:
            return

        entries = history_manager.get_entries()
        if not entries:
            return

        if event.key == "up":
            if self.history_index == -1:
                self.history_index = len(entries) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            input_widget.value = entries[self.history_index]
            input_widget.cursor_position = len(input_widget.value)
        elif event.key == "down":
            if self.history_index != -1:
                if self.history_index < len(entries) - 1:
                    self.history_index += 1
                    input_widget.value = entries[self.history_index]
                else:
                    self.history_index = -1
                    input_widget.value = ""
                input_widget.cursor_position = len(input_widget.value)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission from the Input widget."""
        user_text = event.value.strip()
        if not user_text:
            return

        history_manager.add(user_text)
        self.history_index = -1

        input_widget = self.query_one("#cmd-input", Input)
        input_widget.value = ""

        if user_text.lower() in ["exit", "quit", "q"]:
            self.exit()
            return

        chat_container = self.query_one("#chat-container", ScrollableContainer)
        header_info = self.query_one("#header-info", Label)
        spinner = self.query_one("#spinner-container", Container)

        await chat_container.mount(UserMessage(user_text))
        chat_container.scroll_end(animate=False)

        active_skills_count = len(skill_registry.list_skills())
        header_info.update(f"[bold #d29922]●[/bold #d29922] [bold #f0f6fc]CLI AGENT[/bold #f0f6fc]  │  [dim #8b949e]{self.model_name}[/dim #8b949e]  │  [bold #d29922]Processing...[/bold #d29922]")
        spinner.styles.display = "block"

        self.process_agent_task(user_text)

    @work(thread=True)
    def process_agent_task(self, user_request: str) -> dict:
        """Executes the task in a background worker thread with managed session memory."""
        req_clean = user_request.strip()
        if req_clean.lower() in ["clear", "/clear", "reset"]:
            session_memory.clear()
            return {"routing": "**[Memory System]** Session memory cleared.", "execution": "Conversation context has been reset."}

        try:
            fast_res = try_fast_path_execution(req_clean)
            if fast_res:
                session_memory.add_turn(req_clean, "Fast-Path", fast_res[1])
                return {"routing": fast_res[0], "execution": fast_res[1]}

            engine = DirectAgentEngine()
            return engine.run_task(req_clean)
        except Exception as e:
            err_msg = str(e)
            if "execution timed out" in err_msg:
                err_msg = "Task execution timed out while waiting for model generation. Consider breaking down your prompt."
            elif "Task '" in err_msg:
                err_msg = re.sub(r"Task '.*?' ", "", err_msg)
            return {"routing": "Routing error encountered.", "execution": f"Error executing task: {err_msg}"}

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Callback when the background worker thread completes."""
        if event.state == WorkerState.SUCCESS:
            data = event.worker.result
            chat_container = self.query_one("#chat-container", ScrollableContainer)
            header_info = self.query_one("#header-info", Label)
            spinner = self.query_one("#spinner-container", Container)

            active_skills_count = len(skill_registry.list_skills())
            spinner.styles.display = "none"
            header_info.update(f"[bold #7ee787]●[/bold #7ee787] [bold #f0f6fc]CLI AGENT[/bold #f0f6fc]  │  [dim #8b949e]{self.model_name}[/dim #8b949e]  │  [dim #8b949e]Branch: {self.sys_info['git_branch']}[/dim #8b949e]  │  [dim #8b949e]Skills: {active_skills_count}[/dim #8b949e]")

            if data.get("routing"):
                chat_container.mount(RouterCard(data["routing"]))
            if data.get("execution"):
                chat_container.mount(ExecutionCard(data["execution"]))

            chat_container.scroll_end(animate=True)


def run_tui():
    """Launches the Box-Free Native Terminal Engine."""
    from cli_agent.ui.native_app import run_native_app
    run_native_app()
