# nicetransfer — Manual

Nice and simple local file transfer via browser.

nicetransfer turns any computer into a local file transfer hub. Start it on one device, scan the QR code on any other device on the same Wi-Fi — the browser opens and files can be transferred immediately. Nothing to install on the client side.

## Features

- Three sections: **Upload only**, **Download only**, **Share** (bidirectional)
- Toggle sections on and off at runtime without restarting
- Token-protected access via QR code
- Image preview for JPG, PNG, GIF, WebP, SVG
- Dark / Light / Auto theme
- Detects missing network and shows hotspot setup instructions (macOS, Linux, Windows)
- Live network monitoring — notifies when IP changes or connection drops

---

## Server setup

The server is the computer running nicetransfer.

### Requirements

- macOS or Linux
- Python 3.9+

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

### Starting

```bash
./run.sh                    # All sections active
./run.sh --no-upload        # Download and Share only
./run.sh --no-download      # Upload and Share only
./run.sh --no-share         # Upload and Download only
./run.sh --port 8888        # Custom port
```

### Control panel

Open `http://localhost:7777` on the server device to access the control panel:

- **QR code and network URL** — share with clients or scan directly
- **Section toggles** — enable/disable Upload, Download, Share at runtime
- **Sortable file list** — click column headers to sort
- **Image preview** — click the 🖼 icon next to image files
- **Theme toggle** — Dark / Light / Auto

---

## Client usage

The client is any device that connects to nicetransfer — phone, tablet, or another computer. No installation required.

1. Make sure the device is on the same Wi-Fi network as the server
2. Scan the QR code shown in the server's browser
3. The browser opens with the transfer interface
4. Upload, download, or share files

To connect manually: open the network URL shown on the server (e.g. `http://192.168.x.x:7777/?token=...`) in any browser.

---

## Sections

| Section | Who can upload | Who can download |
|---------|---------------|-----------------|
| **Upload only** | Clients | — |
| **Download only** | — | Clients |
| **Share** | Everyone | Everyone |

---

## No network

If no network connection is found at startup, nicetransfer shows a warning with platform-specific instructions for creating a Wi-Fi hotspot (macOS, Linux, Windows).

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
