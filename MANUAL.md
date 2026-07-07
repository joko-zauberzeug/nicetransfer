# NiceTransfer — Manual

Nice and simple local file transfer via browser.

NiceTransfer turns any computer into a local file transfer hub. Start it on one device, scan the QR code on any other device on the same Wi-Fi — the browser opens and files can be transferred immediately. Nothing to install on the client side.

NiceTransfer is built on [NiceGUI](https://nicegui.io), a Python UI framework by [Zauberzeug GmbH](https://zauberzeug.com).

This manual is organized by audience: client usage first — for anyone connecting to a running NiceTransfer — followed by server setup for whoever runs the instance.

## Features

NiceTransfer is designed for quick, local file exchange — no accounts, no cloud, nothing to install on the receiving end. Features are grouped by who benefits most: general properties of the tool, what clients experience when they connect, and what operators configure and control.

### General

- **Local & offline** — runs on your network, no cloud, no accounts, no internet required
- **No client install** — any device with a browser connects instantly
- **Multiple clients** — several devices can connect and transfer simultaneously
- **Open source** — AGPL v3

### For clients

- **QR code connect** — scan the code shown on the server to open the transfer interface
- **Sections** — Share (bidirectional), Upload only, Download only; which appear depends on configuration
- **Trash** — deleted files moved to trash, not permanently removed; restore or delete forever *(visible to clients if permitted)*
- **Undo delete** — undo bar after each delete batch with a 10-second window to reverse it
- **ZIP download** — select multiple files and download them as a single archive
- **Camera capture** — opens the camera directly on mobile; image picker on desktop *(in upload sections)*
- **Image preview** — inline preview for JPG, PNG, GIF, WebP, SVG
- **Live file list** — updates across all connected devices instantly, no refresh needed
- **Theme** — Auto / Light / Dark, follows OS or set manually

### For operators

- **Section control** — toggle Upload, Download, Share on and off at runtime without restarting
- **Client permissions** — configure per section whether clients may delete files or access Trash
- **Token protection** — access requires a token; regenerates on each start unless fixed in config
- **Session timeout** — configurable auto-shutdown with countdown in the header
- **Updates** — built-in update check and one-click upgrade from the browser
- **Network monitoring** — detects missing network; notifies on IP change or reconnect; hotspot setup instructions for macOS, Linux, Windows
- **Get** — download the source package directly from the running server; no internet or GitHub needed for distribution
- **Changelog** — version history accessible in the browser
- **Development** — architecture overview and project notes, visible on the server device only
- **AI integration** — plain HTTP interface with `llms.txt` discovery; any AI that can fetch a URL can operate NiceTransfer without special client setup

---

## Client usage

The client is any device that connects to NiceTransfer — phone, tablet, or another computer. Just a browser and a QR scanner — no account, no extra apps.

1. Make sure the device is on the same Wi-Fi network as the server
2. Scan the QR code shown in the server's browser
3. The browser opens with the transfer interface
4. Upload, download, or share files

To connect manually: open the network URL shown on the server (e.g. `http://192.168.x.x:<port>/?token=...`) in any browser.

---

## Sections

Each section controls which operations are available.

| Section | Upload | Download | Delete |
|---------|--------|----------|--------|
| **Share** | ✓ | ✓ | server always; clients if permitted |
| **Upload only** | ✓ | — | server always; clients if permitted |
| **Download only** | — | ✓ | server always; clients if permitted |
| **Trash** | — | — | restore or delete forever |

Sections can be enabled or disabled at runtime via the control panel without restarting the server. Deleted files are always moved to Trash first — nothing is removed immediately.

---

## Working with files

- **Sortable file list** — click column headers to sort by name, size, or date
- **Multi-file selection** — checkboxes in the file list; top checkbox selects or deselects all
- **ZIP download** — select files and click the download icon in the table header
- **Per-file download** — click the download icon next to any file
- **Delete** — select files and click the trash icon to move them to Trash
- **Undo** — an undo bar appears immediately after deletion; click **Undo** within 10 seconds to restore the batch, or ✕ to dismiss early
- **Image preview** — click the image icon next to image files to preview in the browser *(only in sections where download is enabled)*

---

## Server setup

The server is the computer running NiceTransfer. Run it on a local, trusted network only — NiceTransfer uses HTTP (not HTTPS) and the token mechanism is not designed for internet exposure.

### Requirements

- macOS or Linux
- [uv](https://docs.astral.sh/uv/) — `./install.sh` offers to install it if missing (via Homebrew or the official installer, after asking)

No preinstalled Python required — uv downloads a suitable Python version and all dependencies (including NiceGUI) automatically.

### Installation

```bash
git clone https://github.com/joko-zauberzeug/nicetransfer
cd nicetransfer
chmod +x install.sh
./install.sh
```

The installer creates:
- `.venv/` — isolated Python environment (managed by uv)
- `config.toml` — configuration file
- `run.sh` — start script

### Configuration

Edit `config.toml`:

```toml
[dirs]
upload   = "/path/to/upload-folder"
download = "/path/to/download-folder"
share    = "/path/to/share-folder"

[server]
port       = 0              # 0 = auto-assign from port_range; e.g. 7777 for a fixed port
port_range = [7700, 7799]  # range used when port = 0
token      = "auto"        # auto = randomly generated on each start; set own value = fixed
ip         = "auto"        # auto = detect network IP; fixed value for multi-homed hosts (VPN, Docker)
timeout    = 60            # minutes until auto-shutdown; 0 = run indefinitely

[ui]
theme    = "auto"   # auto (follows OS), light, dark
upload   = false    # show Upload section on startup
download = false    # show Download section on startup
share    = true     # show Share section on startup

[permissions]
client_delete_upload   = true   # clients may delete files in Upload only
client_delete_download = false  # clients may delete files in Download only
client_delete_share    = true   # clients may delete files in Share
client_trash_visible   = false  # clients can see the Trash section
client_trash_restore   = false  # clients can restore files from Trash
client_shutdown        = false  # clients may shut down the server remotely
```

By default, clients can delete in Upload and Share sections; Download deletion, Trash access, and remote shutdown remain restricted. The server device always has full access regardless of these settings.

**Directory paths** — use absolute paths (e.g. `/Users/alice/transfers`). Relative paths are resolved from the working directory where `./run.sh` is called, not from the project folder — this can lead to unexpected locations if you start NiceTransfer from a different directory. Paths support `~/` expansion. Any directory configured here is fully accessible to anyone who has the token, so only point to folders you intend to share.

To customize colors and other visual details, edit `nicetransfer.css`.

### Starting

```bash
./run.sh                    # Start with settings from config.toml
./run.sh --no-upload        # Disable Upload section (overrides config)
./run.sh --no-download      # Disable Download section (overrides config)
./run.sh --no-share         # Disable Share section (overrides config)
./run.sh --port 8888        # Custom port
./run.sh --no-open          # Do not open the browser on startup
./run.sh --ip 192.168.1.20  # Fixed IP for network URL and QR code
```

**When to set a fixed IP:** On machines with several network interfaces (VPN active, Docker installed), the automatic detection follows the default route and may pick an address other devices cannot reach — the QR code then points nowhere. Set `ip` in `config.toml` (or use `--ip`) to the address of the network your other devices are on. The server always listens on all interfaces; this setting only controls which address is shown and encoded in the QR code.

The default sections and theme are read from `config.toml`. Command-line flags always take precedence over the config file.

### Stopping

**Ctrl+C** in the terminal where `./run.sh` is running triggers a clean shutdown — NiceGUI lifecycle is respected, no warnings.

To stop remotely (e.g. from a script or AI client):

```bash
curl -s -X POST "http://127.0.0.1:<port>/shutdown?token=<token>"
```

The token is shown in the startup banner. As a last resort:

```bash
pkill -f nicetransfer.py
```

### Upgrading

The easiest way is via the **Control panel → Updates** section in the browser. Click **Check** to see if a new version is available, then **Upgrade** to apply it automatically. NiceTransfer restarts itself after a successful upgrade.

From the terminal (with interactive review):

```bash
./upgrade.sh
```

The upgrade script detects whether NiceTransfer was installed via `git clone` or as a source download and handles both cases:

- **Git install** — runs `git pull`, then optionally upgrades dependencies
- **Standalone install** — downloads the latest version from GitHub, shows a diff for each changed file, and asks what to update

For each change you can choose: **Y** (apply), **N** (skip), or **D** (show diff first). `run.sh` is handled separately and regenerated only if needed.

```bash
./upgrade.sh --yes    # apply all updates without prompting
./upgrade.sh --check  # print available updates as JSON (for scripts/GUI)
```

To check for updates automatically on each start, enable it in `config.toml`:

```toml
[updates]
check_on_start = true     # prints to terminal if a new version is available
notify_deps    = true     # also checks nicegui and other dependencies
channel        = "stable" # "stable" (latest release) or "rolling" (main branch)
```

**Note on dependency updates:** NiceTransfer is tested with the dependency versions installed at release time. Upgrading dependencies independently may introduce incompatibilities — `upgrade.sh` will warn you before doing so.

### Control panel

Open the local URL shown in the banner (e.g. `http://127.0.0.1:<port>/?token=...`) on the server device. The page opens with a full-screen hero showing the QR code. Scroll down to reach the control panel and file sections.

The menu (top right) gives access to **Manual**, **Changelog**, **Get** (source download), and — on the server device — **Development** (architecture overview and project notes for developers).

**Connection** — QR code and network URL; scan with any device on the same Wi-Fi to connect.

**Control** — runtime settings:

- **Section toggles** — enable/disable Upload, Download, Share at runtime
- **Client permissions** — grant clients the ability to delete files per section, see Trash, restore from Trash, or shut down the server
- **Session timeout** — set a timeout in minutes and click **Set** to start or restart the countdown; set to 0 to disable; a countdown appears under the logo in the header when a timeout is active
- **Updates** — shows installed versions of NiceTransfer and NiceGUI; click **Check** to check for updates; if an update is available, click **Upgrade** to apply it and restart automatically
- **Theme toggle** — Auto / Light / Dark

**Trash** — shows all deleted files with their original name and source section:

- Select files and click **Restore** (↩) to move them back to their original section
- Select files and click **Delete forever** (🗑) to remove them permanently
- Files in Trash do not count toward section file lists

---

## No network

If no network connection is found at startup, NiceTransfer shows a warning with platform-specific instructions for creating a Wi-Fi hotspot (macOS, Linux, Windows).

While running, the network is checked every 5 seconds. A notification appears in the terminal and browser if:

- **Network lost** — clients are disconnected
- **Reconnected, same IP** — clients should reconnect automatically
- **Reconnected, new IP** — clients must rescan the QR code

---

## AI integration

NiceTransfer's primary AI interface is **plain HTTP + `llms.txt`** — no MCP client, no special setup required. Any AI that can fetch a URL and read text can operate NiceTransfer.

### Working with an AI assistant

An AI assistant running on the server device (e.g. Claude Code) can start, operate, and stop NiceTransfer entirely through the HTTP interface. For this to work reliably, the right phrases matter — some instructions trigger the correct behavior, others do not.

**Starting NiceTransfer**

Tell the AI explicitly which script to run:

> "Start NiceTransfer with `./run.sh`"

Do not just say "start NiceTransfer" — the AI may guess wrong. After starting, the AI should read the `llms+` URL from the banner output automatically. If it does not, say:

> "Fetch the `llms+` URL from the banner and read it completely"

**Getting the AI to read a URL (not open a browser)**

There is an important difference between opening a URL and visiting it:

- ❌ "Open the local URL" → opens a browser window; the AI reads nothing
- ❌ "Show me the site" → same result
- ✓ "Visit the local URL" → the AI fetches the page and reads the HTML
- ✓ "Fetch `llms+` and read it completely" → the AI fetches and reads the full operating instructions

**Phrases that work reliably**

| What you want | Say this |
|---|---|
| Start NiceTransfer | "Start NiceTransfer with `./run.sh`" |
| Read operating instructions | "Fetch `llms+` from the banner and read it completely" |
| List files | "List the files in share" (or upload / download) |
| Upload a file | "Upload this file to share" |
| Download a file | "Download `filename` from share" |
| Check for updates | "Check for updates" |
| Shut down | "Shut down NiceTransfer" |
| Explain a feature | "Read the manual and explain how sections work" |

**What the AI cannot do**

Operator controls — section toggles, permissions, timeout — are only available in the browser Control panel. The AI works within whatever is currently configured; it cannot reconfigure the server. If a section is disabled, the AI will get a 404, just like a human client.

Every page embeds discovery hints in the HTML `<head>`:

```html
<meta name="llms-txt"             content="http://192.168.x.x:<port>/llms.txt?token=...">
<!-- on the server device (localhost): points to llms-local.txt instead -->
<meta name="llms-txt-instruction" content="fetch and read completely before acting — do not truncate, summarize, stop early, or read partially">
<meta name="nicetransfer-manual"  content="http://...:<port>/manual.md?token=... — user manual; fetch and read completely — do not truncate, summarize, stop early, or read partially — when asked how NiceTransfer works, how to use a feature, or for section explanations">
<meta name="mcp-server"           content="http://192.168.x.x:<port>/mcp?token=...">
<meta name="mcp-server-card"      content="http://192.168.x.x:<port>/.well-known/mcp/server-card.json?token=...">
```

### llms.txt — the AI entry point

Fetch `/llms.txt?token=...` to get the complete operating instructions: all available HTTP endpoints, what they do, and how to call them. The AI uses these endpoints directly — no guessing, no training-data assumptions.

### HTTP endpoints for AI

All endpoints require `?token=TOKEN`. Key operations:

| Endpoint | What it does |
|----------|--------------|
| `GET /status` | Server state: active sections, client permissions, auto-shutdown countdown |
| `GET /files/{section}` | List files with download URLs (section: share, upload, download, trash) |
| `POST /upload/{section}` | Upload a file (multipart/form-data, field: `file`) |
| `GET /download/{section}/{filename}` | Download a file |
| `DELETE /files/{section}/{filename}` | Move a file to trash |
| `POST /restore/{trash_name}` | Restore a file from trash |
| `DELETE /trash/{trash_name}` | Permanently delete a file from trash *(server only)* |
| `POST /shutdown` | Shut down the server cleanly |
| `POST /check-updates` | Check for NiceTransfer and NiceGUI updates |
| `GET /manual.md` | This manual as plain text |
| `GET /changelog.md` | Version history as plain text |
| `GET /development.md` | Development guide as plain text *(server only)* |

Client permissions (delete, trash access, shutdown) apply to remote AI clients exactly as they do to human clients — configured in the Control panel.

### MCP (optional)

An MCP server is available at `/mcp` for AI clients with native MCP support. It covers the same operations as the HTTP interface. See `/llms.txt` for details.

---

## Security

- Access is token-protected everywhere — browser, downloads, previews, AI discovery endpoints
- Token regenerates on each start unless a fixed value is set in `config.toml`
- The server only binds to the local network — no internet exposure
