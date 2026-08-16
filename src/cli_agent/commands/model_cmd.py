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
        console.print("  1. ollama/nemotron-3-ultra [NVIDIA Ultra Deep Logic - Cloud]")
        console.print("  2. ollama/gpt-oss:120b [OpenAI OSS 120B Flagship - Cloud]")
        console.print("  3. ollama/gemma4:31b [Google Gemma 31B Fast - Cloud]")
        console.print("  4. ollama/qwen3.5:4b [Local Ollama - Fast]")
        console.print("  5. gemini/gemini-2.0-flash [Google Gemini Cloud API - Free]")
        console.print("  6. openai/gpt-4o-mini [OpenAI Cloud API]")
        console.print("  7. anthropic/claude-3-5-sonnet [Anthropic Cloud API]")
        console.print("  8. Local llama.cpp GGUF file path (e.g. /path/to/model.gguf)")
        console.print("  9. Custom model string")

        try:
            choice = session.prompt("Enter choice (1-9) > ").strip()
            new_model = ""

            if choice == "1":
                new_model = "ollama/nemotron-3-ultra"
            elif choice == "2":
                new_model = "ollama/gpt-oss:120b"
            elif choice == "3":
                new_model = "ollama/gemma4:31b"
            elif choice == "4":
                new_model = "ollama/qwen3.5:4b"
            elif choice == "5":
                new_model = "gemini/gemini-2.0-flash"
                if not os.getenv("GEMINI_API_KEY"):
                    key = session.prompt("Enter GEMINI_API_KEY > ").strip()
                    if key:
                        os.environ["GEMINI_API_KEY"] = key
                        cfg.config.api_keys["gemini"] = key
                        cfg.save_config(cfg.config)
            elif choice == "6":
                new_model = "openai/gpt-4o-mini"
                if not os.getenv("OPENAI_API_KEY"):
                    key = session.prompt("Enter OPENAI_API_KEY > ").strip()
                    if key:
                        os.environ["OPENAI_API_KEY"] = key
                        cfg.config.api_keys["openai"] = key
                        cfg.save_config(cfg.config)
            elif choice == "7":
                new_model = "anthropic/claude-3-5-sonnet"
                if not os.getenv("ANTHROPIC_API_KEY"):
                    key = session.prompt("Enter ANTHROPIC_API_KEY > ").strip()
                    if key:
                        os.environ["ANTHROPIC_API_KEY"] = key
                        cfg.config.api_keys["anthropic"] = key
                        cfg.save_config(cfg.config)
            elif choice == "8":
                gguf_path = session.prompt("Enter absolute path to your .gguf file > ").strip()
                if os.path.exists(gguf_path):
                    new_model = gguf_path
                else:
                    console.print(f"[bold #ef4444]File not found: {gguf_path}[/bold #ef4444]\n")
                    return True
            elif choice == "9":
                new_model = session.prompt("Enter model string (e.g. ollama/qwen2.5-coder:32b) > ").strip()

            if new_model:
                cfg.set_model(new_model)
                if context.engine:
                    context.engine.set_model(new_model)
                console.print(f"[bold #10b981]✓ Active model updated to: {new_model}[/bold #10b981]\n")
        except (KeyboardInterrupt, EOFError):
            console.print()

        return True
