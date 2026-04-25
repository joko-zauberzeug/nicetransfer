# nicetransfer — Manual

nicetransfer is a local file transfer tool. It starts a web server on the local network through which files can be transferred between devices — no cloud, no installation on the remote device.

## Requirements

- macOS, Linux
- Python 3.9+
- All devices on the same Wi-Fi network

## Installation

```bash
git clone https://github.com/yourusername/nicetransfer
cd nicetransfer
chmod +x install.sh
./install.sh
```

The installer creates:
- `.venv/` — isolated Python environment
- `config.toml` — configuration file
- `run.sh` — start script

## Configuration

Edit `config.toml` in the project folder:

```toml
[dirs]
upload   = "/path/to/upload-folder"
download = "/path/to/download-folder"
share    = "/path/to/share-folder"

[server]
port  = 7777
token = ""   # empty = randomly generated on each start
```

## Starting

```bash
./run.sh                    # Default (all features active)
./run.sh --no-upload        # Download and Share only
./run.sh --no-download      # Upload and Share only
./run.sh --no-share         # Upload and Download only
./run.sh --port 8888        # Use a different port
```

## Usage

1. Start `./run.sh`
2. Scan the QR code in the browser (localhost:7777) with your smartphone
3. The browser opens on the smartphone with the transfer interface

## Sections

| Section | Function |
|---------|----------|
| **Upload** | Upload files from the device to the server |
| **Download** | Download files from the server |
| **Share** | Bidirectional — everyone can upload and download |

## Control (server device only)

Additional options visible at `localhost:7777`:
- QR code and network URL
- Toggles: enable/disable Upload / Download / Share
- File list sorting

## Security

- Access is token-protected (included in the QR code)
- Token is regenerated on each start (unless set in config.toml)
- Only reachable on the local network
- No internet access, no cloud
