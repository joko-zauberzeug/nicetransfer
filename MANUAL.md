# NiceTransfer — Manual

Nice and simple local file transfer via browser.

NiceTransfer turns any computer into a local file transfer hub. Start it on one device, scan the QR code on any other device on the same Wi-Fi — the browser opens and files can be transferred immediately. Nothing to install on the client side.

NiceTransfer is built on [NiceGUI](https://nicegui.io), a Python UI framework by [Zauberzeug GmbH](https://zauberzeug.com).

## Features

- Three file sections: **Share** (bidirectional), **Upload only**, **Download only**
- **Trash** section — deleted files are moved to trash, not permanently removed; restore or delete forever per selection
- Toggle sections on and off at runtime without restarting
- Select multiple files and download them as a ZIP archive
- Delete selected files — moves them to Trash; server always has this capability, clients only when permitted
- **Undo last delete** — an undo bar appears after each delete batch with a 10-second window to reverse it; per-section, per-client, works regardless of Trash visibility
- **Camera capture** — "Take photo" button in upload sections opens the camera directly on mobile; image picker on desktop
- File list updates live across all connected devices — no manual refresh needed
- Token-protected access via QR code
- Image preview for JPG, PNG, GIF, WebP, SVG
- Auto / Light / Dark theme
- Detects missing network and shows hotspot setup instructions (macOS, Linux, Windows)
- Live network monitoring — notifies when IP changes or connection drops

---

## Server setup

The server is the computer running NiceTransfer.

### Requirements

- macOS or Linux
- Python 3.9+

All other dependencies (including NiceGUI) are installed automatically by `./install.sh`.

### Installation

```bash
git clone https://github.com/joko-zauberzeug/nicetransfer
cd nicetransfer
chmod +x install.sh
./install.sh
```

The installer creates:
- `.venv/` — isolated Python environment
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
port    = 7777
token   = ""   # empty = randomly generated on each start
timeout = 60   # minutes until auto-shutdown; 0 = run indefinitely

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
```

By default, clients can delete in Upload and Share sections; Download deletion and Trash access remain restricted. The server device always has full delete and trash access regardless of these settings.

To customize colors and other visual details, edit `nicetransfer.css`.

### Starting

```bash
./run.sh                    # Start with settings from config.toml
./run.sh --no-upload        # Disable Upload section (overrides config)
./run.sh --no-download      # Disable Download section (overrides config)
./run.sh --no-share         # Disable Share section (overrides config)
./run.sh --port 8888        # Custom port
```

The default sections and theme are read from `config.toml`. Command-line flags always take precedence over the config file.

### Stopping

```bash
pkill -f nicetransfer.py
```

### Control panel

Open the local URL shown in the banner (e.g. `http://127.0.0.1:7777/?token=...`) on the server device. The page opens with a full-screen hero showing the QR code. Scroll down to reach the control panel and file sections.

**Connection** — QR code and network URL; scan with any device on the same Wi-Fi to connect.

**Control** — runtime settings:

- **Section toggles** — enable/disable Upload, Download, Share at runtime
- **Client permissions** — grant clients the ability to delete files per section, see Trash, or restore from Trash
- **Session timeout** — set a timeout in minutes and click **Set** to start or restart the countdown; set to 0 to disable; a countdown appears under the logo in the header when a timeout is active
- **Sortable file list** — click column headers to sort
- **Multi-file selection** — checkboxes in the file list; top checkbox selects all
- **ZIP download** — select files and click the download icon in the table header
- **Delete** — select files and click the trash icon to move them to Trash
- **Undo** — an undo bar appears immediately after deletion; click **Undo** within 10 seconds to restore the batch, or ✕ to dismiss early
- **Image preview** — click the image icon next to image files to preview in the browser
- **Per-file download** — click the download icon next to any file
- **Theme toggle** — Auto / Light / Dark

**Trash** — shows all deleted files with their original name and source section:

- Select files and click **Restore** (↩) to move them back to their original section
- Select files and click **Delete forever** (🗑) to remove them permanently
- Files in Trash do not count toward section file lists

---

## Client usage

The client is any device that connects to NiceTransfer — phone, tablet, or another computer. No installation required.

1. Make sure the device is on the same Wi-Fi network as the server
2. Scan the QR code shown in the server's browser
3. The browser opens with the transfer interface
4. Upload, download, or share files

To connect manually: open the network URL shown on the server (e.g. `http://192.168.x.x:7777/?token=...`) in any browser.

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

## No network

If no network connection is found at startup, NiceTransfer shows a warning with platform-specific instructions for creating a Wi-Fi hotspot (macOS, Linux, Windows).

While running, the network is checked every 5 seconds. A notification appears in the terminal and browser if:

- **Network lost** — clients are disconnected
- **Reconnected, same IP** — clients should reconnect automatically
- **Reconnected, new IP** — clients must rescan the QR code

---

## AI integration

NiceTransfer embeds AI discovery hints in every page. When an AI app (e.g. Claude) scans the QR code and fetches the URL, it finds the following in the HTML `<head>`:

```html
<meta name="mcp-server"      content="http://192.168.x.x:7777/mcp?token=...">
<meta name="mcp-server-card" content="http://192.168.x.x:7777/.well-known/mcp/server-card.json?token=...">
<meta name="llms-txt"        content="http://192.168.x.x:7777/llms.txt?token=...">
```

Two additional endpoints are available (both token-protected):

| Endpoint | Content |
|----------|---------|
| `/.well-known/mcp/server-card.json` | Machine-readable capability description (JSON) |
| `/llms.txt` | Plain-text description of tools and API for AI assistants |

The MCP endpoint (`/mcp`) is not yet implemented — the discovery layer is in place for when it is.

---

## Security

- Access is token-protected everywhere — browser, downloads, previews, AI discovery endpoints
- Token regenerates on each start unless a fixed value is set in `config.toml`
- The server only binds to the local network — no internet exposure
