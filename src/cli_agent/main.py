import sys
import os
import argparse
from dotenv import load_dotenv

# Add src folder to sys.path to allow absolute imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from cli_agent.core.engine import DirectAgentEngine
from cli_agent.utils import CLIFormatter
from cli_agent.ui import run_tui
from cli_agent.services import try_fast_path_execution, session_memory, get_env_context_string, history_manager

def ensure_api_key() -> bool:
    config_dir = os.path.expanduser("~/.cli-agent")
    global_env_path = os.path.join(config_dir, ".env")
    
    if os.path.exists(global_env_path):
        load_dotenv(global_env_path)
    load_dotenv()

    if os.getenv("OLLAMA_API_KEY"):
        return True

    CLIFormatter.print_welcome()
    CLIFormatter.print_info("First-Time Setup: OLLAMA_API_KEY was not found.")
    print("Please provide your Ollama credentials (saved to ~/.cli-agent/.env for future runs):\n")
    
    try:
        api_key = input("Enter your OLLAMA API Key: ").strip()
        if not api_key:
            CLIFormatter.print_error("OLLAMA_API_KEY is required to run the CLI agent.")
            return False
            
        model_name = input("Enter OLLAMA Model Name [default: gemma4:31b-cloud]: ").strip() or "gemma4:31b-cloud"
        api_base = input("Enter OLLAMA API Base URL [default: https://ollama.com/v1]: ").strip() or "https://ollama.com/v1"

        os.makedirs(config_dir, exist_ok=True)
        with open(global_env_path, "w", encoding="utf-8") as f:
            f.write(f"OLLAMA_API_KEY={api_key}\n")
            f.write(f"OLLAMA_MODEL_NAME={model_name}\n")
            f.write(f"OLLAMA_API_BASE={api_base}\n")

        os.environ["OLLAMA_API_KEY"] = api_key
        os.environ["OLLAMA_MODEL_NAME"] = model_name
        os.environ["OLLAMA_API_BASE"] = api_base

        CLIFormatter.print_info(f"Configuration saved to {global_env_path}!\n")
        return True
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        return False

def run_cli():
    # Ensure API Key is configured interactively if missing
    if not ensure_api_key():
        return

    parser = argparse.ArgumentParser(description="AI Command Line Agent Interface")
    parser.add_argument("--classic", action="store_true", help="Launch classic console input loop instead of TUI")
    args, unknown = parser.parse_known_args()

    if not args.classic:
        # Launch modern full-screen TUI
        run_tui()
        return

    # Print welcome screen for classic mode
    CLIFormatter.print_welcome()
    
    # CLI Loop
    while True:
        try:
            # Get user input
            user_request = input("\nUser command > ").strip()
            
            if not user_request:
                continue
                
            if user_request.lower() in ["exit", "quit", "q"]:
                CLIFormatter.print_info("Exiting CLI Agent. Goodbye!")
                break
                
            history_manager.add(user_request)

            if user_request.lower() in ["clear", "/clear", "reset"]:
                session_memory.clear()
                CLIFormatter.print_info("Session memory cleared. Conversation context reset.")
                continue

            fast_res = try_fast_path_execution(user_request)
            if fast_res:
                session_memory.add_turn(user_request, "Fast-Path", fast_res[1])
                CLIFormatter.print_routing(fast_res[0])
                CLIFormatter.print_execution(fast_res[1])
                continue

            CLIFormatter.print_info(f"Analyzing and processing task: '{user_request}'...")
            
            engine = DirectAgentEngine()
            task_res = engine.run_task(user_request)
            
            CLIFormatter.print_routing(task_res["routing"])
            CLIFormatter.print_execution(task_res["execution"])
            
        except KeyboardInterrupt:
            console_msg = "\nExiting CLI Agent. Goodbye!"
            print(console_msg)
            break
        except Exception as e:
            CLIFormatter.print_error(f"An unexpected error occurred during execution: {str(e)}")

if __name__ == "__main__":
    run_cli()

