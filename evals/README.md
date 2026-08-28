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

## Why this is opt-in, not part of every push

- **Costs real API credits** on every run (one call per scenario, plus
  DeepEval's own LLM-judge call to score each result).
- **Non-deterministic**: model output varies run to run, so some `GEval`
  relevance flakiness is expected and is not, by itself, a regression.
- **Needs network access and a live API key** - not available/desirable on
  every CI matrix leg building a release binary.

It runs via a separate, manually-triggered GitHub Actions workflow
(`.github/workflows/eval_suite.yml`, `workflow_dispatch` only - no cron),
gated on an `OPENAI_API_KEY` repo secret.

## Running locally

```bash
pip install -r requirements.txt -r requirements-dev.txt
export OPENAI_API_KEY=sk-...          # used both as the model under test's
                                       # provider and as DeepEval's LLM-judge
deepeval test run evals/ -v
```

Override the model under test (default `openai/gpt-4o-mini`, chosen for
speed/cost) with:

```bash
export EVAL_MODEL_NAME=openai/gpt-4o
```
