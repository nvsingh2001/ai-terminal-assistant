"""Edge-case coverage for the 4 built-in skills, beyond the happy-path smoke
tests in test_agent_bootstrap.py."""
import os
import sys

import pytest

from cli_agent.skills.builtins.code_editing.handler import CodeEditingSkill
from cli_agent.skills.builtins.file_management.handler import FileManagementSkill
from cli_agent.skills.builtins.git_operations.handler import GitOperationsSkill
from cli_agent.skills.builtins.shell_execution.handler import ShellExecutionSkill

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="assumes a POSIX shell and path separators"
)


# --- shell_execution -------------------------------------------------------

def test_shell_execution_requires_command():
    skill = ShellExecutionSkill()
    assert "Error" in skill.execute(command="")


@pytest.mark.parametrize(
    "dangerous",
    ["rm -rf /", "echo hi; rm -rf /*", "sudo shutdown -h now", "mkfs.ext4 /dev/sda1"],
)
def test_shell_execution_blocks_dangerous_patterns(dangerous):
    skill = ShellExecutionSkill()
    result = skill.execute(command=dangerous)
    assert "blocked" in result.lower()


def test_shell_execution_reports_nonzero_exit_code():
    skill = ShellExecutionSkill()
    result = skill.execute(command="exit 7")
    assert "exit code 7" in result


def test_shell_execution_captures_stderr():
    skill = ShellExecutionSkill()
    result = skill.execute(command="echo oops 1>&2")
    assert "STDERR" in result and "oops" in result


def test_shell_execution_times_out(monkeypatch):
    skill = ShellExecutionSkill()
    result = skill.execute(command="sleep 0.01")
    # Force a synthetic timeout by patching subprocess.run for this call only
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=120)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = skill.execute(command="sleep 999")
    assert "timed out" in result.lower()


# --- file_management ---------------------------------------------------

def test_file_management_blocks_sensitive_paths():
    skill = FileManagementSkill()
    result = skill.execute(action="read", path=os.path.expanduser("~/.ssh/id_rsa"))
    assert "blocked" in result.lower()


def test_file_management_skips_ignored_dirs(work_dir):
    skill = FileManagementSkill()
    nested = work_dir / "node_modules" / "pkg" / "index.js"
    nested.parent.mkdir(parents=True)
    nested.write_text("console.log(1);")
    result = skill.execute(action="read", path=str(nested))
    assert "skipping" in result.lower()


def test_file_management_read_missing_file(work_dir):
    skill = FileManagementSkill()
    result = skill.execute(action="read", path=str(work_dir / "missing.txt"))
    assert "does not exist" in result


def test_file_management_read_directory_as_file_errors(work_dir):
    skill = FileManagementSkill()
    result = skill.execute(action="read", path=str(work_dir))
    assert "is a directory" in result


def test_file_management_start_line_beyond_total_errors(work_dir):
    target = work_dir / "short.txt"
    target.write_text("line1\nline2\nline3\n")
    skill = FileManagementSkill()
    result = skill.execute(action="read", path=str(target), start_line=100)
    assert "exceeds total file lines" in result


def test_file_management_list_missing_dir_errors(work_dir):
    skill = FileManagementSkill()
    result = skill.execute(action="list", path=str(work_dir / "nope"))
    assert "does not exist" in result


def test_file_management_list_file_as_dir_errors(work_dir):
    target = work_dir / "f.txt"
    target.write_text("hi")
    skill = FileManagementSkill()
    result = skill.execute(action="list", path=str(target))
    assert "is a file, not a directory" in result


def test_file_management_unknown_action(work_dir):
    skill = FileManagementSkill()
    result = skill.execute(action="teleport", path=str(work_dir))
    assert "Unknown action" in result


def test_file_management_write_rejected_under_strict_policy(work_dir, monkeypatch):
    from cli_agent.core.config_manager import config_manager
    from cli_agent.ui.diff_preview import diff_renderer

    original_policy = config_manager.config.execution_policy
    config_manager.config.execution_policy = "strict"
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda: "n")
    try:
        skill = FileManagementSkill()
        target = work_dir / "note.txt"
        result = skill.execute(action="write", path=str(target), content="hi")
        assert "cancelled" in result.lower()
        assert not target.exists()
    finally:
        config_manager.config.execution_policy = original_policy


def test_file_management_write_read_roundtrip_under_yolo(work_dir, yolo_policy):
    skill = FileManagementSkill()
    target = work_dir / "note.txt"
    write_res = skill.execute(action="write", path=str(target), content="hello\n")
    assert "Error" not in write_res
    read_res = skill.execute(action="read", path=str(target))
    assert "hello" in read_res


# --- code_editing --------------------------------------------------------

def test_code_editing_alias_params_take_precedence(work_dir, yolo_policy):
    target = work_dir / "a.py"
    target.write_text("x = 1\n")
    skill = CodeEditingSkill()
    result = skill.execute(
        action="edit",
        path="ignored.py",
        target="ignored",
        replacement="ignored",
        file_path=str(target),
        old_string="x = 1",
        new_string="x = 2",
    )
    assert "Successfully updated" in result
    assert target.read_text() == "x = 2\n"


def test_code_editing_edit_target_not_found(work_dir, yolo_policy):
    target = work_dir / "a.py"
    target.write_text("x = 1\n")
    skill = CodeEditingSkill()
    result = skill.execute(action="edit", path=str(target), target="y = 2", replacement="y = 3")
    assert "not found exactly" in result


def test_code_editing_check_syntax_rejects_non_python(work_dir):
    target = work_dir / "a.txt"
    target.write_text("not python")
    skill = CodeEditingSkill()
    result = skill.execute(action="check_syntax", path=str(target))
    assert "only supported for Python" in result


def test_code_editing_check_syntax_reports_error(work_dir):
    target = work_dir / "bad.py"
    target.write_text("def broken(:\n")
    skill = CodeEditingSkill()
    result = skill.execute(action="check_syntax", path=str(target))
    assert "Syntax Error" in result


def test_code_editing_directory_search_caps_matches_at_50(work_dir):
    for i in range(80):
        (work_dir / f"file_{i}.py").write_text("needle\n")
    skill = CodeEditingSkill()
    result = skill.execute(action="search", path=str(work_dir), target="needle")
    assert "Found 50 match(es)" in result


# --- git_operations --------------------------------------------------------

def test_git_operations_rejects_disallowed_op():
    skill = GitOperationsSkill()
    result = skill.execute(operation="push")
    assert "not allowed" in result


def test_git_operations_status_on_real_repo():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        skill = GitOperationsSkill()
        result = skill.execute(operation="status")
    finally:
        os.chdir(cwd)
    # "On branch X" on a normal checkout, but "HEAD detached at pull/N/merge"
    # under GitHub Actions' pull_request trigger (merge-commit checkout, not
    # a named branch) - see test_agent_bootstrap.py for the same fix.
    lowered = result.lower()
    assert "branch" in lowered or "head detached" in lowered, result


def test_git_operations_commit_injects_message_flag(work_dir, monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        import subprocess as sp

        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    skill = GitOperationsSkill()
    skill.execute(operation="commit", commit_message="fix bug")
    assert '-m "fix bug"' in captured["command"]
