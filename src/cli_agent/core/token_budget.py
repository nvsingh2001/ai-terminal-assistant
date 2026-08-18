import ast
import re
from typing import Optional

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False

class TokenBudgeter:
    """
    AST-Aware Code Inspector & Token Budgeting Engine.
    Dynamically counts tokens and converts dense code files into light AST skeletons
    when prompt token budgets are tight.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.encoder = None
        if _TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.encoding_for_model(model_name)
            except Exception:
                try:
                    self.encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self.encoder = None

    def count_tokens(self, text: str) -> int:
        """Counts exact tokens using tiktoken, falling back to char estimation."""
        if not text:
            return 0
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass
        return len(text) // 4

    def extract_ast_skeleton(self, code_text: str, filename: str = "code.py") -> str:
        """
        Parses Python code via AST to extract Class signatures, Methods, and Docstrings,
        omitting internal function bodies to reduce token footprint by up to 80%.
        """
        if not filename.endswith(".py"):
            return self._extract_regex_skeleton(code_text)

        try:
            tree = ast.parse(code_text)
            skeleton_lines = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    skeleton_lines.append(self._format_func_ast(node))
                elif isinstance(node, ast.ClassDef):
                    skeleton_lines.append(f"class {node.name}:")
                    doc = ast.get_docstring(node)
                    if doc:
                        skeleton_lines.append(f'    """{doc}"""')
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            skeleton_lines.append("    " + self._format_func_ast(item).replace("\n", "\n    "))
                elif isinstance(node, ast.Import):
                    names = ", ".join(alias.name for alias in node.names)
                    skeleton_lines.append(f"import {names}")
                elif isinstance(node, ast.ImportFrom):
                    names = ", ".join(alias.name for alias in node.names)
                    skeleton_lines.append(f"from {node.module} import {names}")

            if skeleton_lines:
                return "\n".join(skeleton_lines)
        except Exception:
            pass

        return self._extract_regex_skeleton(code_text)

    def _format_func_ast(self, node: ast.AST) -> str:
        args_str = ast.unparse(node.args) if hasattr(ast, "unparse") else "..."
        returns_str = f" -> {ast.unparse(node.returns)}" if getattr(node, "returns", None) and hasattr(ast, "unparse") else ""
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        func_sig = f"{prefix} {node.name}({args_str}){returns_str}:"
        doc = ast.get_docstring(node)
        if doc:
            return f'{func_sig}\n    """{doc}"""\n    ... # [AST Skeleton: Implementation omitted]'
        return f"{func_sig}\n    ... # [AST Skeleton: Implementation omitted]"

    def _extract_regex_skeleton(self, code_text: str) -> str:
        """Regex fallback skeleton extractor for non-Python or unparseable code files."""
        lines = code_text.splitlines()
        skeleton = []
        pattern = re.compile(r'^\s*(def|class|function|async def|public|private|type|interface|struct)\s+.*')
        for line in lines:
            if pattern.match(line) or line.strip().startswith(("import ", "from ", "export ", "#include")):
                skeleton.append(line)
        if not skeleton:
            return code_text[:2000] + "\n[... Content truncated for token budget ...]"
        return "\n".join(skeleton)

    def get_model_budget(self, model_name: Optional[str] = None) -> int:
        """Determines safe token budget based on active model context window capacity."""
        target_model = (model_name or self.model_name or "").lower()
        # Large context window models (128k - 1M+ tokens)
        large_context_keywords = [
            "nemotron", "gemini", "gpt-4", "claude", "qwen2.5-coder:32b",
            "qwen-2.5-coder:32b", "gpt-oss", "gemma4:31b", "deepseek"
        ]
        for kw in large_context_keywords:
            if kw in target_model:
                return 16000  # ~2,500+ lines of full code without skeletonizing

        return 4000  # Default safe limit for smaller / local models

    def budget_text(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        is_code: bool = False,
        filename: str = "file.txt",
        model_name: Optional[str] = None,
    ) -> str:
        """
        Enforces a dynamic, model-aware max_tokens budget on input text.
        If is_code and token limit is exceeded, uses AST skeleton extraction as fallback.
        """
        limit = max_tokens if max_tokens is not None else self.get_model_budget(model_name)
        current_tokens = self.count_tokens(text)
        if current_tokens <= limit:
            return text

        if is_code:
            skeleton = self.extract_ast_skeleton(text, filename)
            skeleton_tokens = self.count_tokens(skeleton)
            if skeleton_tokens <= limit:
                return f"[AST Skeleton View - Truncated for Token Budget ({current_tokens} -> {skeleton_tokens} tokens)]\n{skeleton}"

        # Hard char truncation fallback
        char_limit = limit * 4
        return text[:char_limit] + f"\n\n[WARNING: Content truncated from {current_tokens} to ~{limit} tokens for LLM window safety.]"


# Global TokenBudgeter singleton
token_budgeter = TokenBudgeter()

