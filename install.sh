#!/usr/bin/env bash
# nicetransfer — installation script
# Creates a venv, installs dependencies, and generates run.sh and config.toml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
DATA_DIR="$SCRIPT_DIR/data"

echo "nicetransfer — Installation"
echo "Directory: $SCRIPT_DIR"
echo

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "✗ python3 not found."
    echo "  Install with: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ python3 found ($PYTHON_VERSION)"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "→ creating venv in .venv ..."
    python3 -m venv "$VENV_DIR"
    echo "✓ venv created"
else
    echo "✓ venv already exists"
fi

# Upgrade pip
echo "→ upgrading pip ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip

# Install dependencies
echo "→ installing nicegui ..."
"$VENV_DIR/bin/pip" install --quiet nicegui

echo "→ installing qrcode ..."
"$VENV_DIR/bin/pip" install --quiet "qrcode[svg]"

echo "✓ dependencies installed"

# Generate run.sh
cat > "$SCRIPT_DIR/run.sh" << EOF
#!/usr/bin/env bash
# nicetransfer — start script
# Usage: ./run.sh [--no-upload] [--no-download] [--port 8888]

source "$VENV_DIR/bin/activate"
python3 "$SCRIPT_DIR/nicetransfer.py" "\$@"
EOF

chmod +x "$SCRIPT_DIR/run.sh"
echo "✓ run.sh created"

# Create config.toml if it doesn't exist
CONFIG_FILE="$SCRIPT_DIR/config.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << EOF
# nicetransfer configuration
# Paths: absolute or with ~/ (will be expanded)

[dirs]
upload   = "$DATA_DIR/upload"
download = "$DATA_DIR/download"
share    = "$DATA_DIR/share"

[server]
port    = 7777
# token: leave empty = randomly generated on each start; set own value = fixed
token   = ""
# timeout in minutes; 0 = run indefinitely
timeout = 60

[ui]
# theme: auto (follows OS setting), light, dark
theme    = "auto"
# sections to show on startup (can still be toggled at runtime)
upload   = false
download = false
share    = true

[permissions]
# Whether clients (non-local) may delete files in each section
client_delete_upload   = true
client_delete_download = false
client_delete_share    = true
# Whether clients can see the Trash section and restore files from it
client_trash_visible   = false
client_trash_restore   = false

[updates]
# check for new NiceTransfer version on each startup (prints to terminal + UI notification)
check_on_start = true
# notify about available dependency updates (nicegui etc.) — with compatibility warning
notify_deps    = false
# update channel: "stable" (latest release tag) or "rolling" (main branch)
channel        = "stable"
EOF
    echo "✓ config.toml created"
else
    echo "✓ config.toml already exists — not overwritten"
fi

echo
echo "┌─────────────────────────────────────────────┐"
echo "│  Installation complete                      │"
echo "│                                             │"
echo "│  1. Edit config.toml if needed:             │"
echo "│     nano config.toml                        │"
echo "│                                             │"
echo "│  2. Start with:                             │"
echo "│     ./run.sh                                │"
echo "│     ./run.sh --no-upload                    │"
echo "│     ./run.sh --no-download                  │"
echo "│     ./run.sh --port 8888                    │"
echo "└─────────────────────────────────────────────┘"
