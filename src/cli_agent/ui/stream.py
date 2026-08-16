import io
import re
from textual.widgets import Log

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class StreamRedirector(io.StringIO):
    """Interceptors stdout/stderr and routes them to the Textual Log widget."""
    def __init__(self, log_widget: Log, original_stream):
        super().__init__()
        self.log_widget = log_widget
        self.original_stream = original_stream

    def write(self, s) -> int:
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='replace')
        s_str = str(s)
        clean_str = ANSI_ESCAPE.sub('', s_str).strip()
        # Remove box-drawing characters and raw trailing fragments that spill over margins
        clean_str = re.sub(r'[─│┌┐└┘├┤┬┴┼━┃┏┓┗┛┣┫┳┻╋╭╮╯╰]', '', clean_str).strip()
        if clean_str:
            try:
                self.log_widget.write_line(clean_str.rstrip())
            except Exception:
                pass
        return len(s)

    def flush(self):
        pass
