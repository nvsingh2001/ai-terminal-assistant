import os
import shutil
import tempfile
import unittest

from cli_agent.core.safety.rollback import RollbackManager
from cli_agent.ui.diff_preview import DiffPreviewRenderer
from cli_agent.core.config_manager import AgentConfig, ConfigManager
from cli_agent.skills.builtins.code_editing.handler import CodeEditingSkill
from cli_agent.skills.builtins.file_management.handler import FileManagementSkill


class TestRollbackAndDiff(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aegis_test_")
        self.snapshot_dir = os.path.join(self.test_dir, "snapshots")
        self.rollback_mgr = RollbackManager(base_snapshot_dir=self.snapshot_dir)
        self.diff_renderer = DiffPreviewRenderer()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_file_snapshot_and_rollback(self):
        """Tests that RollbackManager restores original file content upon rollback."""
        file_path = os.path.join(self.test_dir, "sample.py")
        original_content = "def hello():\n    print('Hello World')\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original_content)

        # 1. Record pre-edit snapshot
        self.rollback_mgr.record_pre_edit(file_path)

        # 2. Modify file
        modified_content = "def hello():\n    print('Hello Production')\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        self.assertEqual(open(file_path).read(), modified_content)

        # 3. Rollback
        restored = self.rollback_mgr.rollback_last_transaction()
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0], os.path.abspath(file_path))
        self.assertEqual(open(file_path).read(), original_content)

    def test_new_file_creation_rollback(self):
        """Tests that rollback removes newly created files."""
        new_file_path = os.path.join(self.test_dir, "brand_new.txt")
        self.assertFalse(os.path.exists(new_file_path))

        # Record snapshot of non-existing file
        self.rollback_mgr.record_pre_edit(new_file_path)

        # Create file
        with open(new_file_path, "w") as f:
            f.write("Some new content")
        self.assertTrue(os.path.exists(new_file_path))

        # Rollback should delete it
        restored = self.rollback_mgr.rollback_last_transaction()
        self.assertEqual(len(restored), 1)
        self.assertFalse(os.path.exists(new_file_path))

    def test_diff_generation(self):
        """Tests unified diff generation logic."""
        old_text = "line1\nline2\nline3\n"
        new_text = "line1\nline2_modified\nline3\nline4\n"
        diff_lines = self.diff_renderer.generate_diff_lines("test.py", old_text, new_text)

        self.assertTrue(any("-line2" in line for line in diff_lines))
        self.assertTrue(any("+line2_modified" in line for line in diff_lines))
        self.assertTrue(any("+line4" in line for line in diff_lines))

    def test_yolo_policy_auto_accept(self):
        """Tests that yolo policy auto-accepts without interactive prompt."""
        accepted = self.diff_renderer.request_approval(
            file_path="foo.py",
            old_content="a = 1",
            new_content="a = 2",
            policy="yolo"
        )
        self.assertTrue(accepted)


if __name__ == "__main__":
    unittest.main()
