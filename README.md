# nicetransfer

Nice and simple local file transfer via browser.

Start the server, scan the QR code on any device on your network, and transfer files instantly — no cloud, no app, no account.

## How it works

**Server device** — the computer running nicetransfer:
1. Run `./run.sh`
2. Open `http://localhost:7777` — the QR code and control panel appear

**Client device** — any phone, tablet, or computer on the same Wi-Fi:
1. Scan the QR code
2. The browser opens — upload, download, or share files immediately

Nothing to install on the client side.

→ [Full manual](MANUAL.md)

## Features

- Three sections: **Upload**, **Download**, **Share** (bidirectional)
- Toggle sections on and off at runtime
- Token-protected access via QR code
- Image preview for JPG, PNG, GIF, WebP, SVG
- Dark / Light / Auto theme
- Detects missing network and shows hotspot setup instructions

## Requirements

- macOS or Linux
- Python 3.9+
- All devices on the same Wi-Fi network

## Installation

```bash
git clone https://github.com/joko-zauberzeug/nicetransfer
cd nicetransfer
chmod +x install.sh
./install.sh
```

Then start with `./run.sh`.

## Configuration

`install.sh` generates `config.toml` automatically. To customise, edit it:

```toml
[dirs]
upload   = "~/nicetransfer/upload"
download = "~/nicetransfer/download"
share    = "~/nicetransfer/share"

[server]
port  = 7777
token = ""   # empty = randomly generated on each start
```

See `config.toml.example` for a reference template.

## CLI options

```bash
./run.sh --no-upload        # Download and Share only
./run.sh --no-download      # Upload and Share only
./run.sh --no-share         # Upload and Download only
./run.sh --port 8888        # Custom port
```

## Security

- Access is token-protected — the token is embedded in the QR code URL
- Token regenerates on each start unless fixed in `config.toml`
- Local access (`127.0.0.1`) bypasses the token check
- Binds to the local network only — no internet exposure
