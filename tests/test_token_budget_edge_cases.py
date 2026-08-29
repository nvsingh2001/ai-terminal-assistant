"""Edge cases for TokenBudgeter beyond the happy-path pagination/outline
coverage in test_file_reading_enhancements.py."""
import pytest

from cli_agent.core.token_budget import TokenBudgeter


@pytest.fixture
def budgeter():
    return TokenBudgeter()


# --- get_model_budget --------------------------------------------------

@pytest.mark.parametrize(
    "model_name",
    ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-flash", "qwen2.5-coder:32b", "deepseek-coder"],
)
def test_get_model_budget_large_context_models(budgeter, model_name):
    assert budgeter.get_model_budget(model_name) == 16000


@pytest.mark.parametrize("model_name", ["qwen3.5:4b", "llama3.2"])
def test_get_model_budget_default_small_models(budgeter, model_name):
    assert budgeter.get_model_budget(model_name) == 4000


def test_get_model_budget_is_case_insensitive(budgeter):
    assert budgeter.get_model_budget("GPT-4O") == 16000


def test_get_model_budget_falls_back_to_instance_model_name_when_unset(budgeter):
    # budgeter.model_name defaults to "gpt-4o" (a large-context keyword) - an
    # empty/None override at call time falls back to that instance default
    # rather than to a hardcoded small budget.
    assert budgeter.get_model_budget("") == 16000
    assert budgeter.get_model_budget(None) == 16000


def test_get_model_budget_empty_instance_model_name_yields_default_small_budget():
    small_budgeter = TokenBudgeter(model_name="")
    assert small_budgeter.get_model_budget(None) == 4000


# --- extract_ast_skeleton ------------------------------------------------

def test_ast_skeleton_extracts_class_and_function_signatures(budgeter):
    code = (
        "import os\n\n"
        "class Greeter:\n"
        "    \"\"\"Greets people.\"\"\"\n"
        "    def hello(self, name):\n"
        "        return f'hi {name}'\n\n"
        "def standalone(x, y):\n"
        "    return x + y\n"
    )
    skeleton = budgeter.extract_ast_skeleton(code, filename="greet.py")
    assert "class Greeter:" in skeleton
    assert "def hello(self, name):" in skeleton
    assert "def standalone(x, y):" in skeleton
    assert "return x + y" not in skeleton  # bodies are omitted
    assert "import os" in skeleton


def test_ast_skeleton_falls_back_to_regex_for_non_python_files(budgeter):
    js_code = "function foo() {\n  return 1;\n}\n\nclass Bar {\n}\n\nconst x = 5;\n"
    skeleton = budgeter.extract_ast_skeleton(js_code, filename="app.js")
    assert "function foo() {" in skeleton
    assert "class Bar {" in skeleton
    assert "const x = 5;" not in skeleton


def test_ast_skeleton_falls_back_to_regex_on_python_syntax_error(budgeter):
    broken_code = "def broken(:\n    pass\n\nclass Ok:\n    pass\n"
    skeleton = budgeter.extract_ast_skeleton(broken_code, filename="broken.py")
    # ast.parse fails, so this must come from the regex fallback, not AST.
    assert "def broken(:" in skeleton
    assert "class Ok:" in skeleton


def test_regex_skeleton_hard_truncates_when_no_structure_found(budgeter):
    text = "x" * 3000
    skeleton = budgeter._extract_regex_skeleton(text)
    assert skeleton.startswith("x" * 2000)
    assert "truncated for token budget" in skeleton.lower()


# --- count_tokens ------------------------------------------------------

def test_count_tokens_empty_string_is_zero(budgeter):
    assert budgeter.count_tokens("") == 0


def test_count_tokens_falls_back_to_char_estimate_without_tiktoken(budgeter):
    budgeter.encoder = None
    text = "a" * 100
    assert budgeter.count_tokens(text) == 25


# --- budget_text ---------------------------------------------------------

def test_budget_text_returns_unchanged_when_under_limit(budgeter):
    text = "short text"
    assert budgeter.budget_text(text, max_tokens=1000) == text


def test_budget_text_hard_truncates_non_code_when_over_limit(budgeter):
    text = "word " * 2000
    result = budgeter.budget_text(text, max_tokens=10, is_code=False)
    assert result.startswith(text[:40])
    assert "WARNING: Content truncated" in result


def test_budget_text_uses_ast_skeleton_for_code_when_it_fits_budget(budgeter):
    # Short signature, huge body - omitting the body should shrink this well
    # below the budget even though the full text is far over it.
    code = "def small():\n" + "    x = 1\n" * 500
    result = budgeter.budget_text(code, max_tokens=50, is_code=True, filename="huge.py")
    assert "AST Skeleton View" in result
    assert "Implementation omitted" in result
