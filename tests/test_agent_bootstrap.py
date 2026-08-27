import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from rich.console import Console

from cli_agent.container import ServiceContainer


class TestAgentBootstrap(unittest.TestCase):
    """End-to-end wiring + built-in skill execution, with no LLM/network calls.

    Exercises the same DI container the real TUI uses (`run_native_app` ->
    `ServiceContainer.create_default`), so a break here means the frozen
    binary would fail on startup for every user, on every platform.
    """

    def setUp(self):
        self.container = ServiceContainer.create_default(console=Console(), prompt_session=None)
        self.test_dir = tempfile.mkdtemp(prefix="aegis_bootstrap_test_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_all_builtin_skills_discovered(self):
        names = {skill.name for skill in self.container.skill_registry.list_skills()}
        self.assertEqual(
            names,
            {"shell_execution", "file_management", "code_editing", "git_operations"},
        )

    def test_all_slash_commands_registered(self):
        names = self.container.dispatcher.get_command_names()
        for expected in ("/help", "/model", "/skills", "/memory", "/verbose", "/undo", "/exit"):
            self.assertIn(expected, names)

    def test_shell_execution_skill_runs_real_command(self):
        result = self.container.skill_registry.execute(
            "shell_execution", command="echo aegis-ci-smoke-test"
        )
        self.assertIn("aegis-ci-smoke-test", result)

    def test_file_management_skill_write_then_read_roundtrip(self):
        target = os.path.join(self.test_dir, "note.txt")

        # Writes go through an interactive diff-approval prompt; force
        # non-interactive auto-accept (same mechanism the real "yolo"
        # execution policy uses) so this can run unattended in CI.
        original_policy = self.container.config_manager.config.execution_policy
        self.container.config_manager.config.execution_policy = "yolo"
        try:
            write_res = self.container.skill_registry.execute(
                "file_management", action="write", path=target, content="hello from CI\n"
            )
        finally:
            self.container.config_manager.config.execution_policy = original_policy
        self.assertNotIn("Error", write_res)

        read_res = self.container.skill_registry.execute(
            "file_management", action="read", path=target
        )
        self.assertIn("hello from CI", read_res)

    def test_code_editing_skill_check_syntax(self):
        good_file = os.path.join(self.test_dir, "valid.py")
        with open(good_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        result = self.container.skill_registry.execute(
            "code_editing", action="check_syntax", path=good_file
        )
        self.assertIn("Syntax check passed", result)

    def test_git_operations_skill_status_on_real_repo(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cwd = os.getcwd()
        try:
            os.chdir(repo_root)
            result = self.container.skill_registry.execute("git_operations", operation="status")
        finally:
            os.chdir(cwd)
        # A real `git status` on a real repo (actions/checkout gives one on
        # every CI leg) always mentions the branch; asserting on that (vs.
        # merely "no error") also fails if git is missing or cwd isn't a
        # repo, not just if the operation name were rejected.
        self.assertIn("branch", result.lower())


if __name__ == "__main__":
    unittest.main()
