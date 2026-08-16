"""Minimalist Dark Theme CSS stylesheets for Textual TUI Application."""

APP_CSS = """
Screen {
    background: #0d1117;
    layout: vertical;
}

#header-info {
    height: 1;
    background: #161b22;
    color: #f0f6fc;
    content-align: center middle;
    text-align: center;
    border-bottom: solid #30363d;
}

#chat-container {
    height: 1fr;
    padding: 1 2;
    background: #0d1117;
    overflow-x: hidden;
}

#spinner-container {
    height: 1;
    align: center middle;
    display: none;
    background: #161b22;
    color: #38bdf8;
}

#input-container {
    height: 3;
    padding: 0 1;
    margin: 0;
    background: #161b22;
    border-top: solid #30363d;
}

#cmd-input {
    border: none;
    background: #0d1117;
    color: #f0f6fc;
    margin: 0;
}

#skill-palette {
    height: 12;
    margin: 1;
    padding: 1;
    border: double #a855f7;
    background: #161b22;
    color: #f0f6fc;
    display: none;
}

#debug-drawer {
    height: auto;
    margin: 0;
    padding: 0;
    border-top: solid #30363d;
    overflow-x: hidden;
}

#debug-log {
    height: 10;
    background: #010409;
    color: #8b949e;
    overflow-x: hidden;
}

.agent-user {
    margin: 1 0 0 0;
    color: #38bdf8;
}

.agent-router {
    margin: 0 0 0 1;
    color: #a855f7;
}

.agent-execution {
    margin: 1 0 1 1;
    color: #7ee787;
}
"""
