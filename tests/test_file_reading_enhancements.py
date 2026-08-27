import os
import shutil
import tempfile
import unittest

from cli_agent.core.token_budget import TokenBudgeter
from cli_agent.skills.builtins.file_management.handler import FileManagementSkill


class TestFileReadingEnhancements(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aegis_reading_test_")
        self.skill = FileManagementSkill()
        self.budgeter = TokenBudgeter()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_line_range_sliced_reading(self):
        """Tests that start_line and end_line accurately slice file contents with line numbers."""
        file_path = os.path.join(self.test_dir, "numbers.py")
        lines = [f"print('Line {i}')" for i in range(1, 21)]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Read lines 5 to 8
        res = self.skill.execute(action="read", path=file_path, start_line=5, end_line=8)
        self.assertIn("lines 5 to 8 of 20 total lines", res)
        self.assertIn("[L   5] print('Line 5')", res)
        self.assertIn("[L   8] print('Line 8')", res)
        self.assertNotIn("print('Line 4')", res)
        self.assertNotIn("print('Line 9')", res)

    def test_ast_outline_action(self):
        """Tests that action='outline' returns class and method signatures."""
        code_file = os.path.join(self.test_dir, "service.py")
        code = """
class AuthService:
    \"\"\"Handles user authentication and JWT tokens.\"\"\"
    def authenticate(self, username: str, password: str) -> bool:
        # Complex multi-step hashing and db check
        if not username:
            return False
        return True

    def generate_token(self, user_id: str) -> str:
        return "jwt_token_123"
"""
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        res = self.skill.execute(action="outline", path=code_file)
        self.assertIn("[AST Skeleton Outline:", res)
        self.assertIn("class AuthService:", res)
        self.assertIn("def authenticate(self, username: str, password: str) -> bool:", res)
        self.assertIn("def generate_token(self, user_id: str) -> str:", res)
        self.assertNotIn("Complex multi-step hashing", res)

    def test_dynamic_model_token_budgets(self):
        """Tests that models like Nemotron / Gemini get 16k token budgets and smaller models get 4k."""
        self.assertEqual(self.budgeter.get_model_budget("ollama/nemotron-3-ultra"), 16000)
        self.assertEqual(self.budgeter.get_model_budget("gemini/gemini-2.0-flash"), 16000)
        self.assertEqual(self.budgeter.get_model_budget("openai/gpt-4o"), 16000)
        self.assertEqual(self.budgeter.get_model_budget("ollama/gemma:2b"), 4000)


if __name__ == "__main__":
    unittest.main()
