import sys
import os
import argparse
from dotenv import load_dotenv

# Ensure src directory is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from cli_agent.ui.native_app import run_native_app

def load_environment():
    """Loads environment configuration from ~/.cli-agent/.env and local .env."""
    config_dir = os.path.expanduser("~/.cli-agent")
    global_env_path = os.path.join(config_dir, ".env")
    
    if os.path.exists(global_env_path):
        load_dotenv(global_env_path)
    load_dotenv()

def run_cli():
    """Main CLI Application Entry Point."""
    load_environment()

    parser = argparse.ArgumentParser(description="AI Command Line Agent Interface")
    parser.parse_known_args()

    # Launch next-generation native terminal interface
    run_native_app()

if __name__ == "__main__":
    run_cli()
