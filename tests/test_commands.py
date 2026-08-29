"""Command dispatcher alias/fuzzy resolution, plus execute() logic for slash
commands beyond the "is registered" check in test_agent_bootstrap.py."""
import pytest

from cli_agent.commands.base import CommandContext, ISlashCommand
from cli_agent.commands.dispatcher import CommandDispatcher
from cli_agent.commands.forget_cmd import ForgetCommand
from cli_agent.commands.memory_cmd import MemoryCommand
from cli_agent.commands.model_cmd import ModelCommand
from cli_agent.commands.policy_cmd import PolicyCommand
from cli_agent.commands.remember_cmd import RememberCommand
from cli_agent.commands.verbose_cmd import VerboseCommand
from cli_agent.core.config_manager import config_manager
from cli_agent.memory.manager import tri_tier_memory
from cli_agent.skills.registry import skill_registry


class FakeConsole:
    def __init__(self):
        self.lines = []

    def print(self, *args, **kwargs):
        self.lines.append(" ".join(str(a) for a in args))

    @property
    def text(self):
        return "\n".join(self.lines)


class FakePromptSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def prompt(self, *args, **kwargs):
        return self._responses.pop(0)


def make_context(prompt_responses=None, engine=None):
    return CommandContext(
        prompt_session=FakePromptSession(prompt_responses or []),
        config_manager=config_manager,
        skill_registry=skill_registry,
        memory_store=None,
        console=FakeConsole(),
        engine=engine,
        tri_tier_memory=tri_tier_memory,
    )


# --- dispatcher alias/fuzzy resolution --------------------------------------

class _StubCommand(ISlashCommand):
    def __init__(self, name):
        self._name = name
        self.calls = 0

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return "stub"

    def execute(self, context, raw_args=""):
        self.calls += 1
        return True


def test_dispatcher_resolves_registered_alias():
    ctx = make_context()
    dispatcher = CommandDispatcher(ctx)
    undo = _StubCommand("/undo")
    dispatcher.register(undo)
    # "exit"/"clear"/"help" are baked-in aliases; policy/undo aliases are
    # registered per-command via ISlashCommand.aliases, not the dispatcher's
    # static _aliases map - simulate the same "/quit" -> "/exit" pattern.
    exit_cmd = _StubCommand("/exit")
    dispatcher.register(exit_cmd)
    assert dispatcher.dispatch("quit") is True
    assert exit_cmd.calls == 1


def test_dispatcher_dispatches_exact_match_with_args():
    ctx = make_context()
    dispatcher = CommandDispatcher(ctx)
    policy = PolicyCommand()
    dispatcher.register(policy)
    handled = dispatcher.dispatch("/policy yolo")
    assert handled is True
    assert config_manager.config.execution_policy == "yolo"


def test_dispatcher_unknown_slash_command_gives_fuzzy_hint():
    ctx = make_context()
    dispatcher = CommandDispatcher(ctx)
    dispatcher.register(_StubCommand("/policy"))
    handled = dispatcher.dispatch("/pol")
    assert handled is True
    assert "Did you mean '/policy'?" in ctx.console.text


def test_dispatcher_unknown_non_slash_input_falls_through_to_llm():
    ctx = make_context()
    dispatcher = CommandDispatcher(ctx)
    assert dispatcher.dispatch("what is the weather") is False


def test_dispatcher_empty_input_is_not_handled():
    ctx = make_context()
    dispatcher = CommandDispatcher(ctx)
    assert dispatcher.dispatch("   ") is False


# --- /policy -----------------------------------------------------------

def test_policy_command_direct_arg_sets_policy():
    ctx = make_context()
    original = config_manager.config.execution_policy
    try:
        PolicyCommand().execute(ctx, "strict")
        assert config_manager.config.execution_policy == "strict"
    finally:
        config_manager.config.execution_policy = original


def test_policy_command_interactive_menu_choice():
    ctx = make_context(prompt_responses=["3"])
    original = config_manager.config.execution_policy
    try:
        PolicyCommand().execute(ctx, "")
        assert config_manager.config.execution_policy == "yolo"
    finally:
        config_manager.config.execution_policy = original


# --- /model --------------------------------------------------------------

def test_model_command_local_ollama_choice_needs_no_key_prompt():
    ctx = make_context(prompt_responses=["4"])
    original = config_manager.config.model_name
    try:
        ModelCommand().execute(ctx, "")
        assert config_manager.config.model_name == "ollama/qwen3.5:4b"
    finally:
        config_manager.config.model_name = original


def test_model_command_missing_gguf_path_does_not_update_model():
    ctx = make_context(prompt_responses=["8", "/no/such/model.gguf"])
    original = config_manager.config.model_name
    ModelCommand().execute(ctx, "")
    assert config_manager.config.model_name == original
    assert "not found" in ctx.console.text.lower()


# --- /verbose --------------------------------------------------------------

class _StubEngine:
    def __init__(self):
        self.verbose = None

    def set_verbose(self, value):
        self.verbose = value


def test_verbose_command_toggles_state():
    engine = _StubEngine()
    ctx = make_context(engine=engine)
    original = config_manager.config.verbose
    try:
        new_state = not original
        VerboseCommand().execute(ctx, "")
        assert config_manager.config.verbose == new_state
        assert engine.verbose == new_state
    finally:
        config_manager.config.verbose = original


# --- /remember, /forget, /memory (real isolated SQLite store) --------------

def test_remember_and_forget_project_fact_roundtrip():
    ctx = make_context()
    RememberCommand().execute(ctx, "database=DuckDB")
    facts = {f.key: f.value for f in tri_tier_memory.get_project_facts()}
    assert facts.get("database") == "DuckDB"

    ForgetCommand().execute(ctx, "database")
    facts_after = {f.key: f.value for f in tri_tier_memory.get_project_facts()}
    assert "database" not in facts_after


def test_remember_global_preference():
    ctx = make_context()
    RememberCommand().execute(ctx, "--global preferred_shell=bash")
    prefs = tri_tier_memory.get_global_preferences()
    assert prefs.get("preferred_shell") == "bash"


def test_forget_unknown_key_reports_not_found():
    ctx = make_context()
    ForgetCommand().execute(ctx, "no_such_key")
    assert "not found" in ctx.console.text.lower()


def test_memory_command_renders_without_error():
    ctx = make_context()
    handled = MemoryCommand().execute(ctx, "")
    assert handled is True
