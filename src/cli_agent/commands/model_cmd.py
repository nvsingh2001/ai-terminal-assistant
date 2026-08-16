import os
from cli_agent.commands.base import ISlashCommand, CommandContext

class ModelCommand(ISlashCommand):
    """Handles LLM Model & Provider interactive switching."""

    @property
    def name(self) -> str:
        return "/model"

    @property
    def description(self) -> str:
        return "Switch active LLM model or cloud provider"

    def execute(self, context: CommandContext, raw_args: str = "") -> bool:
        console = context.console
        session = context.prompt_session
        cfg = context.config_manager

        console.print("[bold #38bdf8]Select LLM Provider / Model:[/bold #38bdf8]")
        console.print("  1. ollama/qwen3.5:4b [Local Ollama - Fast]")
        console.print("  2. ollama/gemma4:31b-cloud [Ollama Cloud]")
        console.print("  3. gemini/gemini-1.5-flash [Google Gemini Cloud API]")
        console.print("  4. openai/gpt-4o-mini [OpenAI Cloud API]")
        console.print("  5. anthropic/claude-3-5-sonnet [Anthropic Cloud API]")
        console.print("  6. Local llama.cpp GGUF file path (e.g. /path/to/model.gguf)")
        console.print("  7. Custom model string")

        try:
            choice = session.prompt("Enter choice (1-7) > ").strip()
            new_model = ""

            if choice == "1":
                new_model = "ollama/qwen3.5:4b"
            elif choice == "2":
                new_model = "ollama/gemma4:31b-cloud"
            elif choice == "3":
                new_model = "gemini/gemini-1.5-flash"
                if not os.getenv("GEMINI_API_KEY"):
                    key = session.prompt("Enter GEMINI_API_KEY > ").strip()
                    if key:
                        os.environ["GEMINI_API_KEY"] = key
                        cfg.config.api_keys["gemini"] = key
                        cfg.save_config(cfg.config)
            elif choice == "4":
                new_model = "openai/gpt-4o-mini"
                if not os.getenv("OPENAI_API_KEY"):
                    key = session.prompt("Enter OPENAI_API_KEY > ").strip()
                    if key:
                        os.environ["OPENAI_API_KEY"] = key
                        cfg.config.api_keys["openai"] = key
                        cfg.save_config(cfg.config)
            elif choice == "5":
                new_model = "anthropic/claude-3-5-sonnet"
                if not os.getenv("ANTHROPIC_API_KEY"):
                    key = session.prompt("Enter ANTHROPIC_API_KEY > ").strip()
                    if key:
                        os.environ["ANTHROPIC_API_KEY"] = key
                        cfg.config.api_keys["anthropic"] = key
                        cfg.save_config(cfg.config)
            elif choice == "6":
                gguf_path = session.prompt("Enter absolute path to your .gguf file > ").strip()
                if os.path.exists(gguf_path):
                    new_model = gguf_path
                else:
                    console.print(f"[bold #ef4444]File not found: {gguf_path}[/bold #ef4444]\n")
                    return True
            elif choice == "7":
                new_model = session.prompt("Enter model string (e.g. ollama/llama3.2) > ").strip()

            if new_model:
                cfg.set_model(new_model)
                if context.engine:
                    context.engine.set_model(new_model)
                console.print(f"[bold #10b981]✓ Active model updated to: {new_model}[/bold #10b981]\n")
        except (KeyboardInterrupt, EOFError):
            console.print()

        return True
