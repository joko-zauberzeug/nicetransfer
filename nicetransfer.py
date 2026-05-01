#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Joko Keuschnig
"""
nicetransfer — local file transfer via browser
NiceGUI 3.x
"""

import sys, subprocess, importlib, socket, secrets, argparse, webbrowser, threading, base64, zipfile, io, json as _json, asyncio, os, signal, atexit
from pathlib import Path
from datetime import datetime
import time as _time


# ── 1. Dependency-Check ───────────────────────────────────────────────────────

def _pkg_installed(name):
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False

def _install(spec):
    print(f"  → installing {spec} ...")
    r = subprocess.run([sys.executable, "-m", "pip", "install", spec, "--quiet"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ Error:\n{r.stderr}")
        print("  Tip: run ./run.sh (activates venv)")
        sys.exit(1)
    print(f"  ✓ {spec}")

def check_deps():
    needed = []
    if not _pkg_installed("nicegui"): needed.append("nicegui")
    if not _pkg_installed("qrcode"):  needed.append("qrcode[svg]")
    if not _pkg_installed("mcp"):     needed.append("mcp")
    if sys.version_info < (3,11) and not _pkg_installed("tomli"): needed.append("tomli")
    if needed:
        print("nicetransfer: installing missing dependencies:")
        for p in needed: _install(p)
        print()

check_deps()


# ── 2. Imports ────────────────────────────────────────────────────────────────

from nicegui import ui, app, events, background_tasks
from starlette.requests import Request
from starlette.responses import FileResponse, Response, HTMLResponse, JSONResponse, PlainTextResponse

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import qrcode, qrcode.image.svg, io as _io
    HAS_QR = True
except ImportError:
    HAS_QR = False

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ── 3. Paths & Static ─────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "config.toml"
PID_FILE    = SCRIPT_DIR / ".nicetransfer.pid"
app.add_static_files("/nt-static", str(SCRIPT_DIR))


# ── 4. Config ─────────────────────────────────────────────────────────────────

def load_config():
    if not CONFIG_FILE.exists(): return {}
    if tomllib is None: return {}
    with open(CONFIG_FILE, "rb") as f: return tomllib.load(f)

cfg = load_config()

def cfg_path(key, default):
    return Path(cfg.get("dirs", {}).get(key, default)).expanduser().resolve()
def cfg_int(section, key, default):
    return int(cfg.get(section, {}).get(key, default))
def cfg_str(section, key, default):
    return str(cfg.get(section, {}).get(key, default))
def cfg_bool(section, key, default):
    return bool(cfg.get(section, {}).get(key, default))
def cfg_theme():
    t = cfg.get("ui", {}).get("theme", "auto").lower()
    return {"dark": True, "light": False}.get(t, None)  # None = auto


# ── 5. CLI ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="nicetransfer")
parser.add_argument("--upload-dir",   type=Path, default=None)
parser.add_argument("--download-dir", type=Path, default=None)
parser.add_argument("--share-dir",    type=Path, default=None)
parser.add_argument("--port",         type=int,  default=None)
parser.add_argument("--no-upload",    action="store_true")
parser.add_argument("--no-download",  action="store_true")
parser.add_argument("--no-share",     action="store_true")
parser.add_argument("--token",        type=str,  default=None)
ARGS = parser.parse_args()

DATA = SCRIPT_DIR / "data"
UPLOAD_DIR   = (ARGS.upload_dir.expanduser().resolve()   if ARGS.upload_dir
                else cfg_path("upload",   str(DATA / "upload")))
DOWNLOAD_DIR = (ARGS.download_dir.expanduser().resolve() if ARGS.download_dir
                else cfg_path("download", str(DATA / "download")))
SHARE_DIR    = (ARGS.share_dir.expanduser().resolve()    if ARGS.share_dir
                else cfg_path("share",    str(DATA / "share")))
TRASH_DIR    = DATA / "trash"
_cfg_port = ARGS.port if ARGS.port is not None else cfg_int("server", "port", 0)
if _cfg_port == 0:
    _range = cfg.get("server", {}).get("port_range", [7700, 7799])
    _start, _end = int(_range[0]), int(_range[1])
    PORT = None
    import random as _random
    for _p in _random.sample(range(_start, _end + 1), _end - _start + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
            if _s.connect_ex(('127.0.0.1', _p)) != 0:
                PORT = _p
                break
    if PORT is None:
        print(f"✗  No free port found in range {_start}–{_end}. Set a fixed port in config.toml.")
        sys.exit(1)
else:
    PORT = _cfg_port
TOKEN       = ARGS.token or cfg_str("server", "token", "") or secrets.token_urlsafe(12)
TIMEOUT_MIN          = cfg_int("server",  "timeout",        0)   # 0 = no timeout
VERSION              = "1.2"
UPDATE_CHECK_ON_START = cfg_bool("updates", "check_on_start", False)
NOTIFY_DEPS          = cfg_bool("updates", "notify_deps",     False)
UPDATE_CHANNEL       = cfg_str("updates",  "channel",         "stable")

for d in [UPLOAD_DIR, DOWNLOAD_DIR, SHARE_DIR, TRASH_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if PID_FILE.exists():
    try:
        _pid_data = dict(line.split("=", 1) for line in PID_FILE.read_text().strip().splitlines())
        _pid  = int(_pid_data["pid"])
        _port = int(_pid_data["port"])
        os.kill(_pid, 0)
        print(f"✗  NiceTransfer is already running from this directory (PID {_pid}, port {_port}).")
        print(f"   Stop it first:  pkill -f nicetransfer.py")
        print(f"   Or restart it:  pkill -f nicetransfer.py && while pgrep -f nicetransfer.py > /dev/null 2>&1; do sleep 0.1; done && bash {SCRIPT_DIR}/run.sh")
        sys.exit(1)
    except (ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
    except (KeyError, ValueError):
        PID_FILE.unlink(missing_ok=True)


# ── 6. State ──────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.upload_enabled   = not ARGS.no_upload   and cfg_bool("ui", "upload",   True)
        self.download_enabled = not ARGS.no_download and cfg_bool("ui", "download", True)
        self.share_enabled    = not ARGS.no_share    and cfg_bool("ui", "share",    True)
        self.client_delete_upload   = cfg_bool("permissions", "client_delete_upload",   True)
        self.client_delete_download = cfg_bool("permissions", "client_delete_download", False)
        self.client_delete_share    = cfg_bool("permissions", "client_delete_share",    True)
        self.client_trash_visible   = cfg_bool("permissions", "client_trash_visible",   False)
        self.client_trash_restore   = cfg_bool("permissions", "client_trash_restore",   False)

state = AppState()


# ── 7. Helpers ────────────────────────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP   = get_local_ip()
NO_NETWORK = LOCAL_IP == "127.0.0.1"
ACCESS_URL = f"http://{LOCAL_IP}:{PORT}/?token={TOKEN}"

def hotspot_hint_md():
    if sys.platform == "darwin":
        return (
            "**No network detected** — other devices cannot reach this server.\n\n"
            "**Option A — Internet Sharing (macOS):**  \n"
            "System Settings → General → Sharing → Internet Sharing\n\n"
            "**Option B — use a phone hotspot:**  \n"
            "Enable Personal Hotspot on iPhone or Android, then connect this Mac to it."
        )
    elif sys.platform == "linux":
        return (
            "**No network detected** — other devices cannot reach this server.\n\n"
            "**Create a hotspot** (requires NetworkManager):  \n"
            "```\nnmcli device wifi hotspot ssid 'nicetransfer' password 'yourpassword'\n```\n"
            "Or: Settings → WiFi → Turn on Hotspot"
        )
    elif sys.platform.startswith("win"):
        return (
            "**No network detected** — other devices cannot reach this server.\n\n"
            "**Create a hotspot (Windows):**  \n"
            "Settings → Network & Internet → Mobile Hotspot"
        )
    else:
        return "**No network detected.** Please create a WiFi hotspot so other devices can connect."

def hotspot_hint_text():
    if sys.platform == "darwin":
        return (
            "  Option A: System Settings → General → Sharing → Internet Sharing\n"
            "  Option B: connect to an iPhone/Android Personal Hotspot"
        )
    elif sys.platform == "linux":
        return (
            "  nmcli device wifi hotspot ssid 'nicetransfer' password 'yourpassword'\n"
            "  or: Settings → WiFi → Turn on Hotspot"
        )
    elif sys.platform.startswith("win"):
        return "  Settings → Network & Internet → Mobile Hotspot"
    else:
        return "  Please create a WiFi hotspot manually."

def make_qr_svg(url):
    if not HAS_QR: return ""
    try:
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                          box_size=8, border=2)
        buf = _io.BytesIO(); img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception:
        return ""

QR_SVG = make_qr_svg(ACCESS_URL)

def is_local(request: Request):
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}

def file_entries(directory: Path):
    try:
        files = [f for f in directory.iterdir() if f.is_file() and f.name != ".gitkeep"]
    except Exception:
        return []
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        sz = f.stat().st_size
        mt = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size_str = (f"{sz} B" if sz < 1024 else
                    f"{sz/1024:.1f} KB" if sz < 1024**2 else
                    f"{sz/1024**2:.1f} MB")
        result.append({"name": f.name, "size": size_str, "time": mt,
                        "is_img": f.suffix.lower() in IMAGE_EXTS,
                        "dir": directory.name})
    return result

async def save_upload(e: events.UploadEventArguments, directory: Path):
    name = e.file.name
    dest = directory / name
    if dest.exists():
        ts = datetime.now().strftime("%H%M%S")
        dest = directory / f"{dest.stem}_{ts}{dest.suffix}"
    await e.file.save(dest)
    return dest

def safe_filename(name: str, directory: Path) -> Path | None:
    """Sanitize a filename and verify it stays within directory.
    Strips all directory components (prevents path traversal).
    Returns the destination Path or None if the name is invalid."""
    clean = Path(name).name          # keep only the final component
    if not clean or clean in (".", ".."):
        return None
    dest = directory / clean
    try:
        dest.resolve().relative_to(directory.resolve())
        return dest
    except ValueError:
        return None


def move_to_trash(file_path: Path, source_dir_name: str) -> Path:
    """Move file to trash with a timestamp prefix to avoid name conflicts."""
    batch = datetime.now().strftime("%Y%m%d_%H%M%S")
    trash_name = f"{batch}_{file_path.name}"
    dest = TRASH_DIR / trash_name
    file_path.rename(dest)
    meta = {"original_name": file_path.name, "source": source_dir_name, "batch": batch}
    (TRASH_DIR / f"{trash_name}.meta").write_text(_json.dumps(meta))
    return dest

def restore_from_trash(trash_name: str) -> bool:
    """Restore a file from trash to its original section directory."""
    trash_path = TRASH_DIR / trash_name
    meta_path  = TRASH_DIR / f"{trash_name}.meta"
    if not trash_path.exists():
        return False
    original_name = trash_name
    source_dir    = SHARE_DIR
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text())
            original_name = meta.get("original_name", trash_name)
            source_dir = {"upload": UPLOAD_DIR, "download": DOWNLOAD_DIR,
                          "share": SHARE_DIR}.get(meta.get("source", ""), SHARE_DIR)
        except Exception:
            pass
    dest = source_dir / original_name
    if dest.exists():
        ts   = datetime.now().strftime("%H%M%S")
        stem = Path(original_name).stem
        suf  = Path(original_name).suffix
        dest = source_dir / f"{stem}_{ts}{suf}"
    trash_path.rename(dest)
    if meta_path.exists():
        meta_path.unlink()
    return True

def trash_entries():
    """Return file entries for the trash directory, excluding .meta sidecars."""
    try:
        files = [f for f in TRASH_DIR.iterdir()
                 if f.is_file() and not f.name.endswith(".meta") and f.name != ".gitkeep"]
    except Exception:
        return []
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        meta_path = TRASH_DIR / f"{f.name}.meta"
        meta = {}
        if meta_path.exists():
            try:
                meta = _json.loads(meta_path.read_text())
            except Exception:
                pass
        sz = f.stat().st_size
        mt = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size_str = (f"{sz} B" if sz < 1024 else
                    f"{sz/1024:.1f} KB" if sz < 1024**2 else
                    f"{sz/1024**2:.1f} MB")
        result.append({
            "name":          f.name,
            "original_name": meta.get("original_name", f.name),
            "source":        meta.get("source", ""),
            "size":          size_str,
            "time":          mt,
        })
    return result


# ── 8. Token middleware ───────────────────────────────────────────────────────

@app.middleware("http")
async def token_guard(request, call_next):
    path = request.url.path
    skip = ["/_nicegui", "/static", "/favicon", "/nt-static"]
    if any(path.startswith(p) for p in skip): return await call_next(request)
    if request.headers.get("upgrade","").lower() == "websocket": return await call_next(request)
    if request.query_params.get("token","") != TOKEN:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;background:#1d2027;color:#ff6d00;"
            "display:flex;align-items:center;justify-content:center;height:100vh'>"
            "<div style='text-align:center'><div style='font-size:2rem'>⛔</div>"
            "<div>Access denied — scan QR code</div></div></body></html>",
            status_code=403)
    return await call_next(request)


# ── 9. CSS ────────────────────────────────────────────────────────────────────

CSS = f'<link rel="stylesheet" href="/nt-static/nicetransfer.css?v={int(__import__("time").time())}">'

app.colors(primary='#FF6D00')


# ── 10. File section ──────────────────────────────────────────────────────────

def make_rows(entries, with_download):
    rows = []
    for e in entries:
        rows.append({
            "name":        e["name"],
            "size":        e["size"],
            "time":        e["time"],
            "is_img":      e["is_img"],
            "dl_url":      f"/download/{e['dir']}/{e['name']}?token={TOKEN}" if with_download else "",
            "preview_url": f"/preview/{e['dir']}/{e['name']}"  if e["is_img"]   else "",
        })
    return rows

def build_file_section(title: str, directory: Path, with_upload: bool, with_download: bool,
                       anchor: str, with_delete: bool = False):
    entries = file_entries(directory)
    rows = make_rows(entries, with_download)

    # An "actions" column sits between the native select-all checkbox and File header.
    # It holds the ZIP-download and/or Trash buttons when enabled.
    has_actions = with_download or with_delete
    columns = []
    if has_actions:
        columns.append({"name": "actions", "label": "", "field": "name",
                        "sortable": False, "align": "left"})
    columns += [
        {"name": "name", "label": "File", "field": "name", "sortable": True,  "align": "left"},
        {"name": "size", "label": "Size", "field": "size", "sortable": False, "align": "right"},
        {"name": "time", "label": "Date", "field": "time", "sortable": True,  "align": "right"},
    ]

    with ui.card().classes("w-full q-pa-none nt-section").props(f'id="{anchor}"'):

        # ── Row 1: centered title ─────────────────────────────────────────────
        with ui.row().classes("nt-section-header items-center justify-center w-full q-py-sm"):
            ui.label(title).classes("nt-section-title text-h5 text-primary")

        # ── Row 2: drop zone + Upload Files (only when upload enabled) ────────
        if with_upload:
            async def handle_upload(e: events.UploadEventArguments, d=directory):
                dest = await save_upload(e, d)
                ui.notify(f"✓ {dest.name}", type="positive")
                new_rows = make_rows(file_entries(d), with_download)
                table.rows = new_rows
                table.update()

            uploader = ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True) \
                .classes("w-full").props("flat").style("padding:0; margin:0")

            uploader.add_slot("header", """
                <div class="nt-drop-zone row items-center justify-center q-py-xs w-full"
                     style="min-height:40px; gap:12px">
                  <q-btn v-if="props.canAddFiles" flat dense no-caps
                         class="nt-text-secondary" icon="upload" label="Upload files">
                    <q-uploader-add-trigger />
                  </q-btn>
                  <q-btn v-if="props.canAddFiles" flat dense no-caps
                         class="nt-text-secondary" icon="photo_camera" label="Take photo">
                    <input type="file" accept="image/*" capture="environment"
                           class="q-uploader__input overflow-hidden absolute-full cursor-pointer"
                           aria-hidden="true" title=""
                           @change="props.addFiles(Array.from($event.target.files)); $event.target.value = ''" />
                  </q-btn>
                  <div class="row items-center text-body2 nt-text-secondary" style="gap:4px">
                    or
                    <q-icon name="upload_file" size="sm" />
                    Drop files here
                  </div>
                </div>
            """)
            uploader.add_slot("list", "")

        # ── Image preview dialog ──────────────────────────────────────────────
        with ui.dialog() as img_dialog, ui.card() \
                .props("dark") \
                .classes("p-0 relative overflow-hidden shadow-none") \
                .style("max-width:95vw"):
            preview_html = ui.html("").classes("block")
            ui.button("✕", on_click=img_dialog.close) \
                .props("flat color=white round dense size=sm") \
                .classes("absolute-top-right q-ma-xs")

        _mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                     ".gif": "image/gif", ".webp": "image/webp",
                     ".bmp": "image/bmp", ".svg": "image/svg+xml"}

        def handle_preview(ev):
            url: str = ev.args
            parts = url.lstrip("/").split("/")
            if len(parts) >= 3:
                _, file_path = _resolve_file(parts[1], parts[2])
                if file_path:
                    mime = _mime_map.get(file_path.suffix.lower(), "image/jpeg")
                    b64  = base64.b64encode(file_path.read_bytes()).decode()
                    preview_html.set_content(
                        f'<img src="data:{mime};base64,{b64}" '
                        f'style="max-width:88vw;max-height:80vh;object-fit:contain;display:block">'
                    )
            img_dialog.open()

        # ── Search + Table ────────────────────────────────────────────────────
        with ui.column().classes("w-full q-pa-sm gap-2"):
            search = ui.input(placeholder="Search...").props("dense outlined clearable").classes("w-full")

            if with_delete:
                _undo: dict = {"names": [], "task": None}
                with ui.row().classes("items-center q-px-xs q-py-xs").style(
                        "gap:0.5rem; background:rgba(255,109,0,0.08); border-radius:4px") as undo_bar:
                    undo_label = ui.label("").classes("text-body2 text-grey-8").style("flex:1; min-width:0")
                    ui.button("Undo", on_click=lambda: do_undo()) \
                        .props("flat dense no-caps size=sm color=primary")
                    ui.button(icon="close", on_click=lambda: dismiss_undo()) \
                        .props("flat round dense size=xs").classes("nt-text-secondary") \
                        .tooltip("Dismiss")
                undo_bar.set_visibility(False)

            table = ui.table(columns=columns, rows=rows, row_key="name") \
                .classes("w-full").props("dense flat" + (" selection=multiple" if has_actions else ""))
            search.bind_value_to(table, "filter")

            table.on("preview", handle_preview)

            if has_actions:
                zip_btn_html = (
                    """<q-btn flat dense round size="xs" icon="file_download"
                           :color="$parent.selected && $parent.selected.length ? 'primary' : 'grey-5'"
                           :disable="!$parent.selected || !$parent.selected.length"
                           @click.stop="$parent.$emit('download_zip')">
                        <q-tooltip anchor="bottom middle" self="top middle">Download selected as ZIP</q-tooltip>
                    </q-btn>"""
                    if with_download else ""
                )
                del_btn_html = (
                    """<q-btn flat dense round size="xs" icon="delete"
                           :color="$parent.selected && $parent.selected.length ? 'primary' : 'grey-5'"
                           :disable="!$parent.selected || !$parent.selected.length"
                           @click.stop="$parent.$emit('delete_selected')">
                        <q-tooltip anchor="bottom middle" self="top middle">Move selected to trash</q-tooltip>
                    </q-btn>"""
                    if with_delete else ""
                )
                table.add_slot("header-cell-actions", f"""
                    <q-th :props="props" auto-width>
                        {zip_btn_html}
                        {del_btn_html}
                    </q-th>
                """)
                table.add_slot("body-cell-actions", """<q-td auto-width />""")

                if with_download:
                    def handle_download_zip(_ev):
                        if not table.selected:
                            return
                        buf = _io.BytesIO()
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for row in table.selected:
                                fp = directory / row["name"]
                                if fp.exists() and fp.is_file():
                                    zf.write(fp, row["name"])
                        buf.seek(0)
                        ui.download(buf.read(), f"{directory.name}.zip")

                    table.on("download_zip", handle_download_zip)

                if with_delete:
                    def do_undo(d=directory):
                        if not _undo["names"]:
                            return
                        count = 0
                        for name in list(_undo["names"]):
                            if restore_from_trash(name):
                                count += 1
                        _undo["names"] = []
                        if _undo["task"]:
                            _undo["task"].cancel()
                            _undo["task"] = None
                        undo_bar.set_visibility(False)
                        if count:
                            ui.notify(f"Restored {count} file(s)", type="positive", icon="restore")
                            table.rows = make_rows(file_entries(d), with_download)
                            table.update()

                    def dismiss_undo():
                        _undo["names"] = []
                        if _undo["task"]:
                            _undo["task"].cancel()
                            _undo["task"] = None
                        undo_bar.set_visibility(False)

                    async def handle_delete_selected(_ev, d=directory):
                        if not table.selected:
                            return
                        names = []
                        count = 0
                        for row in list(table.selected):
                            fp = d / row["name"]
                            if fp.exists() and fp.is_file():
                                trash_path = move_to_trash(fp, d.name)
                                names.append(trash_path.name)
                                count += 1
                        if count:
                            _undo["names"] = names
                            if _undo["task"]:
                                _undo["task"].cancel()

                            async def auto_dismiss():
                                await asyncio.sleep(10)
                                dismiss_undo()

                            _undo["task"] = background_tasks.create(auto_dismiss(), name='undo-auto-dismiss')
                            undo_label.set_text(f"{count} file(s) moved to trash")
                            undo_bar.set_visibility(True)
                            table.selected.clear()
                            table.rows = make_rows(file_entries(d), with_download)
                            table.update()

                    table.on("delete_selected", handle_delete_selected)

            table.add_slot("body-cell-name", """
                <q-td :props="props">
                    <q-btn v-if="props.row.dl_url" flat dense round size="xs"
                           icon="file_download" color="primary" class="q-mr-xs"
                           tag="a" :href="props.row.dl_url" @click.stop>
                        <q-tooltip anchor="bottom middle" self="top middle">Download</q-tooltip>
                    </q-btn>
                    <q-btn v-if="props.row.is_img" flat dense round size="xs"
                           icon="image" color="primary" class="q-mr-xs"
                           @click.stop="$parent.$emit('preview', props.row.preview_url)">
                        <q-tooltip anchor="bottom middle" self="top middle">Preview</q-tooltip>
                    </q-btn>
                    <span>{{ props.row.name }}</span>
                </q-td>
            """)

            # ── Live sync: update table when directory changes on any client ──
            known = {"entries": file_entries(directory)}

            def sync_table():
                current = file_entries(directory)
                if current != known["entries"]:
                    known["entries"] = current
                    table.rows = make_rows(current, with_download)
                    table.update()

            ui.timer(3.0, sync_table)


def build_trash_section(can_restore: bool = True, can_empty: bool = True):
    """Trash section — lists moved files, supports restore and permanent delete."""

    def _make_rows():
        return [{"name": e["name"], "original_name": e["original_name"],
                 "source": e["source"], "size": e["size"], "time": e["time"]}
                for e in trash_entries()]

    columns = [
        {"name": "actions",       "label": "",        "field": "name",          "sortable": False, "align": "left"},
        {"name": "original_name", "label": "File",    "field": "original_name", "sortable": True,  "align": "left"},
        {"name": "source",        "label": "From",    "field": "source",        "sortable": True,  "align": "left"},
        {"name": "size",          "label": "Size",    "field": "size",          "sortable": False, "align": "right"},
        {"name": "time",          "label": "Trashed", "field": "time",          "sortable": True,  "align": "right"},
    ]

    with ui.card().classes("w-full q-pa-none nt-section").props('id="trash"'):

        with ui.row().classes("nt-section-header items-center justify-center w-full q-py-sm"):
            ui.label("Trash").classes("nt-section-title text-h5 text-primary")

        with ui.column().classes("w-full q-pa-sm gap-2"):
            search = ui.input(placeholder="Search...").props("dense outlined clearable").classes("w-full")

            table = ui.table(columns=columns, rows=_make_rows(), row_key="name") \
                .classes("w-full").props("dense flat selection=multiple")
            search.bind_value_to(table, "filter")

            restore_btn_html = (
                """<q-btn flat dense round size="xs" icon="restore"
                       :color="$parent.selected && $parent.selected.length ? 'primary' : 'grey-5'"
                       :disable="!$parent.selected || !$parent.selected.length"
                       @click.stop="$parent.$emit('restore_selected')">
                    <q-tooltip anchor="bottom middle" self="top middle">Restore selected</q-tooltip>
                </q-btn>"""
                if can_restore else ""
            )
            perm_del_btn_html = (
                """<q-btn flat dense round size="xs" icon="delete_forever"
                       :color="$parent.selected && $parent.selected.length ? 'red-7' : 'grey-5'"
                       :disable="!$parent.selected || !$parent.selected.length"
                       @click.stop="$parent.$emit('perm_delete')">
                    <q-tooltip anchor="bottom middle" self="top middle">Delete permanently</q-tooltip>
                </q-btn>"""
                if can_empty else ""
            )
            table.add_slot("header-cell-actions", f"""
                <q-th :props="props" auto-width>
                    {restore_btn_html}
                    {perm_del_btn_html}
                </q-th>
            """)
            table.add_slot("body-cell-actions", """<q-td auto-width />""")

            if can_restore:
                def handle_restore(_ev):
                    if not table.selected:
                        return
                    count = 0
                    for row in list(table.selected):
                        if restore_from_trash(row["name"]):
                            count += 1
                    if count:
                        ui.notify(f"Restored {count} file(s)", type="positive", icon="restore")
                        table.selected.clear()
                        table.rows = _make_rows()
                        table.update()
                table.on("restore_selected", handle_restore)

            if can_empty:
                def handle_perm_delete(_ev):
                    if not table.selected:
                        return
                    count = 0
                    for row in list(table.selected):
                        fp   = TRASH_DIR / row["name"]
                        meta = TRASH_DIR / f"{row['name']}.meta"
                        if fp.exists():
                            fp.unlink()
                            count += 1
                        if meta.exists():
                            meta.unlink()
                    if count:
                        ui.notify(f"Permanently deleted {count} file(s)", type="negative", icon="delete_forever")
                        table.selected.clear()
                        table.rows = _make_rows()
                        table.update()
                table.on("perm_delete", handle_perm_delete)

            known = {"entries": trash_entries()}

            def sync_trash():
                current = trash_entries()
                if current != known["entries"]:
                    known["entries"] = current
                    table.rows = _make_rows()
                    table.update()

            ui.timer(3.0, sync_trash)


# ── 11. Shared header ─────────────────────────────────────────────────────────

def build_header(is_dark, section_links=None, current="", is_local=False):
    logo_href = f"/?token={TOKEN}"

    with ui.header().classes("items-center q-px-md q-py-sm nt-header"):
        with ui.column().classes("gap-0 items-start"):
            ui.html(f'<a href="{logo_href}" class="nt-logo text-primary">'
                    f'<span style="font-weight:700">Nice</span>'
                    f'<span style="font-weight:400">Transfer</span>'
                    f'</a>')
            countdown = ui.label().classes("nt-text-secondary text-caption").style(
                "font-family: monospace; line-height: 1; margin-left: 2px"
            ).tooltip("Session timeout")
            def _update_countdown(lbl=countdown):
                if _timeout_active <= 0:
                    lbl.set_text("")
                    return
                remaining = max(0, _timeout_active * 60 - (_time.time() - _start_time))
                m, s = divmod(int(remaining), 60)
                lbl.set_text(f"⏱ {m}:{s:02d}")
            _update_countdown()
            ui.timer(1, _update_countdown)

        tab_refs  = {}
        menu_refs = {}

        if section_links:
            with ui.tabs().props("dense no-caps").classes("nt-text-secondary nt-nav-tabs"):
                for label, anchor in section_links:
                    t = ui.tab(label).on("click",
                        js_handler=f"() => document.getElementById('{anchor}')?.scrollIntoView({{behavior:'smooth'}})")
                    tab_refs[anchor] = t

        ui.space()

        icon = "dark_mode" if is_dark.value is True else ("light_mode" if is_dark.value is False else "brightness_auto")
        theme_btn = ui.button(icon=icon).props("flat round dense").classes("nt-text-secondary").tooltip("Toggle theme")

        def toggle_theme():
            if is_dark.value is True:
                is_dark.set_value(None); theme_btn.props("icon=brightness_auto")
            elif is_dark.value is None:
                is_dark.set_value(False); theme_btn.props("icon=light_mode")
            else:
                is_dark.set_value(True); theme_btn.props("icon=dark_mode")
            app.storage.user['theme'] = is_dark.value

        theme_btn.on("click", toggle_theme)

        menu_btn = ui.dropdown_button(icon="menu").props("flat round dense no-caps").classes("nt-text-secondary")
        with menu_btn:
            with ui.list().props("dense"):
                if section_links:
                    for label, anchor in section_links:
                        item = ui.item(label, on_click=None).classes("nt-menu-section").on("click",
                            js_handler=f"() => document.getElementById('{anchor}')?.scrollIntoView({{behavior:'smooth'}})")
                        menu_refs[anchor] = item
                    ui.separator()
                ui.item("Manual",    on_click=lambda: ui.navigate.to(f"/manual?token={TOKEN}"))
                ui.item("Changelog", on_click=lambda: ui.navigate.to(f"/changelog?token={TOKEN}"))
                ui.item("Get",       on_click=lambda: ui.navigate.to(f"/get?token={TOKEN}"))
                if is_local:
                    ui.separator()
                    ui.item("Development", on_click=lambda: ui.navigate.to(f"/development?token={TOKEN}"))

        if section_links:
            # None = always visible; str = state attribute to check
            anchor_to_key = {
                "connection": None,
                "control":    None,
                "share":      "share_enabled",
                "upload":     "upload_enabled",
                "download":   "download_enabled",
                "trash":      None if is_local else "client_trash_visible",
            }

            def update_nav():
                for anchor, tab in tab_refs.items():
                    key = anchor_to_key.get(anchor)
                    vis = True if key is None else getattr(state, key, True)
                    tab.set_visibility(vis)
                    if anchor in menu_refs:
                        menu_refs[anchor].set_visibility(vis)

            ui.timer(1.0, update_nav)


# ── 12. Main page ─────────────────────────────────────────────────────────────

@ui.page("/")
async def index(request: Request):
    local = is_local(request)
    ui.add_head_html(CSS)
    ui.add_head_html(
        f'<meta name="mcp-server" content="http://{LOCAL_IP}:{PORT}/mcp?token={TOKEN}">\n'
        f'<meta name="mcp-server-card" content="http://{LOCAL_IP}:{PORT}/.well-known/mcp/server-card.json?token={TOKEN}">\n'
        f'<meta name="llms-txt" content="http://{LOCAL_IP}:{PORT}/llms.txt?token={TOKEN}">'
    )
    is_dark = ui.dark_mode(value=app.storage.user.get('theme', cfg_theme()))

    # Build header — local gets Connection + Control tabs in addition to file sections
    _section_links = []
    if local:
        _section_links += [("Connection", "connection"), ("Control", "control")]
    _section_links += [
        ("Share",         "share"),
        ("Upload only",   "upload"),
        ("Download only", "download"),
        ("Trash",         "trash"),
    ]
    build_header(is_dark, is_local=local, section_links=_section_links)

    with ui.column().classes("w-full q-pa-md").style("max-width: 960px; margin: 0 auto; gap: 1.5rem"):

        # ── Server control panel ──────────────────────────────────────────────
        if local:
            _cur = get_local_ip()
            _last_ip = {"value": _cur, "real": _cur}  # "real" = last non-loopback IP

            @ui.refreshable
            def local_panel():
                ip = get_local_ip()
                no_net = ip == "127.0.0.1"
                url = f"http://{ip}:{PORT}/?token={TOKEN}"
                qr  = make_qr_svg(url) if not no_net else ""

                with ui.element("div").classes("nt-hero nt-section w-full").props('id="connection"'):
                    with ui.element("div").classes("nt-hero-content"):
                        if no_net:
                            ui.icon("wifi_off").props("size=4rem color=primary").classes("opacity-60")
                            ui.label("No network detected").classes("text-h5")
                            ui.label("Other devices cannot connect") \
                                .classes("text-body2 text-grey q-mb-sm")
                            with ui.card().classes("text-left").style("max-width: 480px"):
                                ui.markdown(hotspot_hint_md())
                        else:
                            ui.html(
                                'Simple and <span class="text-primary">NiceTransfer</span> of files.'
                            ).classes("text-h3 text-weight-bold")
                            with ui.element("div").classes("nt-qr-hero"):
                                ui.html(qr)
                            ui.label("Scan QR code to connect").classes("text-h5")
                            with ui.row().classes("items-center justify-center").style("gap:0.25rem"):
                                ui.label(url).classes("nt-url")

                                async def do_copy(u=url):
                                    await ui.clipboard.write(u)
                                    ui.notify("URL copied", type="positive", timeout=1500)

                                ui.button(icon="content_copy", on_click=do_copy) \
                                    .props("flat round dense size=xs").classes("nt-text-secondary") \
                                    .tooltip("Copy URL")
                                with ui.element("span").classes("nt-share-wrap"):
                                    ui.button(icon="share") \
                                        .props("flat round dense size=xs").classes("nt-text-secondary") \
                                        .tooltip("Share") \
                                        .on("click", js_handler=(
                                            f"() => navigator.share({{title:'NiceTransfer',"
                                            f"url:{_json.dumps(url)}}})"
                                        ))
                                ui.run_javascript(
                                    "document.querySelectorAll('.nt-share-wrap')"
                                    ".forEach(e => { if (!navigator.share) e.style.display='none' })"
                                )
                    ui.icon("keyboard_arrow_down").props("size=2rem") \
                        .classes("nt-scroll-hint")

                with ui.card().classes("w-full q-pa-none nt-section").props('id="control"'):
                    with ui.row().classes("nt-section-header items-center justify-center w-full q-py-sm"):
                        ui.label("Control").classes("nt-section-title text-h5 text-primary")
                    with ui.column().classes("w-full q-pa-sm gap-0"):
                        for label, key, path in [
                            ("Share",         "share_enabled",    SHARE_DIR),
                            ("Upload only",   "upload_enabled",   UPLOAD_DIR),
                            ("Download only", "download_enabled", DOWNLOAD_DIR),
                        ]:
                            with ui.column().classes("w-full q-py-xs gap-0"):
                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label(label)
                                    _key = key
                                    ui.switch(value=getattr(state, _key),
                                        on_change=lambda e, k=_key: setattr(state, k, e.value))
                                ui.label(str(path)).classes("text-caption nt-text-secondary break-all -mt-1")
                            ui.separator().props("spaced=false")

                        ui.label("Client permissions").classes("text-overline q-mt-sm text-primary")
                        ui.separator()
                        _restore_ref = {}
                        for label, key in [
                            ("Client can delete — Share",         "client_delete_share"),
                            ("Client can delete — Upload only",   "client_delete_upload"),
                            ("Client can delete — Download only", "client_delete_download"),
                            ("Clients see Trash",                 "client_trash_visible"),
                            ("Clients can restore from Trash",    "client_trash_restore"),
                        ]:
                            indent = key == "client_trash_restore"
                            row = ui.row().classes("items-center justify-between w-full q-py-xs")
                            if indent:
                                row.classes("pl-5")
                            with row:
                                lbl = ui.label(label)
                                _key = key
                                if key == "client_trash_visible":
                                    def on_trash_visible(e, r=_restore_ref):
                                        state.client_trash_visible = e.value
                                        if "lbl" in r:
                                            r["lbl"].style("opacity:1" if e.value else "opacity:0.38")
                                    ui.switch(value=state.client_trash_visible, on_change=on_trash_visible)
                                elif key == "client_trash_restore":
                                    _restore_ref["lbl"] = lbl
                                    lbl.style("opacity:1" if state.client_trash_visible else "opacity:0.38")
                                    ui.switch(value=state.client_trash_restore,
                                        on_change=lambda e: setattr(state, "client_trash_restore", e.value)) \
                                        .bind_enabled_from(state, "client_trash_visible")
                                else:
                                    ui.switch(value=getattr(state, _key),
                                        on_change=lambda e, k=_key: setattr(state, k, e.value))
                            ui.separator().props("spaced=false")

                        ui.label("Session timeout").classes("text-overline q-mt-sm text-primary")
                        ui.separator()
                        with ui.row().classes("items-center justify-between w-full q-py-xs"):
                            ui.label("Timeout (minutes, 0 = off)")
                            with ui.row().classes("items-center gap-2"):
                                timeout_input = ui.number(value=_timeout_active, min=0, step=1, precision=0) \
                                    .props("dense outlined").classes("w-20")
                                def apply_timeout():
                                    global _start_time, _timeout_active
                                    _timeout_active = max(0, int(timeout_input.value or 0))
                                    _start_time = _time.time()
                                    _start_shutdown_timer()
                                ui.button("Set", on_click=apply_timeout) \
                                    .props("flat dense color=primary")
                        ui.separator().props("spaced=false")

                        ui.label("Updates").classes("text-overline q-mt-sm text-primary")
                        ui.separator()

                        @ui.refreshable
                        def update_status_display():
                            if _update_notice.get("nt"):
                                n = _update_notice["nt"]
                                ui.label(f"v{n['latest']} available [{n['channel']}]") \
                                    .classes("text-caption text-primary")
                                ui.button("Upgrade", on_click=open_upgrade_dialog) \
                                    .props("flat dense color=primary size=sm")
                            elif _update_checked:
                                ui.label("Up to date").classes("text-caption nt-text-secondary")
                            else:
                                ui.label("Not checked").classes("text-caption nt-text-secondary")
                            if _update_notice.get("nicegui"):
                                ng = _update_notice["nicegui"]
                                ui.label(f"NiceGUI {ng['latest']} available (installed: {ng['local']})") \
                                    .classes("text-caption text-grey")

                        async def check_updates_now():
                            check_btn.props(add="loading")
                            await _check_updates(force=True)
                            check_btn.props(remove="loading")
                            update_status_display.refresh()
                            import importlib.metadata as _im
                            ng_ver = _im.version("nicegui")
                            if _update_notice.get("nt"):
                                n = _update_notice["nt"]
                                ui.notify(
                                    f"NiceTransfer v{n['latest']} available [{n['channel']}]",
                                    type="warning", close_button=True, timeout=0,
                                )
                            elif not _update_notice.get("nicegui"):
                                ui.notify(
                                    f"NiceTransfer v{VERSION} · NiceGUI {ng_ver} — all up to date",
                                    type="positive", close_button=True, timeout=0,
                                )
                            else:
                                ui.notify(
                                    f"NiceTransfer v{VERSION} — up to date",
                                    type="positive", close_button=True, timeout=0,
                                )
                            if _update_notice.get("nicegui"):
                                ng = _update_notice["nicegui"]
                                ui.notify(
                                    f"NiceGUI {ng['latest']} available (installed: {ng['local']})",
                                    type="info", close_button=True, timeout=0,
                                )

                        def restart_after_upgrade():
                            threading.Timer(2.0, lambda: subprocess.Popen(
                                ["bash", str(SCRIPT_DIR / "run.sh")],
                                cwd=str(SCRIPT_DIR),
                                start_new_session=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )).start()
                            PID_FILE.unlink(missing_ok=True)
                            app.shutdown()

                        async def open_upgrade_dialog():
                            n = _update_notice.get("nt", {})
                            with ui.dialog().props("persistent") as dlg, \
                                    ui.card().classes("w-full").style("min-width:420px;max-width:600px"):
                                ui.label(f"Upgrade to v{n.get('latest', '?')}").classes("text-h6")
                                ui.label(
                                    "Applies all updates automatically. "
                                    "For step-by-step review, run ./upgrade.sh in the terminal."
                                ).classes("text-caption text-grey")
                                log = ui.log(max_lines=200) \
                                    .classes("w-full q-mt-sm").style("height:220px") \
                                    .set_visibility(False)
                                status = ui.label("").classes("text-caption q-mt-xs")
                                with ui.row().classes("w-full justify-end q-mt-sm items-center"):
                                    close_btn  = ui.button("Cancel", on_click=dlg.close).props("flat")
                                    upgrade_btn = ui.button("Upgrade", color="warning") \
                                        .props("unelevated")
                                    restart_btn = ui.button("Restart now", color="primary") \
                                        .props("unelevated").set_visibility(False)

                                async def do_upgrade():
                                    close_btn.set_visibility(False)
                                    upgrade_btn.props(add="loading disable")
                                    log.set_visibility(True)
                                    proc = await asyncio.create_subprocess_exec(
                                        str(SCRIPT_DIR / "upgrade.sh"), "--yes",
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.STDOUT,
                                        cwd=str(SCRIPT_DIR),
                                    )
                                    async for line in proc.stdout:
                                        log.push(line.decode().rstrip())
                                    await proc.wait()
                                    upgrade_btn.set_visibility(False)
                                    if proc.returncode == 0:
                                        status.set_text("Upgrade complete — restart to load the new version.")
                                        restart_btn.set_visibility(True)
                                    else:
                                        status.set_text(f"Upgrade failed (exit {proc.returncode}).")
                                        close_btn.set_text("Close")
                                        close_btn.set_visibility(True)

                                upgrade_btn.on("click", do_upgrade)
                                restart_btn.on("click", restart_after_upgrade)
                            dlg.open()

                        with ui.row().classes("items-center justify-between w-full q-py-xs"):
                            with ui.column().classes("gap-0.5"):
                                import importlib.metadata as _im
                                _ng_ver = _im.version("nicegui")
                                ui.label(f"NiceTransfer v{VERSION} and NiceGUI {_ng_ver}") \
                                    .classes("text-body2")
                                update_status_display()
                            check_btn = ui.button("Check", on_click=check_updates_now) \
                                .props("flat dense color=primary")
                        ui.timer(3.0, update_status_display.refresh, once=True)
                        ui.separator().props("spaced=false")

            local_panel()

            def check_network():
                ip  = get_local_ip()
                old = _last_ip["value"]
                if ip == old:
                    return
                _last_ip["value"] = ip
                local_panel.refresh()

                if ip != "127.0.0.1":
                    _last_ip["real"] = ip

                if old == "127.0.0.1":
                    if ip == _last_ip["real"]:
                        ui.notify("Network reconnected — same IP, clients should reconnect automatically",
                                  type="positive", close_button=True, timeout=0)
                        print(f"\n✓  Network reconnected — same IP ({ip}), clients should reconnect automatically")
                    else:
                        ui.notify("Network reconnected with new IP — clients must rescan the QR code",
                                  type="warning", close_button=True, timeout=0)
                        print(f"\n⚠  Network reconnected with new IP: {_last_ip['real']} → {ip}")
                        print(f"   Clients must reconnect: http://{ip}:{PORT}/?token={TOKEN}")
                elif ip == "127.0.0.1":
                    ui.notify("Network lost — clients disconnected", type="warning", close_button=True, timeout=0)
                    print("\n⚠  Network lost — clients disconnected")
                else:
                    ui.notify("IP changed — clients must rescan the QR code",
                              type="warning", close_button=True, timeout=0)
                    print(f"\n⚠  IP changed: {old} → {ip}")
                    print(f"   Clients must reconnect: http://{ip}:{PORT}/?token={TOKEN}")

            ui.timer(5.0, check_network)

        # ── File sections ─────────────────────────────────────────────────────
        share_col    = ui.element("div").classes("w-full")
        upload_col   = ui.element("div").classes("w-full")
        download_col = ui.element("div").classes("w-full")
        trash_col    = ui.element("div").classes("w-full")

        with share_col:
            build_file_section("Share", SHARE_DIR, with_upload=True, with_download=True,
                               anchor="share",
                               with_delete=local or state.client_delete_share)
        with upload_col:
            build_file_section("Upload only", UPLOAD_DIR, with_upload=True, with_download=False,
                               anchor="upload",
                               with_delete=local or state.client_delete_upload)
        with download_col:
            build_file_section("Download only", DOWNLOAD_DIR, with_upload=False, with_download=True,
                               anchor="download",
                               with_delete=local or state.client_delete_download)
        with trash_col:
            build_trash_section(
                can_restore=local or state.client_trash_restore,
                can_empty=local,
            )

        def apply_toggles():
            upload_col.set_visibility(state.upload_enabled)
            download_col.set_visibility(state.download_enabled)
            share_col.set_visibility(state.share_enabled)
            trash_col.set_visibility(local or state.client_trash_visible)

        ui.timer(1.0, apply_toggles)
        build_footer()


# ── 13. Manual & Changelog ────────────────────────────────────────────────────

@ui.page("/manual")
async def manual_page(request: Request):
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode(value=app.storage.user.get('theme', cfg_theme()))
    build_header(is_dark, current="manual", is_local=is_local(request))
    md_file = SCRIPT_DIR / "MANUAL.md"
    content = md_file.read_text() if md_file.exists() else "_MANUAL.md not found._"
    with ui.column().classes("w-full q-pa-md").style("max-width: 860px; margin: 0 auto"):
        with ui.card().classes("w-full"):
            ui.markdown(content)
    build_footer()

@ui.page("/changelog")
async def changelog_page(request: Request):
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode(value=app.storage.user.get('theme', cfg_theme()))
    build_header(is_dark, current="changelog", is_local=is_local(request))
    md_file = SCRIPT_DIR / "CHANGELOG.md"
    if md_file.exists():
        parts = md_file.read_text().split("\n## ")
        entries = ["## " + p.strip() for p in parts[1:] if p.strip()]
    else:
        entries = []
    with ui.column().classes("w-full q-pa-md").style("max-width: 860px; margin: 0 auto; gap: 1rem"):
        if entries:
            for entry in entries:
                with ui.card().classes("w-full"):
                    ui.markdown(entry).classes("nt-changelog-entry")
        else:
            ui.markdown("_CHANGELOG.md not found._")
    build_footer()


@ui.page("/development")
async def development_page(request: Request):
    if not is_local(request):
        ui.navigate.to(f"/?token={TOKEN}")
        return
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode(value=app.storage.user.get('theme', cfg_theme()))
    build_header(is_dark, current="development", is_local=is_local(request))
    md_file = SCRIPT_DIR / "DEVELOPMENT.md"
    with ui.column().classes("w-full q-pa-md").style("max-width: 860px; margin: 0 auto"):
        with ui.card().classes("w-full q-pa-md"):
            if md_file.exists():
                ui.markdown(md_file.read_text())
            else:
                ui.markdown("_DEVELOPMENT.md not found._")
    build_footer()


def build_footer():
    ui.separator()
    with ui.element("footer").classes("w-full q-px-md q-py-sm text-center text-caption nt-text-secondary q-mt-sm"):
        ui.html(
            f'NiceTransfer v{VERSION} &nbsp;·&nbsp; '
            f'© 2026 Joko Keuschnig &nbsp;·&nbsp; '
            f'<a href="/get?token={TOKEN}" style="color:inherit">AGPL v3</a>'
        )


@ui.page("/get")
async def get_page(request: Request):
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode(value=app.storage.user.get('theme', cfg_theme()))
    build_header(is_dark, current="get", is_local=is_local(request))
    with ui.column().classes("w-full q-pa-md").style("max-width: 860px; margin: 0 auto; gap: 1rem"):

        with ui.card().classes("w-full q-pa-md"):
            ui.label("Local source package").classes("nt-section-title text-overline text-primary")
            with ui.row().classes("items-center justify-between w-full q-mt-sm"):
                with ui.column().classes("gap-1"):
                    ui.label(f"NiceTransfer v{VERSION}").classes("text-h6")
                    ui.label("Requires Python 3.9+ · run install.sh to set up") \
                        .classes("text-caption nt-text-secondary")
                ui.button('Download source', icon='download') \
                    .props(f'href="/download/source?token={TOKEN}" tag=a unelevated color=primary')
            ui.separator().classes("q-my-sm")
            ui.label(
                "The source package contains all files needed to install and run NiceTransfer. "
                "Served directly from this device — no internet required to download. "
                "Includes nicetransfer.py, install.sh, the manual, changelog, development notes, AI guides, and LICENSE."
            ).classes("text-body2 nt-text-secondary")

        with ui.card().classes("w-full q-pa-md"):
            ui.label("GitHub").classes("nt-section-title text-overline text-primary")
            with ui.row().classes("items-center justify-between w-full q-py-xs"):
                with ui.column().style("gap: 0"):
                    ui.label("NiceTransfer releases").classes("text-body2")
                    ui.label("Tagged versions — tested and recommended for stable use") \
                        .classes("text-caption nt-text-secondary")
                ui.button("Open", icon="open_in_new") \
                    .props('href="https://github.com/joko-zauberzeug/nicetransfer/releases" target=_blank flat dense no-caps').classes("nt-text-secondary")
            ui.separator().props("spaced=false")
            with ui.row().classes("items-center justify-between w-full q-py-xs"):
                with ui.column().style("gap: 0"):
                    ui.label("NiceTransfer main branch").classes("text-body2")
                    ui.label("Rolling — always the latest code") \
                        .classes("text-caption nt-text-secondary")
                ui.button("Open", icon="open_in_new") \
                    .props('href="https://github.com/joko-zauberzeug/nicetransfer" target=_blank flat dense no-caps').classes("nt-text-secondary")

        with ui.card().classes("w-full q-pa-md"):
            ui.label("Platforms").classes("nt-section-title text-overline text-primary")
            for platform, icon in [
                ("macOS (.app bundle)",  "laptop_mac"),
                ("Linux (AppImage)",     "computer"),
                ("Android (Termux)",     "phone_android"),
            ]:
                with ui.row().classes("items-center justify-between w-full q-py-xs"):
                    with ui.row().classes("items-center").style("gap: 0.5rem"):
                        ui.icon(icon).classes("nt-text-disabled")
                        ui.label(platform).classes("nt-text-disabled")
                    ui.label("Coming soon. Maybe.").classes("text-caption nt-text-disabled")
                ui.separator().props("spaced=false")

        with ui.card().classes("w-full q-pa-md"):
            ui.label("License").classes("nt-section-title text-overline text-primary")
            with ui.row().classes("items-center justify-between w-full q-py-xs"):
                with ui.row().classes("items-center").style("gap: 0.5rem"):
                    ui.icon("gavel").classes("nt-text-secondary")
                    ui.label("GNU Affero General Public License v3.0")
                ui.button("View in new tab", icon="open_in_new") \
                    .props(f'href="/download/license?token={TOKEN}" target=_blank flat dense no-caps').classes("nt-text-secondary")

    build_footer()


# ── 14. Download & Preview routes ─────────────────────────────────────────────

_SOURCE_FILES = ["nicetransfer.py", "nicetransfer.css", "install.sh",
                 "MANUAL.md", "CHANGELOG.md", "DEVELOPMENT.md",
                 "llms.md", "llms-nicetransfer.md", "CLAUDE.md",
                 "LICENSE", "README.md"]

@app.get("/download/source")
async def download_source():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in _SOURCE_FILES:
            path = SCRIPT_DIR / name
            if path.exists():
                zf.write(path, f"nicetransfer/{name}")
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="nicetransfer-v{VERSION}.zip"'},
    )

@app.get("/download/license")
async def download_license():
    lic = SCRIPT_DIR / "LICENSE"
    content = lic.read_text() if lic.exists() else "LICENSE file not found."
    return PlainTextResponse(content)

@app.post("/shutdown")
async def http_shutdown():
    """Trigger a clean server shutdown (token required via middleware)."""
    PID_FILE.unlink(missing_ok=True)
    app.shutdown()
    return {"status": "shutting down"}

def _resolve_file(folder, filename):
    dir_map = {d.name: d for d in [UPLOAD_DIR, DOWNLOAD_DIR, SHARE_DIR]}
    directory = dir_map.get(folder)
    if not directory: return None, None
    file_path = directory / filename
    if not file_path.exists() or not file_path.is_file(): return None, None
    try:
        file_path.resolve().relative_to(directory)
    except ValueError:
        return None, None
    return directory, file_path

@app.get("/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    _, file_path = _resolve_file(folder, filename)
    if not file_path: return Response("File not found", status_code=404)
    return FileResponse(path=file_path, filename=filename,
                        media_type="application/octet-stream")

@app.get("/preview/{folder}/{filename}")
async def preview_file(folder: str, filename: str):
    _, file_path = _resolve_file(folder, filename)
    if not file_path: return Response("File not found", status_code=404)
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp",
                ".bmp": "image/bmp", ".svg": "image/svg+xml"}
    mime = mime_map.get(file_path.suffix.lower(), "image/jpeg")
    return FileResponse(path=file_path, media_type=mime)


# ── 15. AI discovery endpoints ────────────────────────────────────────────────

@app.get("/.well-known/mcp/server-card.json")
async def mcp_server_card():
    sections = [s for s, on in [("share",    state.share_enabled),
                                 ("upload",   state.upload_enabled),
                                 ("download", state.download_enabled)] if on]
    return JSONResponse({
        "name":        "NiceTransfer",
        "description": "Local file transfer hub — upload, download and share files on the local network via browser.",
        "version":     VERSION,
        "url":         f"http://{LOCAL_IP}:{PORT}",
        "mcp": {
            "endpoint":       f"http://{LOCAL_IP}:{PORT}/mcp",
            "transport":      "streamable-http",
            "authentication": {"type": "query-param", "param": "token"},
        },
        "capabilities": {
            "sections": sections,
            "tools":    ["get_status", "list_files", "upload_file", "download_file"],
        },
    })

def _llms_body():
    sections = [s for s, on in [("share",    state.share_enabled),
                                 ("upload",   state.upload_enabled),
                                 ("download", state.download_enabled)] if on]
    mcp_url  = f"http://{LOCAL_IP}:{PORT}/mcp?token={TOKEN}"
    llms_url = f"http://{LOCAL_IP}:{PORT}/llms.txt?token={TOKEN}"
    return (
        f"# NiceTransfer\n\n"
        f"Local file transfer hub. Transfer files between devices on the same Wi-Fi network via browser.\n"
        f"This file is intended for AI assistants. It describes how to interact with NiceTransfer programmatically.\n\n"

        f"## Connecting\n\n"
        f"NiceTransfer exposes an MCP (Model Context Protocol) endpoint over Streamable HTTP.\n"
        f"No browser, no manual steps — the AI can transfer files directly via tool calls.\n\n"
        f"### If the AI received a URL from a human\n\n"
        f"Fetch the URL. The HTML <head> contains:\n\n"
        f"  <meta name=\"mcp-server\" content=\"http://...:{PORT}/mcp?token=<token>\">\n\n"
        f"Use that content value as the MCP endpoint.\n\n"
        f"### MCP endpoint (this server)\n\n"
        f"  {mcp_url}\n\n"
        f"Transport : Streamable HTTP (MCP spec 2025-03-26)\n"
        f"Auth      : token is already embedded in the URL above as ?token=...\n\n"

        f"## Active sections\n\n"
        f"{', '.join(sections) if sections else 'none (all sections currently disabled)'}\n\n"

        f"## Tools\n\n"
        f"get_status()\n"
        f"  Returns: server URL, active sections\n\n"
        f"list_files(section)\n"
        f"  section: 'upload' | 'download' | 'share'\n"
        f"  Returns: list of {{name, size, modified}}\n\n"
        f"upload_file(section, filename, content_base64)\n"
        f"  section: 'upload' | 'download' | 'share'\n"
        f"  content_base64: base64-encoded file content\n"
        f"  Returns: {{saved_as, bytes}}\n\n"
        f"download_file(section, filename)\n"
        f"  section: 'upload' | 'download' | 'share'\n"
        f"  Returns: {{filename, content_base64, bytes}}\n\n"
        f"shutdown_server()\n"
        f"  Shuts down NiceTransfer cleanly. Use when done.\n"
        f"  Returns: {{status: 'shutting down'}}\n\n"

        f"## Pages\n\n"
        f"  /          — main transfer interface (sections, file lists, control panel)\n"
        f"  /manual    — user manual\n"
        f"  /changelog — version history\n"
        f"  /get       — source code download (AGPL v3 compliance)\n\n"

        f"## Source & license\n\n"
        f"NiceTransfer is AGPL v3. Source download endpoints (token required):\n\n"
        f"  /download/source  — ZIP of all source files\n"
        f"  /download/license — plain text LICENSE\n\n"

        f"## Notes\n\n"
        f"- The token regenerates on each server start unless a fixed token is set in config.toml.\n"
        f"- Always fetch this file fresh ({llms_url}) to get the current MCP URL.\n"
        f"- Files in 'upload' are meant to be sent to the server; 'download' to be fetched from it.\n"
        f"- 'share' is bidirectional.\n"
    )

@app.get("/llms.txt")
async def llms_txt():
    return PlainTextResponse(_llms_body())

@app.get("/llms-local.txt")
async def llms_local_txt(request: Request):
    if not is_local(request):
        return PlainTextResponse("Not available for external clients.\n", status_code=403)
    llms_local_url = f"http://127.0.0.1:{PORT}/llms-local.txt?token={TOKEN}"
    local_section = (
        f"## If the AI started NiceTransfer\n\n"
        f"The startup banner printed to stdout contains:\n\n"
        f"  mcp     : http://127.0.0.1:{PORT}/mcp?token=<token>\n"
        f"  llms    : http://127.0.0.1:{PORT}/llms.txt?token=<token>\n"
        f"  llms+   : {llms_local_url}\n\n"
        f"Extract the token from any of these URLs.\n"
        f"Fetch llms-local.txt immediately after start to get full operating instructions.\n"
        f"Keep the token for the entire session — do not re-extract it on every step.\n"
        f"Never redirect startup output to /tmp or other world-readable files — the banner contains the token.\n\n"
        f"## Checking if NiceTransfer is already running\n\n"
        f"NiceTransfer writes a PID file on startup and deletes it on exit:\n\n"
        f"  {SCRIPT_DIR}/.nicetransfer.pid\n\n"
        f"Contents: `pid=<PID>\\nport=<PORT>`. If the file exists and the process is alive,\n"
        f"NiceTransfer refuses to start from this directory. Multiple instances from different\n"
        f"directories are allowed.\n\n"
        f"Before starting, check:\n\n"
        f"  cat {SCRIPT_DIR}/.nicetransfer.pid 2>/dev/null\n\n"
        f"If the file exists, NiceTransfer is already running on that port — use it.\n"
        f"If the file does not exist (or the PID is dead), start normally.\n\n"
        f"## Stopping NiceTransfer\n\n"
        f"Preferred — MCP tool (if connected) or HTTP endpoint:\n\n"
        f"  shutdown_server()   ← MCP tool\n"
        f"  curl -s -X POST 'http://127.0.0.1:{PORT}/shutdown?token={TOKEN}'\n\n"
        f"Both trigger a clean NiceGUI lifecycle shutdown (exit 0).\n"
        f"Ctrl+C in the terminal where run.sh is running also shuts down cleanly.\n\n"
        f"Last resort — kill the process directly:\n\n"
        f"  pkill -f nicetransfer.py 2>/dev/null\n\n"
        f"## Restarting NiceTransfer\n\n"
        f"Stop first, wait until gone, then start:\n\n"
        f"  curl -s -X POST 'http://127.0.0.1:{PORT}/shutdown?token={TOKEN}'\n"
        f"  while pgrep -f nicetransfer.py > /dev/null 2>&1; do sleep 0.1; done\n"
        f"  bash {SCRIPT_DIR}/run.sh\n\n"
        f"Do not use a fixed sleep — wait for the process to actually exit.\n"
        f"Expected exit codes on the previous background task:\n"
        f"  0   — clean shutdown (HTTP endpoint, Ctrl+C, or timeout)\n"
        f"  143 (SIGTERM) — process was killed by pkill, it is gone\n"
        f"  144 (SIGURG)  — task manager timed out, NiceTransfer keeps running (Python ignores SIGURG)\n\n"
    )
    return PlainTextResponse(local_section + _llms_body())


# ── 16. MCP server ───────────────────────────────────────────────────────────

if HAS_MCP:
    # streamable_http_path="/" puts the MCP route at / inside the sub-app.
    # When mounted at /mcp, Starlette strips the /mcp prefix so the sub-app
    # sees / — which matches the route.  Default "/mcp" would see / and 404.
    #
    # host="0.0.0.0" disables FastMCP's auto DNS-rebinding protection that
    # only allows localhost — our token_guard middleware handles auth instead.
    _mcp = FastMCP(
        "NiceTransfer",
        streamable_http_path="/",
        host="0.0.0.0",
        instructions=(
            "NiceTransfer is a local file transfer hub. "
            "Use list_files to see what's available, upload_file to send files, "
            "download_file to retrieve them. "
            "Valid sections: 'upload', 'download', 'share'."
        ),
    )

    _SECTION_MAP = lambda: {
        "upload":   UPLOAD_DIR,
        "download": DOWNLOAD_DIR,
        "share":    SHARE_DIR,
    }

    @_mcp.tool()
    def get_status() -> dict:
        """Return server status: network URL and which sections are active."""
        return {
            "url": ACCESS_URL,
            "sections": {
                "upload":   state.upload_enabled,
                "download": state.download_enabled,
                "share":    state.share_enabled,
            },
        }

    @_mcp.tool()
    def list_files(section: str) -> list[dict]:
        """List files in a section ('upload', 'download', or 'share')."""
        directory = _SECTION_MAP().get(section)
        if not directory:
            raise ValueError(f"Unknown section '{section}'. Use upload, download, or share.")
        return [{"name": e["name"], "size": e["size"], "modified": e["time"]}
                for e in file_entries(directory)]

    @_mcp.tool()
    def upload_file(section: str, filename: str, content_base64: str) -> dict:
        """Upload a file to a section. content_base64 must be base64-encoded file content."""
        directory = _SECTION_MAP().get(section)
        if not directory:
            raise ValueError(f"Unknown section '{section}'. Use upload, download, or share.")
        dest = safe_filename(filename, directory)
        if dest is None:
            raise ValueError(f"Invalid filename: {filename!r}")
        if dest.exists():
            ts   = datetime.now().strftime("%H%M%S")
            stem = dest.stem
            suf  = dest.suffix
            dest = directory / f"{stem}_{ts}{suf}"
        dest.write_bytes(base64.b64decode(content_base64))
        return {"saved_as": dest.name, "bytes": dest.stat().st_size}

    @_mcp.tool()
    def download_file(section: str, filename: str) -> dict:
        """Download a file from a section. Returns base64-encoded content."""
        _, file_path = _resolve_file(section, filename)
        if not file_path:
            raise ValueError(f"File not found: {filename!r} in section '{section}'.")
        data = file_path.read_bytes()
        return {
            "filename":       filename,
            "content_base64": base64.b64encode(data).decode(),
            "bytes":          len(data),
        }

    @_mcp.tool()
    def shutdown_server() -> dict:
        """Shut down the NiceTransfer server cleanly."""
        PID_FILE.unlink(missing_ok=True)
        app.shutdown()
        return {"status": "shutting down"}

    # Build the Starlette sub-app (this also initialises _mcp._session_manager).
    _mcp_sub = _mcp.streamable_http_app()
    app.mount("/mcp", _mcp_sub)

    # Starlette's Mount does not propagate lifespan events to the sub-app, so
    # the session manager's task group (required for every request) would never
    # start.  We enter the run() context in on_startup and exit in on_shutdown.
    _mcp_ctx = None

    async def _mcp_startup():
        global _mcp_ctx
        _mcp_ctx = _mcp.session_manager.run()
        await _mcp_ctx.__aenter__()

    async def _mcp_shutdown():
        global _mcp_ctx
        if _mcp_ctx is not None:
            try:
                await _mcp_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            _mcp_ctx = None

    app.on_startup(_mcp_startup)
    app.on_shutdown(_mcp_shutdown)


# ── 17. Banner & Start ────────────────────────────────────────────────────────

_MCP_URL = f"http://127.0.0.1:{PORT}/mcp?token={TOKEN}"

_banner_lines = [
    f"NiceTransfer v{VERSION}",
    None,
    f"upload  : {UPLOAD_DIR}",
    f"download: {DOWNLOAD_DIR}",
    f"share   : {SHARE_DIR}",
    None,
    f"local   : http://127.0.0.1:{PORT}/?token={TOKEN}",
    f"network : {ACCESS_URL}",
    f"mcp     : {_MCP_URL}",
    f"llms    : http://127.0.0.1:{PORT}/llms.txt?token={TOKEN}",
    f"llms+   : http://127.0.0.1:{PORT}/llms-local.txt?token={TOKEN}",
    *([f"timeout : {TIMEOUT_MIN} min"] if TIMEOUT_MIN > 0 else []),
    None,
    "Scan QR code in browser · Ctrl+C to quit",
]
_w = max(len(l) for l in _banner_lines if l is not None)
_bar = "─" * (_w + 4)
print(f"┌{_bar}┐")
for _l in _banner_lines:
    if _l is None:
        print(f"├{_bar}┤")
    else:
        print(f"│  {_l:<{_w}}  │")
print(f"└{_bar}┘")
print()

if NO_NETWORK:
    print("⚠  No network detected — other devices cannot connect.")
    print("   To create a hotspot:")
    print(hotspot_hint_text())
    print()

_start_time     = _time.time()
_timeout_active = TIMEOUT_MIN   # mutable; 0 = no timeout

def _timeout_shutdown():
    PID_FILE.unlink(missing_ok=True)
    print(f"\n⏱  Timeout reached ({_timeout_active} min) — shutting down.")
    app.shutdown()
    threading.Timer(5, lambda: os._exit(143)).start()

_timeout_fired = False   # prevents double-firing; reset when user sets new timeout

def _start_shutdown_timer():
    global _timeout_fired
    _timeout_fired = False  # new timeout set — arm the watchdog again

def _timeout_watchdog():
    global _timeout_fired
    if _timeout_active > 0 and not _timeout_fired:
        if (_time.time() - _start_time) >= _timeout_active * 60:
            _timeout_fired = True
            _timeout_shutdown()

app.on_startup(lambda: app.timer(1, _timeout_watchdog))

def _setup_sigterm_cleanup():
    prev = signal.getsignal(signal.SIGTERM)
    def _handler(sig, frame):
        PID_FILE.unlink(missing_ok=True)
        if callable(prev):
            prev(sig, frame)
        else:
            raise SystemExit(0)
    signal.signal(signal.SIGTERM, _handler)

app.on_startup(_setup_sigterm_cleanup)

# ── 18. Update check ──────────────────────────────────────────────────────────

_update_notice: dict = {}   # filled by background check; read by UI
_update_checked = False     # True once any check has completed

def _sync_check_updates(force: bool = False):
    global _update_checked
    import urllib.request, json as _j, importlib.metadata

    _update_notice.clear()

    if UPDATE_CHECK_ON_START or force:
        try:
            if UPDATE_CHANNEL == "rolling":
                url = "https://raw.githubusercontent.com/joko-zauberzeug/nicetransfer/main/nicetransfer.py"
                with urllib.request.urlopen(url, timeout=5) as r:
                    src = r.read().decode()
                import re as _re
                m = _re.search(r'^VERSION\s*=\s*"([^"]+)"', src, _re.MULTILINE)
                latest_ver = m.group(1) if m else None
                channel_label = "rolling/main"
            else:
                with urllib.request.urlopen(
                    "https://api.github.com/repos/joko-zauberzeug/nicetransfer/tags",
                    timeout=5
                ) as r:
                    tags       = _j.loads(r.read())
                    latest_tag = tags[0]["name"] if tags else None
                    latest_ver = latest_tag.lstrip("v") if latest_tag else None
                channel_label = "stable"
            if latest_ver and latest_ver != VERSION:
                _update_notice["nt"] = {"local": VERSION, "latest": latest_ver, "channel": channel_label}
                print(f"⬆  NiceTransfer v{latest_ver} available [{channel_label}]  (run ./upgrade.sh to update)")
        except Exception:
            pass

    if NOTIFY_DEPS or force:
        try:
            with urllib.request.urlopen(
                "https://pypi.org/pypi/nicegui/json", timeout=5
            ) as r:
                latest_ng = _j.loads(r.read())["info"]["version"]
            local_ng = importlib.metadata.version("nicegui")
            if latest_ng != local_ng:
                _update_notice["nicegui"] = {"local": local_ng, "latest": latest_ng}
                print(f"⬆  NiceGUI {latest_ng} available (installed: {local_ng})"
                      f" — NiceTransfer v{VERSION} was tested with installed version")
        except Exception:
            pass

    _update_checked = True

async def _check_updates(force: bool = False):
    await asyncio.to_thread(_sync_check_updates, force)

if UPDATE_CHECK_ON_START or NOTIFY_DEPS:
    app.on_startup(lambda: background_tasks.create(_check_updates()))

app.on_startup(lambda: threading.Timer(
    1.5, lambda: webbrowser.open(f"http://localhost:{PORT}/?token={TOKEN}")).start())

PID_FILE.write_text(f"pid={os.getpid()}\nport={PORT}\n")
atexit.register(lambda: PID_FILE.unlink(missing_ok=True))

try:
    ui.run(host="0.0.0.0", port=PORT, title="NiceTransfer",
           favicon="📁", dark=True, reload=False, show=False,
           storage_secret="nicetransfer-storage")
except KeyboardInterrupt:
    pass
