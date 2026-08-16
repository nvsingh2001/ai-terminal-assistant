import sys
import os

# Add src directory to path for standard and PyInstaller frozen execution
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(bundle_dir, "src"))
    sys.path.insert(0, bundle_dir)
else:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from cli_agent.main import run_cli

if __name__ == "__main__":
    run_cli()
