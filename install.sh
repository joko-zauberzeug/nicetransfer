#!/usr/bin/env bash
# nicetransfer — installation script
# Ensures uv is available, installs Python + dependencies via uv,
# and generates run.sh and config.toml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"

echo "nicetransfer — Installation"
echo "Directory: $SCRIPT_DIR"
echo

# ── uv ────────────────────────────────────────────────────────────────────────
# uv (https://docs.astral.sh/uv/) manages Python and dependencies.
# It downloads a suitable Python by itself — no preinstalled Python required.

find_uv() {
    command -v uv 2>/dev/null && return
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
        [ -x "$candidate" ] && { echo "$candidate"; return; }
    done
    return 1
}

ask_yn() {
    while true; do
        printf "%s [Y/n] " "$1"
        read -r _ans || return 1
        case "$_ans" in
            [Yy]|[Yy][Ee][Ss]|"") return 0 ;;
            [Nn]|[Nn][Oo])        return 1 ;;
        esac
    done
}

UV="$(find_uv || true)"

if [ -z "$UV" ]; then
    echo "uv is required but not installed."
    if command -v brew &> /dev/null; then
        if ask_yn "→ Install uv via Homebrew (brew install uv)?"; then
            brew install uv
            UV="$(find_uv)"
        fi
    fi
    if [ -z "$UV" ]; then
        echo "  The official installer downloads uv from astral.sh into ~/.local/bin:"
        echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
        if ask_yn "→ Run the official uv installer now?"; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
            UV="$(find_uv)"
        fi
    fi
    if [ -z "$UV" ]; then
        echo "✗ uv not installed. Install it manually and re-run ./install.sh:"
        echo "    https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

echo "✓ uv found ($("$UV" --version))"

# ── Python + dependencies ─────────────────────────────────────────────────────
# uv sync reads pyproject.toml, downloads a suitable Python if none is
# installed, creates .venv, and installs all dependencies.

echo "→ installing Python + dependencies (uv sync) ..."
"$UV" sync --project "$SCRIPT_DIR"
echo "✓ dependencies installed"

# ── run.sh ────────────────────────────────────────────────────────────────────

cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/usr/bin/env bash
# nicetransfer — start script
# Usage: ./run.sh [--no-upload] [--no-download] [--port 8888]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UV="$(command -v uv || { [ -x "$HOME/.local/bin/uv" ] && echo "$HOME/.local/bin/uv"; } || { [ -x "$HOME/.cargo/bin/uv" ] && echo "$HOME/.cargo/bin/uv"; })"
if [ -z "$UV" ]; then
    echo "✗ uv not found — run ./install.sh first" >&2
    exit 1
fi
exec "$UV" run --project "$SCRIPT_DIR" "$SCRIPT_DIR/nicetransfer.py" "$@"
EOF

chmod +x "$SCRIPT_DIR/run.sh"
echo "✓ run.sh created"

# ── config.toml ───────────────────────────────────────────────────────────────

CONFIG_FILE="$SCRIPT_DIR/config.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << EOF
# nicetransfer configuration

[dirs]
# Use absolute paths — relative paths resolve from the working directory, not the project folder.
# Any path set here is accessible to anyone with the token. See Manual for details.
upload   = "$DATA_DIR/upload"
download = "$DATA_DIR/download"
share    = "$DATA_DIR/share"

[server]
# port: 0 = auto-assign from port_range (default); set a fixed value e.g. 7777 for stable bookmarks
port       = 0
port_range = [7700, 7799]
# token: "auto" = randomly generated on each start; set own value = fixed
token   = "auto"
# ip: "auto" = detect the network IP for banner/QR code; set a fixed value
# on multi-homed hosts (VPN, Docker) where detection picks the wrong interface
ip      = "auto"
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
client_shutdown        = false  # clients may shut down the server remotely

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
