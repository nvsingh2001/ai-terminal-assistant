#!/bin/sh
set -e

REPO="Ayushsingh-02082004/ai-terminal-assistant"
INSTALL_DIR="$HOME/.cli-agent/bin"
EXE_PATH="$INSTALL_DIR/cli-agent"

echo "=== Installing CLI Agent (cli-agent) ==="

# Detect OS and Arch
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" = "Darwin" ]; then
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        BINARY_NAME="cli-agent-darwin-arm64"
    else
        BINARY_NAME="cli-agent-darwin-amd64"
    fi
elif [ "$OS" = "Linux" ]; then
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
        BINARY_NAME="cli-agent-linux-amd64"
    else
        BINARY_NAME="cli-agent-linux-amd64"
    fi
else
    echo "Unsupported Operating System: $OS"
    exit 1
fi

mkdir -p "$INSTALL_DIR"

DOWNLOAD_URL="https://github.com/$REPO/releases/latest/download/$BINARY_NAME"

echo "Downloading $BINARY_NAME from GitHub Releases..."
curl -fsSL "$DOWNLOAD_URL" -o "$EXE_PATH"
chmod +x "$EXE_PATH"

echo "Successfully installed cli-agent to $EXE_PATH"

# Check if PATH contains install directory
case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *)
        SHELL_PROFILE=""
        if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
            SHELL_PROFILE="$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_PROFILE="$HOME/.bashrc"
        fi

        if [ -n "$SHELL_PROFILE" ]; then
            echo "Adding $INSTALL_DIR to $SHELL_PROFILE..."
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_PROFILE"
        fi
        ;;
esac

echo ""
echo "=== Installation Complete! ==="
echo "Open any terminal window and type: cli-agent"
