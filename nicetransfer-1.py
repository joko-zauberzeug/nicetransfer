#!/usr/bin/env python3
"""
nicetransfer — local file transfer via browser
https://github.com/yourusername/nicetransfer  (placeholder)

Modes:
    python3 nicetransfer.py --mode up    --dir ~/destination
    python3 nicetransfer.py --mode down  --dir ~/source
    python3 nicetransfer.py --mode share --dir ~/folder
    python3 nicetransfer.py --mode share --dir ~/folder --port 7777

Dependencies are checked and installed automatically on startup.
"""

# ── 0. Stdlib-only imports (immer verfügbar) ──────────────────────────────────
import sys
import subprocess
import importlib
import socket
import secrets
import argparse
from pathlib import Path
from datetime import datetime


# ── 1. Dependency-Check ───────────────────────────────────────────────────────

REQUIRED = {
    "nicegui": ("nicegui", ">=1.4"),   # import-name, version-hint
    "qrcode":  ("qrcode",  ">=7.0"),
    "Pillow":  ("PIL",     ">=9.0"),   # qrcode[svg] braucht Pillow für PNG-Fallback
}

def _pkg_installed(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False

def _install(pkg_spec: str):
    print(f"  → installing {pkg_spec} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg_spec, "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ✗ Error installing {pkg_spec}:")
        print(result.stderr)
        sys.exit(1)
    print(f"  ✓ {pkg_spec} installed")

def check_dependencies():
    missing = []
    for pip_name, (import_name, _) in REQUIRED.items():
        if not _pkg_installed(import_name):
            missing.append(pip_name)

    # qrcode braucht svg-extra
    if "qrcode" in missing:
        missing.remove("qrcode")
        missing.append("qrcode[svg]")

    if missing:
        print("nicetransfer: installing missing dependencies:")
        for pkg in missing:
            _install(pkg)
        print()

check_dependencies()


# ── 2. Imports nach Dependency-Check ─────────────────────────────────────────
from nicegui import ui, app, events   # noqa: E402

try:
    import qrcode
    import qrcode.image.svg
    import io
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ── 3. CLI-Argumente ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="nicetransfer — local file transfer via browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  up     Upload only  (others can upload files to this machine)
  down   Download only (others can download files from this machine)
  share  Bidirectional — upload and download, token-protected

Examples:
  python3 nicetransfer.py --mode up --dir ~/photogrammetry/images
  python3 nicetransfer.py --mode share --dir ~/project-folder --port 7777
        """
    )
    p.add_argument("--mode", choices=["up", "down", "share"], default="share",
                   help="Operation mode (default: share)")
    p.add_argument("--dir", type=Path, default=Path("./nicetransfer"),
                   help="Target/source folder (default: ./nicetransfer)")
    p.add_argument("--port", type=int, default=7777,
                   help="Port (default: 7777)")
    p.add_argument("--no-token", action="store_true",
                   help="Do not require token in share mode (less secure)")
    return p.parse_args()

ARGS = parse_args()
TARGET_DIR: Path = ARGS.dir.expanduser().resolve()
TARGET_DIR.mkdir(parents=True, exist_ok=True)
MODE: str = ARGS.mode
PORT: int = ARGS.port
USE_TOKEN: bool = (MODE == "share") and (not ARGS.no_token)
TOKEN: str = secrets.token_urlsafe(12) if USE_TOKEN else ""


# ── 4. Hilfsfunktionen ────────────────────────────────────────────────────────

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:{PORT}"
ACCESS_URL = f"{BASE_URL}/?token={TOKEN}" if USE_TOKEN else BASE_URL

def make_qr_svg(url: str) -> str:
    if not HAS_QR:
        return ""
    try:
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(url, image_factory=factory, box_size=7, border=2)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception:
        return ""

QR_SVG = make_qr_svg(ACCESS_URL)

def file_entries() -> list[dict]:
    try:
        files = sorted(
            [f for f in TARGET_DIR.iterdir() if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
    except Exception:
        return []
    result = []
    for f in files:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 ** 2:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size/1024**2:.1f} MB"
        result.append({"name": f.name, "size": size_str, "time": mtime, "path": f})
    return result

def save_upload(e: events.UploadEventArguments) -> Path:
    dest = TARGET_DIR / e.name
    if dest.exists():
        ts = datetime.now().strftime("%H%M%S")
        dest = TARGET_DIR / f"{dest.stem}_{ts}{dest.suffix}"
    dest.write_bytes(e.content.read())
    return dest


# ── 5. Token-Middleware ───────────────────────────────────────────────────────

@app.middleware("http")
async def token_guard(request, call_next):
    if not USE_TOKEN:
        return await call_next(request)
    # Interne NiceGUI-Routen durchlassen
    path = request.url.path
    if any(path.startswith(p) for p in ["/_nicegui", "/static", "/_starlette", "/favicon"]):
        return await call_next(request)
    # WebSocket durchlassen
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)
    # Token prüfen
    req_token = request.query_params.get("token", "")
    if req_token != TOKEN:
        from starlette.responses import HTMLResponse
        return HTMLResponse(
            "<html><body style='font-family:monospace;background:#111;color:#f55;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><div style='font-size:2rem'>⛔</div>"
            "<div>Access denied — scan QR code</div></div></body></html>",
            status_code=403
        )
    return await call_next(request)


# ── 6. CSS ────────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'IBM Plex Sans', sans-serif;
  background: #0d0d0d;
  color: #ddd;
  min-height: 100vh;
}

.nt-header {
  border-bottom: 1px solid #222;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  gap: 1.2rem;
}
.nt-logo {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 1.05rem;
  color: #00e676;
}
.nt-mode-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  padding: 0.2rem 0.55rem;
  border-radius: 2px;
  letter-spacing: 0.08em;
}
.badge-up    { background: #003320; color: #00e676; border: 1px solid #00e67633; }
.badge-down  { background: #001a33; color: #40c4ff; border: 1px solid #40c4ff33; }
.badge-share { background: #2a1a00; color: #ffab40; border: 1px solid #ffab4033; }

.nt-body {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.8rem 2rem;
  display: grid;
  gap: 1.5rem;
}

.nt-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}
@media (max-width: 600px) {
  .nt-grid { grid-template-columns: 1fr; }
  .nt-body { padding: 1rem; }
}

.nt-card {
  background: #141414;
  border: 1px solid #222;
  border-radius: 4px;
  padding: 1.4rem;
}
.nt-card-title {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem;
  color: #444;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 1rem;
}

.nt-url {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: #00e676;
  background: #071a0e;
  border: 1px solid #00e67622;
  border-radius: 3px;
  padding: 0.55rem 0.75rem;
  word-break: break-all;
  margin-bottom: 1rem;
}

.nt-qr {
  display: flex;
  justify-content: center;
  margin: 0.5rem 0 1rem;
}
.nt-qr svg {
  background: white;
  padding: 10px;
  border-radius: 4px;
  width: 170px;
  height: 170px;
}
.nt-qr-hint {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: #444;
  text-align: center;
  margin-top: 0.4rem;
}

.nt-dir {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  color: #444;
  margin-top: 0.6rem;
  word-break: break-all;
}

.nt-file-entry {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.5rem 0;
  border-bottom: 1px solid #1c1c1c;
  gap: 0.5rem;
}
.nt-file-entry:last-child { border-bottom: none; }
.nt-file-name {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: #bbb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 55%;
}
.nt-file-meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.67rem;
  color: #444;
  text-align: right;
  white-space: nowrap;
}
.nt-count {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: #00e67655;
  margin-bottom: 0.6rem;
}
.nt-empty {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: #2a2a2a;
  text-align: center;
  padding: 1.5rem 0;
}

.q-uploader {
  background: #141414 !important;
  border: 1px dashed #2a2a2a !important;
  border-radius: 4px !important;
  width: 100% !important;
  max-width: 100% !important;
  box-shadow: none !important;
}
.q-uploader__header { background: #1a1a1a !important; }
.q-uploader__list   { background: #111 !important; }
</style>
"""


# ── 7. UI ─────────────────────────────────────────────────────────────────────

MODE_LABELS = {"up": "upload", "down": "download", "share": "share"}
MODE_CLASSES = {"up": "badge-up", "down": "badge-down", "share": "badge-share"}

CAN_UPLOAD   = MODE in ("up", "share")
CAN_DOWNLOAD = MODE in ("down", "share")

@ui.page("/")
def index():
    ui.add_head_html(CSS)

    # Header
    with ui.element("div").classes("nt-header"):
        ui.element("div").classes("nt-logo").set_content("nicetransfer")
        ui.element("div").classes(f"nt-mode-badge {MODE_CLASSES[MODE]}").set_content(
            MODE_LABELS[MODE]
        )

    with ui.element("div").classes("nt-body"):

        with ui.element("div").classes("nt-grid"):

            # ── Linke Spalte ──────────────────────────────────────────────
            with ui.element("div"):

                # Verbindungs-Card
                with ui.element("div").classes("nt-card"):
                    ui.element("div").classes("nt-card-title").set_content("Connection")
                    ui.element("div").classes("nt-url").set_content(ACCESS_URL)
                    if QR_SVG:
                        with ui.element("div").classes("nt-qr"):
                            ui.html(QR_SVG)
                        ui.element("div").classes("nt-qr-hint").set_content(
                            "Scan QR → browser opens"
                        )
                    else:
                        ui.element("div").classes("nt-qr-hint").set_content(
                            "qrcode not available — enter URL manually"
                        )
                    ui.element("div").classes("nt-dir").set_content(
                        f"folder: {TARGET_DIR}"
                    )

                # Upload-Card (nur wenn CAN_UPLOAD)
                if CAN_UPLOAD:
                    ui.element("div").style("height:1.2rem")
                    with ui.element("div").classes("nt-card"):
                        ui.element("div").classes("nt-card-title").set_content("Upload files")

                        def handle_upload(e: events.UploadEventArguments):
                            dest = save_upload(e)
                            ui.notify(f"✓ {dest.name}", type="positive", position="top")
                            refresh_filelist()

                        ui.upload(
                            on_upload=handle_upload,
                            multiple=True,
                            auto_upload=True,
                        ).props('color="green-9" flat bordered label="Select files"').classes("w-full")

            # ── Rechte Spalte: Dateiliste ─────────────────────────────────
            with ui.element("div").classes("nt-card"):
                header_text = "Files in folder"
                if CAN_DOWNLOAD and not CAN_UPLOAD:
                    header_text = "Available files"
                ui.element("div").classes("nt-card-title").set_content(header_text)

                list_container = ui.element("div")

                def refresh_filelist():
                    list_container.clear()
                    entries = file_entries()
                    with list_container:
                        if not entries:
                            ui.element("div").classes("nt-empty").set_content(
                                "no files available"
                            )
                        else:
                            ui.element("div").classes("nt-count").set_content(
                                f"{len(entries)} file{'s' if len(entries) != 1 else ''}"
                            )
                            for e in entries:
                                with ui.element("div").classes("nt-file-entry"):
                                    if CAN_DOWNLOAD:
                                        ui.link(
                                            e["name"],
                                            target=f"/download/{e['name']}",
                                        ).classes("nt-file-name").style("color:#40c4ff")
                                    else:
                                        ui.element("div").classes("nt-file-name").set_content(e["name"])
                                    with ui.element("div").classes("nt-file-meta"):
                                        ui.element("div").set_content(e["size"])
                                        ui.element("div").set_content(e["time"])

                refresh_filelist()
                ui.timer(5.0, refresh_filelist)


# ── 8. Download-Route ─────────────────────────────────────────────────────────

if CAN_DOWNLOAD:
    from starlette.responses import FileResponse
    from starlette.routing import Route

    @app.get("/download/{filename}")
    async def download_file(filename: str):
        file_path = TARGET_DIR / filename
        if not file_path.exists() or not file_path.is_file():
            from starlette.responses import Response
            return Response("File not found", status_code=404)
        # Security check: no path traversal
        try:
            file_path.resolve().relative_to(TARGET_DIR)
        except ValueError:
            from starlette.responses import Response
            return Response("Invalid path", status_code=403)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )


# ── 9. Start-Banner ───────────────────────────────────────────────────────────

token_info = f"Token     : {TOKEN}" if USE_TOKEN else "Token     : none (--no-token)"
can_info   = f"Upload: {'✓' if CAN_UPLOAD else '✗'}  Download: {'✓' if CAN_DOWNLOAD else '✗'}"

print(f"""
┌──────────────────────────────────────────────┐
│  nicetransfer  [{MODE_LABELS[MODE]:^8}]                   │
├──────────────────────────────────────────────┤
│  Folder    : {str(TARGET_DIR):<33}│
│  Local     : http://127.0.0.1:{PORT:<5}              │
│  Network   : {ACCESS_URL:<33}│
│  {token_info:<44}│
│  {can_info:<44}│
├──────────────────────────────────────────────┤
│  Scan QR code in browser                     │
│  Ctrl+C to quit                              │
└──────────────────────────────────────────────┘
""")

ui.run(
    host="0.0.0.0",
    port=PORT,
    title="nicetransfer",
    favicon="📁",
    dark=True,
    reload=False,
    show=False,
)
