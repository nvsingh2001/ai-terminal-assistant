import os
import shutil
import subprocess
import sys


def build():
    print("=== BUILDING CLI-AGENT STANDALONE BINARY ===")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    entrypoint = os.path.join(root_dir, "run.py")
    config_dir = os.path.join(root_dir, "src", "cli_agent", "config")

    # Path separator for PyInstaller --add-data (';' on Windows, ':' on Unix)
    sep = ";" if sys.platform == "win32" else ":"
    data_arg = f"{config_dir}{sep}cli_agent/config"

    binary_name = "aegis"

    src_dir = os.path.join(root_dir, "src")

    # Use project virtual environment python if available to avoid packing heavy global ML packages (torch, scipy, pandas)
    venv_python = (
        os.path.join(root_dir, "venv", "Scripts", "python.exe")
        if sys.platform == "win32"
        else os.path.join(root_dir, "venv", "bin", "python")
    )
    py_exec = venv_python if os.path.exists(venv_python) else sys.executable

    excludes = [
        "torch",
        "tensorflow",
        "scipy",
        "pandas",
        "faiss",
        "faiss_cpu",
        "onnxruntime",
        "pyarrow",
        "matplotlib",
        "tkinter",
        "lxml",
        "PIL",
        "Pillow",
        "pdfminer",
        "pypdfium2",
        "docx",
    ]
    exclude_args = []
    for exc in excludes:
        exclude_args.extend(["--exclude-module", exc])

    cmd = [
        py_exec,
        "-m",
        "PyInstaller",
        "--onefile",
        "--log-level",
        "WARN",
        "--name",
        binary_name,
        "--paths",
        src_dir,
        "--add-data",
        data_arg,
        "--collect-all",
        "litellm",
        "--collect-all",
        "textual",
        "--collect-all",
        "tiktoken",
        "--collect-all",
        "tiktoken_ext",
        "--collect-all",
        "prompt_toolkit",
        "--collect-all",
        "rich",
        "--collect-all",
        "langgraph",
        "--collect-all",
        "langgraph_checkpoint",
        "--collect-all",
        "langgraph_sdk",
        "--collect-all",
        "langchain_core",
        "--collect-all",
        "langchain_openai",
        "--collect-all",
        "langchain_google_genai",
        "--collect-all",
        "langchain_anthropic",
        "--collect-all",
        "nest_asyncio",
        "--collect-all",
        "pydantic_ai",
        "--collect-all",
        "pydantic_ai_slim",
        "--collect-all",
        "pydantic_core",
        "--collect-all",
        "pydantic",
        "--collect-all",
        "genai_prices",
        "--copy-metadata",
        "genai_prices",
        "--copy-metadata",
        "pydantic_ai",
        "--copy-metadata",
        "pydantic_ai_slim",
        "--copy-metadata",
        "langgraph",
        *exclude_args,
        entrypoint,
    ]

    print(f"Running build command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root_dir)

    if result.returncode == 0:
        print("\n=== BUILD SUCCESSFUL ===")
        dist_dir = os.path.join(root_dir, "dist")
        ext = ".exe" if sys.platform == "win32" else ""
        out_file = os.path.join(dist_dir, f"{binary_name}{ext}")
        print(f"Standalone executable created at: {out_file}")

        # Atomically install to ~/.local/bin if directory exists
        local_bin = os.path.expanduser("~/.local/bin")
        if os.path.exists(local_bin) and sys.platform != "win32":
            target_bin = os.path.join(local_bin, binary_name)
            subprocess.run(["install", "-m", "755", out_file, target_bin], check=False)
            alias_bin = os.path.join(local_bin, "cli-agent")
            subprocess.run(["ln", "-sf", target_bin, alias_bin], check=False)
            print(f"Installed to {target_bin} and symlinked {alias_bin}")
    else:
        print("\n=== BUILD FAILED ===")
        sys.exit(1)


if __name__ == "__main__":
    build()
