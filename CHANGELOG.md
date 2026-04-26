# Changelog

## Visual overhaul and mobile navigation — 26. April 2026, 11:22

- Inter font self-hosted (OFL) — same typeface as nicegui.io, no external request, works offline
- Page background: subtle off-white (`#f8fafc`) in light mode; cards lift off with a soft shadow instead of hard borders
- Frosted glass header — semi-transparent with blur, adapts to light and dark mode
- Brand orange replaces Quasar blue throughout: `--q-primary` overridden, toggle switches and active indicators now orange
- All decorative horizontal lines removed — cleaner layout without visual noise
- Header icons and tabs use `grey-7` — legible on both light and dark backgrounds
- Drop zone: "Upload files or ↑ Drop files here" — "or" makes the two paths explicit
- File list icon order: download icon always first, preview icon (images only) second
- Empty file list text is now muted — less visual weight when no files are present
- Mobile header: section tabs hidden on small screens, section links added to the hamburger menu instead — nothing gets clipped

## Platform distribution notes — 25. April 2026, 23:35

- Added `PLATFORMS.md` — feasibility notes for macOS (.app bundle), Linux (AppImage, Flatpak), and Android (Termux)

→ [926553b](https://github.com/joko-zauberzeug/nicetransfer/commit/926553bfa419bac86d93046ad70f3396e797c89c)

## Manual update — 25. April 2026, 23:15

- NiceTransfer renamed consistently throughout (was nicetransfer)
- Built on [NiceGUI](https://nicegui.io) by Zauberzeug GmbH — mentioned in the intro
- Requirements clarified: only Python 3.9+ needed manually, all other dependencies (including NiceGUI) installed automatically by `./install.sh`
- Starting section: corrected default comment, added note that CLI flags override config
- Control panel: emoji replaced with description, ZIP download and multi-file selection documented
- Sections table simplified to ✓/— with a plain explanation — removes the ambiguous "Everyone vs. Clients" wording
- Features list updated: live sync and ZIP download added

→ [4b7428a](https://github.com/joko-zauberzeug/nicetransfer/commit/4b7428aa0f67718b1c2e0faab569fa7e968fc0ca)

## Live sync, config defaults, naming and polish — 25. April 2026, 22:38

- File list updates automatically on all connected clients within 3 seconds when any client uploads — no manual refresh needed
- New `[ui]` section in `config.toml`: set default theme (`auto` / `light` / `dark`) and which sections are shown on startup
- Default out of the box: Auto theme, Share section only
- Renamed to **NiceTransfer** (capital N and T) in logo, browser title, and terminal banner
- Section titles no longer forced uppercase — consistent with the control panel labels
- "Upload Files" → "Upload files" — consistent sentence case with "Drop files here"
- Removed the vertical separator between logo and navigation tabs
- CSS link gets a timestamp on each server start — no more stale browser cache after updates

→ [e2a329e](https://github.com/joko-zauberzeug/nicetransfer/commit/e2a329ebb9d7bc54f1dfa31d374eac6187093be4)

## UI polish: multi-select ZIP download, consistent sizing, CSS extracted — 25. April 2026, 21:43

- Checkboxes in the file list for multi-file selection — native Quasar `selection=multiple`
- Select-all checkbox in the table header; ZIP download button in the same row (grey when nothing selected, orange when active)
- Clicking the ZIP button downloads all selected files as a single archive named after the folder
- Per-file download icons now deep-orange — consistent with the active ZIP button
- Section titles centered in the header bar
- Drop zone: "Upload Files" button and "Drop files here" text grouped and centered together
- Removed the separator line and dead whitespace between the upload zone and the file table
- CSS moved to `nicetransfer.css`; brand color defined as `--nt-orange` CSS variable — single source of truth
- Typography switched to Quasar scale: section titles use `text-h6`, drop zone text `text-body2`, upload button default size

→ [36c7ddb](https://github.com/joko-zauberzeug/nicetransfer/commit/36c7ddbf25402f69b6d74ea82b680c1f588f765e)

## Drag & drop, image preview, color consistency — 25. April 2026, 14:53

- Drag & drop files directly onto the upload zone — visual highlight while dragging
- Image preview via NiceGUI dialog with base64 data URI — no new tab, no download dialog in Firefox
- File list: separate icon buttons for preview (🖼) and download (⬇), filename as plain text — prevents accidental double-tap on mobile
- Root cause of the Firefox download bug: preview icon and filename download link were adjacent tap targets
- Section title color unified to `#FF6D00` via `.nt-section-title` CSS class — consistent with the logo orange
- Preview dialog: dark gray background, no padding, no border

→ [e1805e6](https://github.com/joko-zauberzeug/nicetransfer/commit/e1805e68c04a6448566ff6615b6d2556850c0d74)

## README trimmed, Manual completed — 25. April 2026, 13:13

README is now a short pitch with a quick start — everything else lives in the Manual.

- README reduced to tagline, how it works, manual link, and installation
- Manual gains a Features section
- No duplicate content between the two documents

→ [40c6d2b](https://github.com/joko-zauberzeug/nicetransfer/commit/40c6d2bf94b15d154c0c5b2e1e083ce10fc62bf6)

## Documentation update — 25. April 2026, 12:54

README and Manual restructured with a clearer focus on what nicetransfer is and who uses it.

- New tagline: "Nice and simple local file transfer via browser"
- README keeps it short — hook, how it works, features, quick start
- Manual now clearly separated into server setup and client usage
- Link from README to the full manual on GitHub

→ [5eea327](https://github.com/joko-zauberzeug/nicetransfer/commit/5eea327dc5437ce556375fc0eb1d3c148a9a0358)

## Network awareness — 25. April 2026, 12:10

nicetransfer now detects network state at startup and while running.

- If no network is found on startup, a warning is shown in the terminal and in the web UI with platform-specific hotspot setup instructions (macOS, Linux, Windows)
- A background timer checks every 5 seconds whether the network IP has changed
- When the network drops or reconnects, both the terminal and the web UI show a notification
- Three cases are distinguished: network lost, reconnected with same IP (clients reconnect automatically), reconnected with new IP (clients must rescan the QR code)

→ [6ac5f9a](https://github.com/joko-zauberzeug/nicetransfer/commit/6ac5f9a17908936dc9e2914c258ba5e00ace82f8)

## First fixes after going public — 25. April 2026, 11:24

Several small issues discovered while preparing the repo for GitHub.

- Startup banner now adapts its width dynamically — no more broken box borders with long paths or URLs
- Hidden files (`.gitkeep`) are no longer shown in the file list
- Removed duplicate "no files" label — NiceGUI's table already handles this on its own
- Changelog page now renders each version as a separate card (blog-post style)

→ [742f563](https://github.com/joko-zauberzeug/nicetransfer/commit/742f5633487a254681b11a1dfd051a712ea4c2ee)

## v0.4 — 2026-04-25

### Changed
- Complete UI overhaul using native NiceGUI/Quasar components
- `ui.header()`, `ui.card()`, `ui.list()`, `ui.item()`, `ui.button_dropdown()`, `ui.tabs()` used throughout
- Custom CSS reduced to a minimum (logo color, QR code, scroll margin)
- Quasar color palette instead of custom hex
- Font: Quasar/Roboto default instead of IBM Plex
- Section navigation in header as tabs with smooth scroll
- Hamburger menu as native Quasar dropdown

## v0.3 — 2026-04-25

### New
- Header navigation with Manual and Changelog
- Light / Dark / Auto theme toggle
- File list sorting: Newest, Oldest, A→Z, Z→A
- Share section toggle
- Image preview for JPG, PNG, GIF, WebP, SVG
- CSS extracted to separate file (`nicetransfer.css`)

## v0.2 — 2026-04-25

### New
- Three separate folders: upload / download / share
- `config.toml` for persistent configuration
- Toggle for upload and download (server device only)
- Token protection with QR code
- Auto-refresh of file list every 8 seconds
- Download links in file list

### Changed
- Default port: 7777 (no conflict with NiceGUI default)
- Local access (127.0.0.1) does not require a token

## v0.1 — 2026-04-25

### Initial release
- Upload via browser
- QR code for easy access
- File list with auto-refresh
