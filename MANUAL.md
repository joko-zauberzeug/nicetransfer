# NiceTransfer — Manual

Nice and simple local file transfer via browser.

NiceTransfer turns any computer into a local file transfer hub. Start it on one device, scan the QR code on any other device on the same Wi-Fi — the browser opens and files can be transferred immediately. Nothing to install on the client side.

NiceTransfer is built on [NiceGUI](https://nicegui.io) by Zauberzeug GmbH.

## Features

- Three sections: **Upload only**, **Download only**, **Share** (bidirectional)
- Toggle sections on and off at runtime without restarting
- Select multiple files and download them as a ZIP archive
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
port  = 7777
token = ""   # empty = randomly generated on each start

[ui]
theme    = "auto"   # auto (follows OS), light, dark
upload   = false    # show Upload section on startup
download = false    # show Download section on startup
share    = true     # show Share section on startup
```

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

### Control panel

Open `http://localhost:7777` on the server device to access the control panel:

- **QR code and network URL** — share with clients or scan directly
- **Section toggles** — enable/disable Upload, Download, Share at runtime
- **Sortable file list** — click column headers to sort
- **Multi-file selection** — checkboxes in the file list; top checkbox selects all
- **ZIP download** — select files and click the download icon in the table header
- **Image preview** — click the image icon next to image files to preview in the browser
- **Per-file download** — click the download icon next to any file
- **Theme toggle** — Auto / Light / Dark

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

Each section controls which operations are available. All connected devices — including the server — have equal access.

| Section | Upload | Download |
|---------|--------|----------|
| **Upload only** | ✓ | — |
| **Download only** | — | ✓ |
| **Share** | ✓ | ✓ |

Sections can be enabled or disabled at runtime via the control panel without restarting the server.

---

## No network

If no network connection is found at startup, NiceTransfer shows a warning with platform-specific instructions for creating a Wi-Fi hotspot (macOS, Linux, Windows).

While running, the network is checked every 5 seconds. A notification appears in the terminal and browser if:

- **Network lost** — clients are disconnected
- **Reconnected, same IP** — clients should reconnect automatically
- **Reconnected, new IP** — clients must rescan the QR code

---

## Security

- Access is token-protected — the token is embedded in the QR code URL
- Token regenerates on each start unless a fixed value is set in `config.toml`
- Local access (`127.0.0.1`) does not require a token
- The server only binds to the local network — no internet exposure
