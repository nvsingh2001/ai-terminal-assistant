# Real-inference eval suite (Layer 2)

This directory is **not** part of the regular test suite. It is a
[DeepEval](https://deepeval.com)-based eval suite that exercises the real
`ServiceContainer` -> `LangGraphAgentEngine.run_task()` against a **real,
hosted LLM API** for a curated set of golden prompts, scoring whether the
agent picks the correct skill/tool for each prompt (`ToolCorrectnessMetric`)
and produces a relevant answer (`GEval`).

It is kept structurally separate from `tests/` (a sibling top-level
directory, not a subdirectory of `tests/`) so the default `pytest`/CI
invocation used to gate every push never collects it by accident.

## Provider: Ollama Cloud

Both the model under test and DeepEval's own LLM-judge run against
[Ollama Cloud](https://ollama.com) (`https://ollama.com/v1`, OpenAI-protocol
compatible) - the same remote-Ollama path `LangChainModelResolver` already
uses for the real app (see `src/cli_agent/core/llm/langchain_resolver.py`).
Only `OLLAMA_API_KEY` is required; no OpenAI/Anthropic/Gemini key is needed.

- **Model under test**: `EVAL_MODEL_NAME` (default `ollama/qwen3.5:4b` - fast/cheap).
- **DeepEval's judge**: `EVAL_JUDGE_MODEL` (default `gpt-oss:120b` - a stronger
  model for scoring, wired via DeepEval's `LocalModel` pointed at the same
  Ollama Cloud endpoint - see `judge_model` fixture in `conftest.py`).

## Why this is opt-in, not part of every push

- **Costs real API credits** on every run (one call per scenario, plus
  DeepEval's own LLM-judge call to score each result).
- **Non-deterministic**: model output varies run to run, so some `GEval`
  relevance flakiness is expected and is not, by itself, a regression.
- **Needs network access and a live API key** - not available/desirable on
  every CI matrix leg building a release binary.

It runs via a separate, manually-triggered GitHub Actions workflow
(`.github/workflows/eval_suite.yml`, `workflow_dispatch` only - no cron),
gated on an `OLLAMA_API_KEY` repo secret.

## Running locally

```bash
pip install -r requirements.txt -r requirements-dev.txt
export OLLAMA_API_KEY=...   # from ollama.com -> Settings -> API Keys
deepeval test run evals/ -v
```

Override the models with:

```bash
export EVAL_MODEL_NAME=ollama/gpt-oss:120b
export EVAL_JUDGE_MODEL=gemma4:31b
export OLLAMA_API_BASE=https://ollama.com/v1   # only if not using the default
```
