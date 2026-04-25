# Platform distribution — notes

Ideas and feasibility assessment for distributing NiceTransfer beyond the current
git clone + run.sh workflow.

---

## macOS — .app bundle

**Approach:** Package with `py2app` or `PyInstaller` into a self-contained `.app` bundle.
Python and all dependencies are embedded — no Python installation required on the target machine.

- Double-click → server starts → browser opens automatically
- Can live in the Dock, can be set to autostart
- NiceGUI's `native=True` mode (via `pywebview`) could open the control panel in a native
  webview window instead of the browser — other devices still connect via browser as usual
- Distribute via GitHub Releases as a notarized `.app` (notarization avoids the macOS
  Gatekeeper "unidentified developer" warning)

**Mac App Store:** Not realistic. App Store sandboxing prohibits binding a local network
server and accessing arbitrary file system paths — exactly what NiceTransfer does.

**Effort:** Moderate. PyInstaller build + notarization workflow.

---

## Linux — AppImage

**Approach:** Build a self-contained `.AppImage` using PyInstaller + appimagetool.
Runs on any major distribution without installation or root.

- Single file, `chmod +x`, double-click (or run from terminal)
- Same GitHub Releases workflow as macOS

**Desktop integration:** A `.desktop` file adds NiceTransfer to the application menu
(GNOME, KDE, etc.) — useful for users who install via git clone.

**Flatpak / Snap:** More involved but realistic. Flatpak on Flathub would give
NiceTransfer an "app store" presence on Linux. Sandboxing permissions for network
binding and file access are configurable and less restrictive than Apple's.

**Effort:** AppImage — moderate (same PyInstaller build, different packaging step).
Flatpak — higher effort, requires a Flatpak manifest and Flathub submission.

---

## Android — Termux

**Approach:** Run NiceTransfer inside Termux (a Linux terminal emulator for Android).

```bash
pkg install python
pip install nicegui
# clone + run as usual
```

- Android device becomes the server; other devices connect via QR code as usual
- The Android browser connects to localhost:7777 for the control panel
- File access requires `termux-setup-storage` for Downloads etc.
- `install.sh` may need minor adjustments (shell compatibility)

**Limitations:**
- Terminal must stay open (or use Termux:Boot for background start)
- Android 12+ may restrict background processes
- Not suitable for non-technical users

**Play Store:** Not realistic with the current architecture.

**Effort:** Low for basic support (test + document). High for a polished Android experience.

---

## Recommended next steps

1. **AppImage + .app via GitHub Actions** — single CI pipeline builds both on push,
   attaches artifacts to GitHub Releases. Most impact for least ongoing effort.
2. **`.desktop` file** — small addition for Linux users who install manually.
3. **Flatpak** — consider once the core distribution story is stable.
4. **Android** — document Termux setup in the Manual for interested users.
