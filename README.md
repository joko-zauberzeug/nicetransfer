# nicetransfer

Local file transfer via browser — no cloud, no app, no account.

Start a web server on your local network, scan a QR code on any device, and transfer files instantly over Wi-Fi.

## Features

- Upload, download, or share files via any browser
- QR code for instant access from mobile devices
- Token-protected access (included in the QR code)
- Three independent sections: Upload / Download / Share
- Toggle sections on and off without restarting
- Dark / light / auto theme
- Image preview for JPG, PNG, GIF, WebP, SVG
- No internet required — local network only

## Requirements

- macOS or Linux
- Python 3.9+
- All devices on the same Wi-Fi network

## Installation

```bash
git clone https://github.com/yourusername/nicetransfer
cd nicetransfer
chmod +x install.sh
./install.sh
```

This creates:
- `.venv/` — isolated Python environment
- `config.toml` — local configuration (from `config.toml.example`)
- `run.sh` — start script with correct paths

## Configuration

`install.sh` generates `config.toml` automatically pointing to `./data/`. To customise, edit `config.toml`:

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

## Usage

```bash
./run.sh                    # All sections active
./run.sh --no-upload        # Download and Share only
./run.sh --no-download      # Upload and Share only
./run.sh --no-share         # Upload and Download only
./run.sh --port 8888        # Custom port
```

1. Run `./run.sh`
2. Open `http://localhost:7777` in your browser
3. Scan the QR code with your phone — the browser opens with the transfer interface
4. Transfer files

## Sections

| Section | Description |
|---------|-------------|
| **Upload** | Remote devices upload files to the server |
| **Download** | Remote devices download files from the server |
| **Share** | Bidirectional — upload and download for everyone |

The server device (`localhost`) also sees a control panel with toggles to enable/disable each section at runtime.

## Security

- Access is token-protected; the token is embedded in the QR code URL
- Token is regenerated on each start unless a fixed value is set in `config.toml`
- Local access (`127.0.0.1`) bypasses the token check
- The server only binds to the local network — no internet exposure
