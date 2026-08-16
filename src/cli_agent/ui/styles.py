"""Modern Slate / Obsidian Theme CSS stylesheets for the Textual TUI Application."""

APP_CSS = """
Screen {
    background: #0f172a;
    layout: vertical;
}

#header-info {
    height: 1;
    background: #1e293b;
    color: #f8fafc;
    content-align: center middle;
}

#chat-container {
    height: 1fr;
    padding: 1 2;
    background: #0f172a;
}

#spinner-container {
    height: 3;
    align: center middle;
    display: none;
    background: #1e293b;
    color: #38bdf8;
}

#input-container {
    height: 3;
    padding: 0 1;
    margin: 0;
    background: #1e293b;
}

#cmd-input {
    border: tall #38bdf8;
    background: #0f172a;
    color: #f8fafc;
    margin: 0;
}

#skill-palette {
    height: 12;
    margin: 1;
    padding: 1;
    border: double #a855f7;
    background: #1e293b;
    color: #f8fafc;
    display: none;
}

#debug-drawer {
    height: auto;
    margin: 0;
    padding: 0;
    border-top: solid #475569;
    overflow-x: hidden;
}

#debug-log {
    height: 10;
    background: #020617;
    color: #94a3b8;
    overflow-x: hidden;
}
"""
