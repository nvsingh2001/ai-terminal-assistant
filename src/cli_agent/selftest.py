import os
import shutil
import sys
import tempfile
import traceback


def run_selftest() -> int:
    """Runs a set of real functional checks against the actual running
    interpreter/bundle (source venv or frozen PyInstaller binary alike).

    Exists because a plain unittest run against the source tree cannot
    detect bugs that only manifest in the frozen binary (e.g. a plugin
    module PyInstaller's static analysis misses via --collect-all but
    doesn't --hidden-import). Prints PASS/FAIL per check; exits non-zero
    on any failure so CI can gate on it.
    """
    from rich.console import Console

    from cli_agent.container import ServiceContainer

    failures = []

    def check(name, fn):
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as e:
            failures.append(name)
            print(f"[FAIL] {name}: {e}")
            traceback.print_exc()

    container = ServiceContainer.create_default(console=Console(), prompt_session=None)
    test_dir = tempfile.mkdtemp(prefix="aegis_selftest_")

    try:
        def check_skills_discovered():
            names = {s.name for s in container.skill_registry.list_skills()}
            expected = {"shell_execution", "file_management", "code_editing", "git_operations"}
            assert names == expected, f"expected {expected}, got {names}"

        def check_commands_registered():
            names = container.dispatcher.get_command_names()
            for expected in ("/help", "/model", "/skills", "/memory", "/verbose", "/undo", "/exit"):
                assert expected in names, f"missing command {expected}"

        def check_shell_execution():
            result = container.skill_registry.execute(
                "shell_execution", command="echo aegis-selftest"
            )
            assert "aegis-selftest" in result, result

        def check_file_management_roundtrip():
            target = os.path.join(test_dir, "note.txt")
            original_policy = container.config_manager.config.execution_policy
            container.config_manager.config.execution_policy = "yolo"
            try:
                write_res = container.skill_registry.execute(
                    "file_management", action="write", path=target, content="hello from selftest\n"
                )
                assert "Error" not in write_res, write_res
            finally:
                container.config_manager.config.execution_policy = original_policy

            read_res = container.skill_registry.execute("file_management", action="read", path=target)
            assert "hello from selftest" in read_res, read_res

        def check_code_editing_syntax():
            good_file = os.path.join(test_dir, "valid.py")
            with open(good_file, "w", encoding="utf-8") as f:
                f.write("def add(a, b):\n    return a + b\n")
            result = container.skill_registry.execute(
                "code_editing", action="check_syntax", path=good_file
            )
            assert "Syntax check passed" in result, result

        def check_git_operations():
            result = container.skill_registry.execute("git_operations", operation="status")
            assert "Error: Operation" not in result, result

        check("skill_registry discovers all 4 built-in skills", check_skills_discovered)
        check("dispatcher registers all slash commands", check_commands_registered)
        check("shell_execution skill runs a real command", check_shell_execution)
        check("file_management skill write+read roundtrip", check_file_management_roundtrip)
        check("code_editing skill check_syntax", check_code_editing_syntax)
        check("git_operations skill status", check_git_operations)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    if failures:
        print(f"\n=== SELFTEST FAILED ({len(failures)} check(s)): {', '.join(failures)} ===", file=sys.stderr)
        return 1

    print("\n=== SELFTEST PASSED ===")
    return 0
