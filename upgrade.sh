#!/usr/bin/env bash
# nicetransfer upgrade script
# Usage: ./upgrade.sh [--yes] [--check]
#   --yes    non-interactive, apply all updates
#   --check  output JSON status and exit (for GUI use)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
GITHUB_REPO="joko-zauberzeug/nicetransfer"
API_BASE="https://api.github.com/repos/$GITHUB_REPO"
RAW_BASE="https://raw.githubusercontent.com/$GITHUB_REPO"

YES_ALL=false
CHECK_ONLY=false
CHANNEL_ARG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --yes|-y)     YES_ALL=true ;;
        --check)      CHECK_ONLY=true ;;
        --channel=*)  CHANNEL_ARG="${1#--channel=}" ;;
        --channel)    shift; CHANNEL_ARG="$1" ;;
    esac
    shift
done

# Read channel from config.toml, override with --channel flag if given
CHANNEL=$(python3 -c "
import sys
try:
    import tomllib
except ImportError:
    try: import tomli as tomllib
    except ImportError: tomllib = None
if tomllib:
    try:
        with open('$SCRIPT_DIR/config.toml', 'rb') as f:
            print(tomllib.load(f).get('updates', {}).get('channel', 'stable'))
        sys.exit()
    except Exception: pass
# fallback: grep
import re, pathlib
txt = pathlib.Path('$SCRIPT_DIR/config.toml').read_text()
m = re.search(r'channel\s*=\s*\"([^\"]+)\"', txt)
print(m.group(1) if m else 'stable')
" 2>/dev/null || echo "stable")
[ -n "$CHANNEL_ARG" ] && CHANNEL="$CHANNEL_ARG"
echo "Channel       : $CHANNEL"

# ── helpers ───────────────────────────────────────────────────────────────────

ask_ynd() {
    # Prompt with [Y/n/d]; echoes "y", "n", or "d"
    $YES_ALL && { echo "y"; return; }
    while true; do
        printf "%s [Y/n/d] " "$1"
        read -r _ans
        case "${_ans,,}" in
            y|yes|"") echo "y"; return ;;
            n|no)     echo "n"; return ;;
            d|diff)   echo "d"; return ;;
        esac
    done
}

ask_yn() {
    $YES_ALL && return 0
    while true; do
        printf "%s [Y/n] " "$1"
        read -r _ans
        case "${_ans,,}" in
            y|yes|"") return 0 ;;
            n|no)     return 1 ;;
        esac
    done
}

extract_version() {
    grep -E '^VERSION\s*=' "$1" | head -1 | sed 's/.*"\(.*\)".*/\1/'
}

# ── local version ─────────────────────────────────────────────────────────────

if [ ! -f "$SCRIPT_DIR/nicetransfer.py" ]; then
    echo "✗ nicetransfer.py not found in $SCRIPT_DIR" >&2
    exit 1
fi

LOCAL_VERSION=$(extract_version "$SCRIPT_DIR/nicetransfer.py")
echo "Local version : v$LOCAL_VERSION"

# ── latest version from GitHub ────────────────────────────────────────────────

if [ "$CHANNEL" = "rolling" ]; then
    LATEST_REF="main"
    RAW_URL="$RAW_BASE/main"
    LATEST_VERSION=$(curl -sf "$RAW_URL/nicetransfer.py" 2>/dev/null \
        | grep -E '^VERSION\s*=' | head -1 | sed 's/.*"\(.*\)".*/\1/' \
        || echo "unknown")
else
    LATEST_REF=$(curl -sf "$API_BASE/tags" 2>/dev/null \
        | python3 -c "import sys,json; tags=json.load(sys.stdin); print(tags[0]['name'] if tags else '')" \
        2>/dev/null || echo "")
    if [ -n "$LATEST_REF" ]; then
        LATEST_VERSION="${LATEST_REF#v}"
        RAW_URL="$RAW_BASE/$LATEST_REF"
    else
        LATEST_REF="main"
        RAW_URL="$RAW_BASE/main"
        LATEST_VERSION=$(curl -sf "$RAW_URL/nicetransfer.py" 2>/dev/null \
            | grep -E '^VERSION\s*=' | head -1 | sed 's/.*"\(.*\)".*/\1/' \
            || echo "unknown")
    fi
fi

echo "Latest version: v$LATEST_VERSION ($LATEST_REF)"

# ── dependency versions ───────────────────────────────────────────────────────

INSTALLED_NICEGUI=$("$VENV/bin/pip" show nicegui 2>/dev/null \
    | grep '^Version:' | awk '{print $2}' || echo "unknown")
LATEST_NICEGUI=$(curl -sf "https://pypi.org/pypi/nicegui/json" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])" \
    2>/dev/null || echo "unknown")

# ── --check mode (JSON for GUI) ───────────────────────────────────────────────

if $CHECK_ONLY; then
    python3 -c "
import json
print(json.dumps({
    'nt':     {'local': '$LOCAL_VERSION',      'latest': '$LATEST_VERSION',  'update': '$LOCAL_VERSION' != '$LATEST_VERSION'},
    'nicegui':{'local': '$INSTALLED_NICEGUI',  'latest': '$LATEST_NICEGUI',  'update': '$INSTALLED_NICEGUI' != '$LATEST_NICEGUI'},
}, indent=2))
"
    exit 0
fi

# ── check if anything to do ───────────────────────────────────────────────────

if [ "$LOCAL_VERSION" = "$LATEST_VERSION" ]; then
    echo "NiceTransfer is up to date."
else
    echo ""
    echo "Update available: v$LOCAL_VERSION → v$LATEST_VERSION"
    echo ""

    # ── source files ─────────────────────────────────────────────────────────

    IS_GIT=false
    [ -d "$SCRIPT_DIR/.git" ] && IS_GIT=true

    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT

    if $IS_GIT; then
        echo "Git install detected."
        git -C "$SCRIPT_DIR" fetch --quiet origin

        CHANGED=$(git -C "$SCRIPT_DIR" diff HEAD..origin/main --name-only 2>/dev/null || echo "")
        if [ -n "$CHANGED" ]; then
            echo "Changed files:"
            echo "$CHANGED" | sed 's/^/  /'
        fi
        echo ""

        _resp=$(ask_ynd "Apply git pull?")
        while [ "$_resp" = "d" ]; do
            git -C "$SCRIPT_DIR" diff HEAD..origin/main || true
            _resp=$(ask_ynd "Apply git pull?")
        done
        if [ "$_resp" = "y" ]; then
            git -C "$SCRIPT_DIR" pull --quiet origin main
            echo "✓ source updated"
        else
            echo "  source update skipped"
        fi

    else
        echo "Standalone install (no .git) — downloading from GitHub..."
        _ref_type=$( [ "$LATEST_REF" = "main" ] && echo "heads/main" || echo "tags/$LATEST_REF" )
        ZIP_URL="https://github.com/$GITHUB_REPO/archive/refs/$_ref_type.zip"
        curl -sfL "$ZIP_URL" -o "$TMP/nt.zip"
        unzip -q "$TMP/nt.zip" -d "$TMP/src"
        EXTRACT_DIR=$(find "$TMP/src" -maxdepth 1 -mindepth 1 -type d | head -1)

        UPDATE_FILES=(nicetransfer.py nicetransfer.css install.sh upgrade.sh
                      MANUAL.md CHANGELOG.md README.md LICENSE)

        for f in "${UPDATE_FILES[@]}"; do
            SRC="$EXTRACT_DIR/$f"
            DST="$SCRIPT_DIR/$f"
            [ -f "$SRC" ] || continue

            if [ -f "$DST" ] && diff -q "$SRC" "$DST" > /dev/null 2>&1; then
                echo "  unchanged : $f"
                continue
            fi

            echo ""
            [ -f "$DST" ] && echo "Modified  : $f" || echo "New file  : $f"
            _resp=$(ask_ynd "Update $f?")
            while [ "$_resp" = "d" ]; do
                diff "$DST" "$SRC" || true
                echo ""
                _resp=$(ask_ynd "Update $f?")
            done
            if [ "$_resp" = "y" ]; then
                cp "$SRC" "$DST"
                echo "  ✓ updated : $f"
            else
                echo "    skipped : $f"
            fi
        done

        # fonts directory
        if [ -d "$EXTRACT_DIR/fonts" ]; then
            cp -r "$EXTRACT_DIR/fonts/." "$SCRIPT_DIR/fonts/"
            echo "  ✓ updated : fonts/"
        fi
    fi

    # ── run.sh ────────────────────────────────────────────────────────────────

    EXPECTED_RUN="$(cat <<RUNEOF
#!/usr/bin/env bash
# nicetransfer — start script
# Usage: ./run.sh [--no-upload] [--no-download] [--port 8888]

source "$VENV/bin/activate"
python3 "$SCRIPT_DIR/nicetransfer.py" "\$@"
RUNEOF
)"

    if [ -f "$SCRIPT_DIR/run.sh" ]; then
        CURRENT_RUN=$(cat "$SCRIPT_DIR/run.sh")
        if [ "$CURRENT_RUN" = "$EXPECTED_RUN" ]; then
            echo "  unchanged : run.sh"
        else
            echo ""
            echo "run.sh has changed."
            _resp=$(ask_ynd "Regenerate run.sh?")
            while [ "$_resp" = "d" ]; do
                diff <(echo "$CURRENT_RUN") <(echo "$EXPECTED_RUN") || true
                echo ""
                _resp=$(ask_ynd "Regenerate run.sh?")
            done
            if [ "$_resp" = "y" ]; then
                printf '%s\n' "$EXPECTED_RUN" > "$SCRIPT_DIR/run.sh"
                chmod +x "$SCRIPT_DIR/run.sh"
                echo "  ✓ updated : run.sh"
            else
                echo "    skipped : run.sh"
            fi
        fi
    else
        printf '%s\n' "$EXPECTED_RUN" > "$SCRIPT_DIR/run.sh"
        chmod +x "$SCRIPT_DIR/run.sh"
        echo "  ✓ created : run.sh"
    fi
fi

# ── dependencies ──────────────────────────────────────────────────────────────

echo ""
echo "Checking dependencies..."
echo "  nicegui: installed=$INSTALLED_NICEGUI  latest=$LATEST_NICEGUI"

if [ "$INSTALLED_NICEGUI" != "$LATEST_NICEGUI" ] && [ "$LATEST_NICEGUI" != "unknown" ]; then
    echo ""
    echo "  ⚠  NiceGUI $LATEST_NICEGUI is available (installed: $INSTALLED_NICEGUI)"
    echo "     NiceTransfer v$LOCAL_VERSION was tested with the installed version."
    echo "     Upgrading may introduce incompatibilities."
    echo ""
    if ask_yn "  Upgrade nicegui to $LATEST_NICEGUI?"; then
        "$VENV/bin/pip" install --quiet --upgrade nicegui
        echo "  ✓ nicegui upgraded to $LATEST_NICEGUI"
    else
        echo "    dependency upgrade skipped"
    fi
else
    echo "  ✓ nicegui is up to date"
fi

# ── done ──────────────────────────────────────────────────────────────────────

echo ""
echo "┌──────────────────────────────────────────────────────┐"
echo "│  Upgrade complete                                    │"
echo "│                                                      │"
echo "│  Restart NiceTransfer to apply:                      │"
echo "│    pkill -f nicetransfer.py && ./run.sh              │"
echo "└──────────────────────────────────────────────────────┘"
