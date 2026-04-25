#!/usr/bin/env python3
"""
nicetransfer v0.5 — local file transfer via browser
NiceGUI 3.x
"""

import sys, subprocess, importlib, socket, secrets, argparse, webbrowser, threading, base64
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
    if sys.version_info < (3,11) and not _pkg_installed("tomli"): needed.append("tomli")
    if needed:
        print("nicetransfer: installing missing dependencies:")
        for p in needed: _install(p)
        print()

check_deps()


# ── 2. Imports ────────────────────────────────────────────────────────────────

from nicegui import ui, app, events
from starlette.requests import Request
from starlette.responses import FileResponse, Response, HTMLResponse

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


# ── 3. Paths & Static ─────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "config.toml"
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
PORT  = ARGS.port or cfg_int("server", "port", 7777)
TOKEN = ARGS.token or cfg_str("server", "token", "") or secrets.token_urlsafe(12)

for d in [UPLOAD_DIR, DOWNLOAD_DIR, SHARE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── 6. State ──────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.upload_enabled   = not ARGS.no_upload
        self.download_enabled = not ARGS.no_download
        self.share_enabled    = not ARGS.no_share

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


# ── 8. Token middleware ───────────────────────────────────────────────────────

@app.middleware("http")
async def token_guard(request, call_next):
    path = request.url.path
    skip = ["/_nicegui", "/static", "/favicon", "/download", "/nt-static", "/preview"]
    if any(path.startswith(p) for p in skip): return await call_next(request)
    if request.headers.get("upgrade","").lower() == "websocket": return await call_next(request)
    if is_local(request): return await call_next(request)
    if request.query_params.get("token","") != TOKEN:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;background:#1d2027;color:#ff6d00;"
            "display:flex;align-items:center;justify-content:center;height:100vh'>"
            "<div style='text-align:center'><div style='font-size:2rem'>⛔</div>"
            "<div>Access denied — scan QR code</div></div></body></html>",
            status_code=403)
    return await call_next(request)


# ── 9. CSS ────────────────────────────────────────────────────────────────────

NT_ORANGE = "#FF6D00"

CSS = """<style>
  .nt-logo {
    color: #FF6D00 !important;
    font-weight: 700;
    font-size: 2rem;
    text-decoration: none;
    letter-spacing: -0.5px;
  }
  /* Section title bar */
  .nt-section-header {
    background: var(--q-primary) !important;
    border-radius: 4px 4px 0 0;
    min-height: 48px;
  }
  .nt-section-title {
    color: #FF6D00 !important;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .nt-section { scroll-margin-top: 64px; }
  .nt-qr { display: flex; justify-content: center; margin: 1rem 0; }
  .nt-qr svg { background: white; padding: 10px; border-radius: 4px; width: 220px; height: 220px; }
  .nt-url { font-family: monospace; font-size: 0.9rem; word-break: break-all; }
  .nt-dl-link { text-decoration: none; color: inherit; }
  .nt-dl-link:hover { text-decoration: underline; }
  /* Drag & drop zone */
  .nt-drop-zone { transition: color 0.15s, background 0.15s; }
  .q-uploader--dnd .nt-drop-zone { color: #FF6D00 !important; background: rgba(255,109,0,0.06); }
  /* Upload widget full width */
  .nt-uploader { width: 100% !important; max-width: 100% !important; }
  .nt-uploader .q-uploader { width: 100% !important; max-width: 100% !important; box-shadow: none !important; }
</style>"""


# ── 10. File section ──────────────────────────────────────────────────────────

def make_rows(entries, with_download):
    rows = []
    for e in entries:
        rows.append({
            "name":        e["name"],
            "size":        e["size"],
            "time":        e["time"],
            "is_img":      e["is_img"],
            "dl_url":      f"/download/{e['dir']}/{e['name']}" if with_download else "",
            "preview_url": f"/preview/{e['dir']}/{e['name']}"  if e["is_img"]   else "",
        })
    return rows

def build_file_section(title: str, directory: Path, with_upload: bool, with_download: bool, anchor: str):
    entries = file_entries(directory)
    rows = make_rows(entries, with_download)
    columns = [
        {"name": "name", "label": "File", "field": "name", "sortable": True,  "align": "left"},
        {"name": "size", "label": "Size", "field": "size", "sortable": False, "align": "right"},
        {"name": "time", "label": "Date", "field": "time", "sortable": True,  "align": "right"},
    ]

    with ui.card().classes("w-full q-pa-none nt-section").props(f'id="{anchor}"'):

        if with_upload:
            # ui.upload with custom header slot — Quasar QUploader supports replacing
            # the header entirely. We put our title + pick-files button there.
            # The list slot is emptied — we show files in our own table below.
            async def handle_upload(e: events.UploadEventArguments, d=directory):
                dest = await save_upload(e, d)
                ui.notify(f"✓ {dest.name}", type="positive")
                new_rows = make_rows(file_entries(d), with_download)
                table.rows = new_rows
                table.update()

            uploader = ui.upload(
                on_upload=handle_upload,
                multiple=True,
                auto_upload=True,
            ).classes("w-full").props("flat")

            # Replace the uploader header with our own design
            # Note: NiceGUI passes slot props as 'props' variable in add_slot templates
            uploader.add_slot("header", f"""
                <div class="column w-full">
                  <div class="nt-section-header row items-center justify-between q-px-md q-py-sm w-full">
                    <div class="nt-section-title">{title}</div>
                    <q-btn v-if="props.canAddFiles" flat dense color="grey-5"
                           icon="add" label="Select files">
                      <q-uploader-add-trigger />
                    </q-btn>
                  </div>
                  <div class="nt-drop-zone row items-center justify-center text-grey-5 q-pa-sm"
                       style="font-size:0.82rem; min-height:36px; border-bottom:1px dashed #444">
                    <q-icon name="upload_file" size="xs" class="q-mr-xs" />
                    drop files here
                  </div>
                </div>
            """)
            # Empty list slot — we handle display ourselves
            uploader.add_slot("list", "")

        else:
            # No upload — just a header bar
            with ui.row().classes("nt-section-header items-center q-px-md q-py-sm w-full"):
                ui.label(title).classes("nt-section-title")

        ui.separator()

        # Image preview dialog — Quasar teleports this to <body>, so it overlays everything
        with ui.dialog() as img_dialog, ui.card().style(
                "background:#2a2a2a; padding:0; max-width:95vw; position:relative; overflow:hidden; box-shadow:none"):
            preview_html = ui.html("").style("display:block")
            ui.button("✕", on_click=img_dialog.close) \
                .props("flat color=white round dense size=sm") \
                .classes("absolute-top-right q-ma-xs")

        _mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                     ".gif": "image/gif", ".webp": "image/webp",
                     ".bmp": "image/bmp", ".svg": "image/svg+xml"}

        def handle_preview(ev):
            url: str = ev.args                         # "/preview/<folder>/<name>"
            parts = url.lstrip("/").split("/")          # ["preview", folder, name]
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

        with ui.column().classes("w-full q-pa-sm").style("gap: 0.5rem"):
            search = ui.input(placeholder="Search...").props("dense outlined clearable").classes("w-full")

            table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props("dense flat")
            search.bind_value_to(table, "filter")

            table.on("preview", handle_preview)
            table.add_slot("body-cell-name", """
                <q-td :props="props">
                    <q-btn v-if="props.row.is_img" flat dense round size="xs"
                           icon="image" class="q-mr-xs"
                           style="color: #FF6D00"
                           @click.stop="$parent.$emit('preview', props.row.preview_url)" />
                    <q-btn v-if="props.row.dl_url" flat dense round size="xs"
                           icon="file_download" color="grey-5" class="q-mr-xs"
                           tag="a" :href="props.row.dl_url" @click.stop />
                    <span>{{ props.row.name }}</span>
                </q-td>
            """)



# ── 11. Shared header ─────────────────────────────────────────────────────────

def build_header(is_dark, section_links=None, current=""):
    with ui.header().classes("items-center q-px-md q-py-sm").props("elevated"):
        ui.link("nicetransfer", "/").classes("nt-logo")

        if section_links:
            ui.separator().props("vertical color=grey-7").classes("q-mx-sm")
            tab_refs = {}
            with ui.tabs().props("dense no-caps").classes("text-grey-4"):
                for label, anchor in section_links:
                    t = ui.tab(label).on("click",
                        js_handler=f"() => document.getElementById('{anchor}')?.scrollIntoView({{behavior:'smooth'}})")
                    tab_refs[anchor] = t

            # Map anchor to state key
            anchor_to_key = {
                "upload":   "upload_enabled",
                "download": "download_enabled",
                "share":    "share_enabled",
            }
            def update_tabs():
                for anchor, tab in tab_refs.items():
                    key = anchor_to_key.get(anchor)
                    if key:
                        tab.set_visibility(getattr(state, key, True))

            ui.timer(1.0, update_tabs)

        ui.space()

        icon = "dark_mode" if is_dark.value is True else ("light_mode" if is_dark.value is False else "brightness_auto")
        theme_btn = ui.button(icon=icon).props("flat round dense color=grey-4")

        def toggle_theme():
            if is_dark.value is True:
                is_dark.set_value(None); theme_btn.props("icon=brightness_auto")
            elif is_dark.value is None:
                is_dark.set_value(False); theme_btn.props("icon=light_mode")
            else:
                is_dark.set_value(True); theme_btn.props("icon=dark_mode")

        theme_btn.on("click", toggle_theme)

        with ui.dropdown_button(icon="menu").props("flat round dense color=grey-4 no-caps"):
            with ui.list().props("dense"):
                ui.item("Manual",    on_click=lambda: ui.navigate.to("/manual"))
                ui.item("Changelog", on_click=lambda: ui.navigate.to("/changelog"))


# ── 12. Main page ─────────────────────────────────────────────────────────────

@ui.page("/")
async def index(request: Request):
    local = is_local(request)
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode()

    # Build header with all possible tabs — visibility controlled reactively
    build_header(is_dark, section_links=[
        ("Upload only",   "upload"),
        ("Download only", "download"),
        ("Share",         "share"),
    ])

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

                if no_net:
                    with ui.card().classes("w-full").style("border-left: 4px solid #FF6D00"):
                        ui.label("⚠  No network — other devices cannot connect") \
                            .classes("text-weight-bold q-mb-sm") \
                            .style("color: #FF6D00")
                        ui.markdown(hotspot_hint_md())

                with ui.row().classes("w-full").style("gap: 1.5rem; align-items: flex-start; flex-wrap: wrap"):

                    with ui.card().style("flex: 1; min-width: 260px"):
                        ui.label("Connection").classes("text-overline text-grey")
                        ui.separator()
                        if no_net:
                            ui.label("Only accessible on this device") \
                                .classes("text-grey text-caption q-mt-sm")
                        else:
                            ui.label(url).classes("nt-url")
                            if qr:
                                with ui.element("div").classes("nt-qr"):
                                    ui.html(qr)
                                ui.label("Scan QR → browser opens") \
                                    .classes("text-caption text-grey text-center")

                    with ui.card().style("flex: 1; min-width: 260px"):
                        ui.label("Control").classes("text-overline text-grey")
                        ui.separator()
                        for label, key, path in [
                            ("Upload only",   "upload_enabled",   UPLOAD_DIR),
                            ("Download only", "download_enabled", DOWNLOAD_DIR),
                            ("Share",         "share_enabled",    SHARE_DIR),
                        ]:
                            with ui.column().classes("w-full q-py-xs").style("gap:0"):
                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label(label)
                                    _key = key
                                    ui.switch(value=getattr(state, _key),
                                        on_change=lambda e, k=_key: setattr(state, k, e.value))
                                ui.label(str(path)).classes("text-caption text-grey") \
                                    .style("word-break:break-all; margin-top:-4px")
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
        upload_col   = ui.element("div").classes("w-full")
        download_col = ui.element("div").classes("w-full")
        share_col    = ui.element("div").classes("w-full")

        with upload_col:
            build_file_section("Upload only", UPLOAD_DIR,   with_upload=True,  with_download=False, anchor="upload")
        with download_col:
            build_file_section("Download only", DOWNLOAD_DIR, with_upload=False, with_download=True,  anchor="download")
        with share_col:
            build_file_section("Share",    SHARE_DIR,    with_upload=True,  with_download=True,  anchor="share")

        def apply_toggles():
            upload_col.set_visibility(state.upload_enabled)
            download_col.set_visibility(state.download_enabled)
            share_col.set_visibility(state.share_enabled)

        ui.timer(1.0, apply_toggles)


# ── 13. Manual & Changelog ────────────────────────────────────────────────────

@ui.page("/manual")
async def manual_page(request: Request):
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode()
    build_header(is_dark, current="manual")
    md_file = SCRIPT_DIR / "MANUAL.md"
    content = md_file.read_text() if md_file.exists() else "_MANUAL.md not found._"
    with ui.column().classes("w-full q-pa-md").style("max-width: 860px; margin: 0 auto"):
        with ui.card().classes("w-full"):
            ui.markdown(content)

@ui.page("/changelog")
async def changelog_page(request: Request):
    ui.add_head_html(CSS)
    is_dark = ui.dark_mode()
    build_header(is_dark, current="changelog")
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
                    ui.markdown(entry)
        else:
            ui.markdown("_CHANGELOG.md not found._")


# ── 14. Download & Preview routes ─────────────────────────────────────────────

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


# ── 15. Banner & Start ────────────────────────────────────────────────────────

_banner_lines = [
    "nicetransfer v0.5",
    None,
    f"upload  : {UPLOAD_DIR}",
    f"download: {DOWNLOAD_DIR}",
    f"share   : {SHARE_DIR}",
    None,
    f"local   : http://127.0.0.1:{PORT}",
    f"network : {ACCESS_URL}",
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

app.on_startup(lambda: threading.Timer(
    1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start())

ui.run(host="0.0.0.0", port=PORT, title="nicetransfer",
       favicon="📁", dark=True, reload=False, show=False)
