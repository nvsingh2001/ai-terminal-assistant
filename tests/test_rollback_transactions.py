"""Multi-file transaction ordering, clear(), and interactive approval-prompt
paths not covered by test_rollback_and_diff.py's single-file happy paths."""
import os

import pytest

from cli_agent.core.safety.rollback import RollbackManager
from cli_agent.ui.diff_preview import DiffPreviewRenderer


@pytest.fixture
def rollback_mgr(tmp_path):
    return RollbackManager(base_snapshot_dir=str(tmp_path / "snapshots"))


@pytest.fixture
def diff_renderer():
    return DiffPreviewRenderer()


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_single_transaction_restores_multiple_files(rollback_mgr, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    _write(a, "a-original")
    _write(b, "b-original")

    rollback_mgr.begin_transaction()
    rollback_mgr.record_pre_edit(str(a))
    rollback_mgr.record_pre_edit(str(b))
    rollback_mgr.commit_transaction()

    _write(a, "a-modified")
    _write(b, "b-modified")

    restored = rollback_mgr.rollback_last_transaction()
    assert len(restored) == 2
    assert a.read_text() == "a-original"
    assert b.read_text() == "b-original"


def test_transactions_roll_back_in_lifo_order(rollback_mgr, tmp_path):
    f = tmp_path / "f.txt"
    _write(f, "v1")

    rollback_mgr.begin_transaction()
    rollback_mgr.record_pre_edit(str(f))
    rollback_mgr.commit_transaction()
    _write(f, "v2")

    rollback_mgr.begin_transaction()
    rollback_mgr.record_pre_edit(str(f))
    rollback_mgr.commit_transaction()
    _write(f, "v3")

    # First undo reverts the most recent transaction (v3 -> v2)
    rollback_mgr.rollback_last_transaction()
    assert f.read_text() == "v2"

    # Second undo reverts the earlier transaction (v2 -> v1)
    rollback_mgr.rollback_last_transaction()
    assert f.read_text() == "v1"

    # Nothing left to roll back
    assert rollback_mgr.rollback_last_transaction() == []


def test_record_pre_edit_within_open_transaction_does_not_auto_commit(rollback_mgr, tmp_path):
    f = tmp_path / "f.txt"
    _write(f, "v1")

    rollback_mgr.begin_transaction()
    rollback_mgr.record_pre_edit(str(f))
    # Transaction is still open - nothing on the stack yet, so a rollback is a no-op.
    assert rollback_mgr.rollback_last_transaction() == []
    rollback_mgr.commit_transaction()
    assert len(rollback_mgr.transaction_stack) == 1


def test_clear_removes_snapshot_dir_and_stack(rollback_mgr, tmp_path):
    f = tmp_path / "f.txt"
    _write(f, "v1")
    rollback_mgr.record_pre_edit(str(f))
    assert os.path.exists(rollback_mgr.session_dir)
    assert len(rollback_mgr.transaction_stack) == 1

    rollback_mgr.clear()

    assert rollback_mgr.transaction_stack == []
    assert rollback_mgr._current_transaction is None
    assert not os.path.exists(rollback_mgr.session_dir)


# --- interactive approval prompt paths ------------------------------------

def test_request_approval_accepts_on_y(diff_renderer, monkeypatch):
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda: "y")
    accepted = diff_renderer.request_approval("f.py", "old", "new", policy="strict")
    assert accepted is True


def test_request_approval_empty_input_defaults_to_accept(diff_renderer, monkeypatch):
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda: "")
    accepted = diff_renderer.request_approval("f.py", "old", "new", policy="trusted-read")
    assert accepted is True


def test_request_approval_rejects_on_n(diff_renderer, monkeypatch):
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda: "n")
    accepted = diff_renderer.request_approval("f.py", "old", "new", policy="strict")
    assert accepted is False


def test_request_approval_keyboard_interrupt_cancels(diff_renderer, monkeypatch):
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)

    def raise_interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", lambda: raise_interrupt())
    accepted = diff_renderer.request_approval("f.py", "old", "new", policy="strict")
    assert accepted is False


def test_request_approval_always_persists_for_session(diff_renderer, monkeypatch):
    monkeypatch.setattr(diff_renderer, "render_diff", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda: "a")

    first = diff_renderer.request_approval("f.py", "old", "new", policy="strict")
    assert first is True
    assert diff_renderer.always_accept is True

    # A second call under the same renderer no longer needs to prompt at all -
    # remove the input stub entirely to prove it's not consulted.
    monkeypatch.delattr("builtins.input")
    second = diff_renderer.request_approval("f.py", "old", "newer", policy="strict")
    assert second is True
