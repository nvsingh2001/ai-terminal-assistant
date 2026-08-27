# Aegis (Autonomous AI Terminal Agent)

```text
   █████╗ ███████╗ ██████╗ ██╗███████╗
  ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝
  ███████║█████╗  ██║  ███╗██║███████╗
  ██╔══██║██╔══╝  ██║   ██║██║╚════██║
  ██║  ██║███████╗╚██████╔╝██║███████║
  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝
```

**Aegis** is an autonomous, next-generation AI command-line agent engineered with **PydanticAI**, **Dependency Injection**, **Strategy Pattern**, and a production **Tri-Tier Long-Term Memory Engine** (Global Preferences, Project Knowledge Graph, Episodic Recall).

It translates plain English developer instructions into validated terminal, file, code, and Git operations directly in your terminal.

---

## Key Features

* **PydanticAI Type-Safe Engine**: Robust multi-turn reasoning loops with validated tool calling.
* **Production Tri-Tier Memory**:
  * **Tier 1 (Global Preferences)**: User-wide defaults and tool preferences saved in `~/.cli-agent/memory.db`.
  * **Tier 2 (Project Knowledge Graph)**: Project-scoped architectural rules, virtualenv paths, and conventions.
  * **Tier 3 (Episodic Recall)**: Automatically indexed past task solutions with relevance recall.
* **Real-Time Execution & Thinking Trace (`/verbose`)**: Inspect the agent's internal reasoning steps and live tool arguments in real time.
* **Universal Model Flexibility (`/model`)**: Seamlessly switch between Local Ollama models (`qwen2.5-coder`, `qwen3.5:4b`), llama.cpp GGUF files, and Cloud APIs (Gemini, Claude, GPT-4o).
* **Autonomous Skill System**:
  * `shell_execution`: Real-time bash shell execution with environment detection.
  * `file_management`: AST-aware token budgeting, reading, writing, and sensitive path guardrails.
  * `code_editing`: AST/pattern searches, surgical edits, and syntax validation.
  * `git_operations`: Status, diff, commit, branch, and log automation.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/nvsingh2001/ai-terminal-assistant.git
cd ai-terminal-assistant

# Create virtual environment & install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run directly
python run.py
```

Or install the standalone binary to your system PATH:
```bash
python build_installer.py
cp dist/aegis ~/.local/bin/aegis
chmod +x ~/.local/bin/aegis
ln -sf ~/.local/bin/aegis ~/.local/bin/cli-agent
```

Then simply launch from any terminal:
```bash
aegis
```

> **macOS troubleshooting**: if Gatekeeper reports the binary as "damaged and can't be opened" or from an unidentified developer, clear the quarantine flag before running it:
> ```bash
> xattr -d com.apple.quarantine /path/to/aegis
> ```

---

## Interactive Slash Commands

| Command | Description |
| :--- | :--- |
| `/model` | Switch active LLM model or cloud provider |
| `/skills` | View active skill palette and tool parameters |
| `/memory` | View active Tri-Tier Long-Term Memory (`/mem`) |
| `/remember <fact>` | Store project knowledge or global preference (`/remember --global`) |
| `/forget <id\|key>` | Delete a memory entry or clear project facts (`/forget --all`) |
| `/verbose` | Toggle real-time thinking and tool execution trace (`/trace`) |
| `/clear` | Reset active conversation memory buffer |
| `/help` | Show interactive commands help menu |
| `/exit` | Exit Aegis terminal session |

---

## Architecture Overview

```text
               ┌──────────────────────────────┐
               │    User Request / Prompt     │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │    NativeCLIAgent (REPL)     │
               └──────────────┬───────────────┘
                              │
               ┌──────────────┴───────────────┐
               │  CommandDispatcher (OCP/Cmd) │
               └──────────────┬───────────────┘
                              │
      ┌───────────────────────┼───────────────────────┐
      ▼                       ▼                       ▼
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ SkillRegistry│    │ TriTierMemoryMgr │    │  PydanticAI Engine│
│ (Tool Layer) │    │ (SQLite WAL DB)  │    │  (LLM Execution)  │
└──────────────┘    └──────────────────┘    └───────────────────┘
```

---

## License

MIT License.
