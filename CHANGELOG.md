# Changelog

## Network awareness — 25. April 2026, 12:10

nicetransfer now detects network state at startup and while running.

- If no network is found on startup, a warning is shown in the terminal and in the web UI with platform-specific hotspot setup instructions (macOS, Linux, Windows)
- A background timer checks every 5 seconds whether the network IP has changed
- When the network drops or reconnects, both the terminal and the web UI show a notification
- Three cases are distinguished: network lost, reconnected with same IP (clients reconnect automatically), reconnected with new IP (clients must rescan the QR code)

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
