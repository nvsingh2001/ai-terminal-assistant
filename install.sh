#!/bin/sh
set -e

REPO="nvsingh2001/ai-terminal-assistant"
INSTALL_DIR="$HOME/.local/bin"
EXE_PATH="$INSTALL_DIR/aegis"
ALIAS_PATH="$INSTALL_DIR/cli-agent"

echo "=== Installing Aegis Terminal Agent (aegis) ==="

# Detect OS and Arch
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" = "Darwin" ]; then
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        BINARY_NAME="aegis-darwin-arm64"
    else
        BINARY_NAME="aegis-darwin-amd64"
    fi
elif [ "$OS" = "Linux" ]; then
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
        BINARY_NAME="aegis-linux-amd64"
    else
        echo "Unsupported Linux architecture: $ARCH (only x86_64 is currently built)"
        exit 1
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

# Clears the quarantine flag some macOS setups apply to downloaded files,
# which otherwise makes Gatekeeper report the binary as "damaged".
if [ "$OS" = "Darwin" ]; then
    xattr -d com.apple.quarantine "$EXE_PATH" 2>/dev/null || true
fi

ln -sf "$EXE_PATH" "$ALIAS_PATH"

echo "Successfully installed aegis to $EXE_PATH (and symlinked $ALIAS_PATH)"

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
echo "Open any terminal window and type: aegis"
