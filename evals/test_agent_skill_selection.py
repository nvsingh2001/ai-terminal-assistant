"""Golden-scenario real-inference evals: does the agent pick the right skill
(and produce a relevant answer) for a natural-language prompt?

Runs the real LangGraphAgentEngine end-to-end against EVAL_MODEL_NAME (see
conftest.py) - no mocking of the model. Both the model under test and
DeepEval's own LLM-judge run against Ollama Cloud, so only OLLAMA_API_KEY is
required - no OpenAI/Anthropic/Gemini keys needed.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall

SCENARIOS = [
    pytest.param(
        "List the files in this directory.",
        ["file_management"],
        id="list-files",
    ),
    pytest.param(
        "What is the current git status of this repository?",
        ["git_operations"],
        id="git-status",
    ),
    pytest.param(
        "Create a file named notes.txt containing exactly the text 'hello world'.",
        ["file_management"],
        id="create-file",
    ),
    pytest.param(
        "Run the shell command: echo aegis-eval",
        ["shell_execution"],
        id="run-shell-command",
    ),
    pytest.param(
        "What is 2 + 2? Just answer with the number, no tools needed.",
        [],
        id="direct-completion-no-tools",
    ),
]


def _run_scenario(container, judge_model, prompt, expected_tools):
    result = container.engine.run_task(prompt)
    tools_invoked = list(dict.fromkeys(container.engine._tools_invoked_in_turn))

    test_case = LLMTestCase(
        input=prompt,
        actual_output=result["execution"],
        tools_called=[ToolCall(name=t) for t in tools_invoked],
        expected_tools=[ToolCall(name=t) for t in expected_tools],
    )

    tool_correctness = ToolCorrectnessMetric(threshold=0.5, model=judge_model)
    relevance = GEval(
        name="Relevance",
        criteria="Determine whether the actual output directly and correctly addresses the input request.",
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.5,
        model=judge_model,
    )
    assert_test(test_case, [tool_correctness, relevance])


@pytest.mark.parametrize("prompt, expected_tools", SCENARIOS)
def test_agent_picks_correct_skill(container, judge_model, prompt, expected_tools):
    _run_scenario(container, judge_model, prompt, expected_tools)


def test_agent_checks_python_syntax(container, judge_model, scratch_repo):
    target = scratch_repo / "sample.py"
    target.write_text("def add(a, b):\n    return a + b\n")
    _run_scenario(
        container,
        judge_model,
        f"Check whether the Python file at {target} has valid syntax.",
        ["code_editing"],
    )
