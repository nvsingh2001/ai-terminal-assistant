import os
import sys
import subprocess
import shutil

def build():
    print("=== BUILDING CLI-AGENT STANDALONE BINARY ===")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    entrypoint = os.path.join(root_dir, "run.py")
    config_dir = os.path.join(root_dir, "src", "cli_agent", "config")
    
    # Path separator for PyInstaller --add-data (';' on Windows, ':' on Unix)
    sep = ";" if sys.platform == "win32" else ":"
    data_arg = f"{config_dir}{sep}cli_agent/config"
    
    binary_name = "cli-agent"
    
    src_dir = os.path.join(root_dir, "src")
    
    # Use project virtual environment python if available to avoid packing heavy global ML packages (torch, scipy, pandas)
    venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(root_dir, "venv", "bin", "python")
    py_exec = venv_python if os.path.exists(venv_python) else sys.executable
    
    excludes = [
        "torch", "tensorflow", "scipy", "pandas", "faiss", "faiss_cpu", 
        "onnxruntime", "pyarrow", "matplotlib", "tkinter", "lxml", 
        "PIL", "Pillow", "pdfminer", "pypdfium2", "docx"
    ]
    exclude_args = []
    for exc in excludes:
        exclude_args.extend(["--exclude-module", exc])
    
    cmd = [
        py_exec, "-m", "PyInstaller",
        "--onefile",
        "--name", binary_name,
        "--paths", src_dir,
        "--add-data", data_arg,
        "--collect-all", "litellm",
        "--collect-all", "textual",
        "--collect-all", "tiktoken",
        "--collect-all", "tiktoken_ext",
        "--collect-all", "prompt_toolkit",
        "--collect-all", "rich",
        *exclude_args,
        entrypoint
    ]
    
    print(f"Running build command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root_dir)
    
    if result.returncode == 0:
        print("\n=== BUILD SUCCESSFUL ===")
        dist_dir = os.path.join(root_dir, "dist")
        ext = ".exe" if sys.platform == "win32" else ""
        out_file = os.path.join(dist_dir, f"{binary_name}{ext}")
        print(f"Standalone executable created at: {out_file}")
    else:
        print("\n=== BUILD FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    build()
