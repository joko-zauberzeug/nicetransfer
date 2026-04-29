# Changelog

## Updates GUI, clean shutdown, color system — Joko, 29. April 2026, 20:47

- **Updates GUI in Control panel** — "Updates" subsection shows installed NiceTransfer and NiceGUI versions; **Check** button queries the configured channel and shows a combined notification ("NiceTransfer v1.2 · NiceGUI 3.11.1 — all up to date", stays until dismissed); if a new version is found, an **Upgrade** button appears and streams `upgrade.sh` output live into a log dialog; auto-refreshes 3 s after page load so the startup check result is visible without clicking
- **Clean shutdown via HTTP** — `POST /shutdown?token=...` triggers `app.shutdown()` for a fully clean NiceGUI teardown; documented in Manual (curl command) and `llms-local.txt`; replaces `pkill` as the recommended remote-stop method
- **MCP `shutdown_server()` tool** — AI clients can shut down the server cleanly; added to MCP tool list and `llms.txt` / `llms-local.txt`
- **Color system** — `app.colors(primary='#FF6D00')` replaces the old CSS variable approach; all Quasar `color=primary` props and `text-primary` classes follow it automatically; CSS cleaned up: removed `:root` color-variable block, redundant toggle rule, and all hardcoded `#FF6D00` / `deep-orange` references — one line in Python controls the full brand color
- **`run.sh`** — `exec` replaces bash shell with Python process; Ctrl+C goes directly to uvicorn; `KeyboardInterrupt` after cleanup wrapped in `try/except` to suppress the cosmetic Python 3.14 asyncio traceback
- **Manual** — Stopping section rewritten (Ctrl+C primary, curl `/shutdown` for remote, `pkill` last resort); Upgrading section gains GUI-first paragraph; Control panel list updated with Updates entry

## v1.2 — Upgrade script, update check, NiceGUI 3.11.1 — Joko, 29. April 2026, 14:31

- **`upgrade.sh`** — new upgrade script; detects git vs. standalone install; interactive `[Y/n/d]` prompts with diff view per file; handles `run.sh` regeneration separately; `--yes` for non-interactive use, `--check` for JSON status output (GUI-ready)
- **Update channels** — `stable` (latest release tag) or `rolling` (main branch); configurable in `config.toml` under `[updates]`; `--channel` flag to override per run
- **Startup update check** — `check_on_start = true` (default) prints to terminal if a new version is available; `notify_deps = true` also checks nicegui and warns about compatibility
- **NiceGUI 3.11.1** — upgraded from 3.11.0; tested, no regressions
- **v1.2** — version bump; version number now only defined once (`VERSION` constant); removed redundant version from module docstring
- **Manual** — Upgrading section added: upgrade script usage, channel config, update check options

→ [cee7660](https://github.com/joko-zauberzeug/nicetransfer/commit/cee7660)

## Going public — Joko, 29. April 2026, 13:13

- **Repository is now public** — NiceTransfer v1.1 released openly under AGPL v3
- **README** — local URL in "How it works" now correctly shows `http://127.0.0.1:7777/?token=...` instead of tokenless `http://localhost:7777`
- **Repo cleanup** — `MCP.md` and `PLATFORMS.md` removed from the repository (internal planning docs, kept locally via `.gitignore`)

→ [3085019](https://github.com/joko-zauberzeug/nicetransfer/commit/3085019)

## Banner and Manual: token in local URL — Joko, 29. April 2026, 00:26

- **Banner** — `local` line now shows `http://127.0.0.1:PORT/?token=...`; token is required for localhost too, the old URL without token didn't work
- **Manual** — "Control panel" section updated to match: now refers to the banner's local URL instead of a hardcoded tokenless `http://localhost:7777`

→ [5677252](https://github.com/joko-zauberzeug/nicetransfer/commit/5677252)

## Screenshots in README — Joko, 28. April 2026, 23:12

- Three screenshots added to `screenshots/`: server QR-code hero (desktop), client landscape with file list and menu, client dark mode
- README: Screenshots section added directly above Installation

→ [50592e7](https://github.com/joko-zauberzeug/nicetransfer/commit/50592e7)

## v1.1 — Share first, /get page, source download — Joko, 28. April 2026, 21:49

- **v1.1** — version bump; version constant now used in banner, footer, ZIP filename, and server-card.json
- **Share section first** — reordered in nav anchors, section toggles, client permissions, file section rendering; most common use case is bidirectional sharing, so it leads
- **`/get` page** — dedicated page for source download (AGPL v3 compliance); platform section ("Coming soon. Maybe."), source ZIP button in orange, license text viewer
- **`/download/source`** — streams a ZIP of all source files on the fly; filename includes version (e.g. `nicetransfer-v1.1.zip`)
- **`/download/license`** — serves the plain-text `LICENSE` file
- **Footer on all pages** — `build_footer()` appended to `/`, `/manual`, `/changelog`, `/get`; shows `© 2026 Joko Keuschnig · AGPL v3` with link to `/get`
- **"Get" added to dropdown menu**
- **`/llms.txt` and `/llms-local.txt`** — now document all human-readable pages (`/manual`, `/changelog`, `/get`) and all source/license download endpoints
- **Manual** — section order updated to Share-first throughout (features list, sections table)

→ [46caf2b](https://github.com/joko-zauberzeug/nicetransfer/commit/46caf2b)

## Hero layout, color consistency, Manual polish — Joko, 28. April 2026, 19:36

- **Connection hero** — "Scan QR code to connect" now appears directly under the QR code, URL with copy/share below; hero content shifted upward via `padding-bottom` on the hero container (avoids overflow issues with negative margins)
- **Color consistency** — Set button changed from `color=orange` (Quasar built-in) to `color=primary`; all accent colors now flow through `--nt-orange` / `--q-primary` in `nicetransfer.css` — one edit changes the full color scheme
- **Manual** — session timeout control documented; NiceGUI attribution rewritten ("built on NiceGUI, a Python UI framework by Zauberzeug GmbH" with links to nicegui.io and zauberzeug.com)
- **AGPL-3.0** — license header (`SPDX-License-Identifier`) and copyright line added to `nicetransfer.py`; times added to all existing changelog entries

→ [24823d9](https://github.com/joko-zauberzeug/nicetransfer/commit/24823d9b150adaae21bffa067e88d13e199ccc04)

## Session timeout control, countdown display — Joko, 28. April 2026, 18:40

- **Countdown in header** — when a timeout is active, a monospace `⏱ MM:SS` counter appears directly under the logo; stable width (no jitter), visible on all pages
- **Timeout control in Control panel** — number input + **Set** button to start or restart the countdown at runtime; set to 0 to disable; "Client permissions" and "Session timeout" subheadings now in orange for visual consistency
- **PID file cleanup on SIGTERM** — timeout-triggered shutdown and external `pkill` both now reliably delete `.nicetransfer.pid`; previously atexit was not called by uvicorn's shutdown path

→ [7d5b0a4](https://github.com/joko-zauberzeug/nicetransfer/commit/7d5b0a4)

## Double-start prevention, llms-local.txt — Joko, 28. April 2026, 16:58

- **PID file (`.nicetransfer.pid`)** — written on startup, deleted on exit; contains `pid` and `port`; NiceTransfer refuses to start from the same directory if a live process is already running, with a clear error message and ready-to-run restart command; stale PID files (crash) are silently cleaned up
- **`/llms-local.txt`** — localhost-only endpoint (403 for external clients); contains token session guidance, PID file check instructions, restart procedure with pgrep wait loop, exit codes 143/144, and security note (never redirect banner output to /tmp)
- **`llms+` line in startup banner** — points to `llms-local.txt` with token; AI assistants fetch it immediately after start
- **`/llms.txt` refactored** — generic content only (no local paths or restart instructions); shared via `_llms_body()` helper used by both endpoints

→ [6896711](https://github.com/joko-zauberzeug/nicetransfer/commit/6896711)

## v1.0 — MCP server, AI operating guide — Joko, 28. April 2026, 13:20

- **MCP server (`/mcp`)** — Streamable HTTP endpoint fully working; `FastMCP` mounted into NiceGUI's FastAPI app with `streamable_http_path="/"` (fixes path-stripping by Starlette's `Mount`) and `host="0.0.0.0"` (disables auto DNS-rebinding protection that would block LAN clients); session manager lifespan wired via `app.on_startup` / `app.on_shutdown` (Starlette `Mount` does not propagate lifespan events)
- Four MCP tools: `get_status`, `list_files`, `upload_file`, `download_file`; path traversal prevented via `safe_filename()`
- **`mcp` line in startup banner** — `mcp     : http://127.0.0.1:PORT/mcp?token=TOKEN`; any AI that starts NiceTransfer reads the endpoint directly from stdout
- **`/llms.txt` as AI operating guide** — documents two discovery workflows: AI started the server (extract token from banner `mcp` line), AI received a URL from a human (read `<meta name="mcp-server">` from the HTML); current MCP URL with live token embedded; tool signatures and section semantics explained
- **Version 1.0** — feature set complete: file transfer, trash, undo, camera upload, token security, AI discovery layer, working MCP server
- Changelog hashes corrected (`6bb3535` → `bd9a9b4`, `0a8ee3b` → `fbc11ec`, `6014249` → `cffdcf8`)

→ [f413094](https://github.com/joko-zauberzeug/nicetransfer/commit/f413094)

## AI discovery layer — Joko, 27. April 2026, 21:45

- **Meta tags in `<head>`** — every page includes `mcp-server`, `mcp-server-card`, and `llms-txt` meta tags with full token-bearing URLs; an AI app that scans the QR code and fetches the page immediately knows how to connect
- **`/.well-known/mcp/server-card.json`** — machine-readable capability description: name, version, MCP endpoint, transport, authentication, active sections, tool list
- **`/llms.txt`** — plain-text description for AI assistants; lists active sections and available tools
- Both endpoints are token-protected (consistent with all other routes); the AI has the token from the QR URL
- MCP endpoint (`/mcp`) not yet implemented — discovery layer is in place for when it is
- Manual: new AI integration section

→ [19c0ab9](https://github.com/joko-zauberzeug/nicetransfer/commit/19c0ab9)

## Token everywhere, auto-shutdown timeout — Joko, 27. April 2026, 21:27

- **Token required for all routes** — localhost exception removed; `/download` and `/preview` no longer bypass the token check; every request (browser, download link, preview, future MCP) requires the token
- `webbrowser.open` on startup now opens `/?token=TOKEN` so the local browser works without manual URL editing
- Download URLs in file tables include `?token=TOKEN`
- Manual and Changelog navigation links include the token
- **Auto-shutdown timeout** — `[server] timeout = 0` in `config.toml`; set to N minutes for automatic shutdown after that duration; `0` = run indefinitely; shown in startup banner when active
- Manual updated: Security section revised, timeout added to config example

→ [bd9a9b4](https://github.com/joko-zauberzeug/nicetransfer/commit/bd9a9b4)

## Cleanup: install.sh template, dead CSS — Joko, 27. April 2026, 20:26

- `install.sh` now generates a complete `config.toml` including `[ui]` and `[permissions]` sections — fresh installs get correct defaults out of the box
- Removed unused `.nt-qr` CSS rule (small 220 px QR, superseded by `.nt-qr-hero`)

→ [fbc11ec](https://github.com/joko-zauberzeug/nicetransfer/commit/fbc11ec)

## Undo delete, camera upload, default client permissions — Joko, 27. April 2026, 20:14

- **Undo last delete** — after moving files to Trash an undo bar appears in the section ("N file(s) moved to trash" + Undo + ✕ dismiss); auto-dismisses after 10 seconds; per-section and per-client; works even when Trash is not visible to the client
- `asyncio.create_task` + `asyncio.sleep(10)` for cancellable auto-dismiss; undo handler runs synchronously in the click context to keep `ui.notify` working
- **Camera capture** — "Take photo" button in upload sections alongside "Upload files"; uses `<input capture="environment">` — opens camera directly on mobile, image file picker on desktop; files are passed to the Quasar uploader via `props.addFiles()` and auto-uploaded
- **Default client permissions** — `client_delete_upload` and `client_delete_share` now default to `true`; clients can delete in Upload and Share by default; Download deletion and Trash access remain off
- Manual updated: undo, camera, updated permissions defaults and description

→ [cffdcf8](https://github.com/joko-zauberzeug/nicetransfer/commit/cffdcf8)

## Trash, hero landing page, navigation overhaul and typography — Joko, 27. April 2026, 13:57

- **Trash section** — deleted files move to Trash instead of being removed permanently; sidecar `.meta` files store original name and source section
- `move_to_trash()`, `restore_from_trash()`, `trash_entries()` helpers; timestamp-prefix naming avoids conflicts
- Trash section: select files to restore (↩) or delete forever (🗑); live sync like all other sections
- **Client delete permissions**: per-section toggles in Control panel — server always has delete, clients only when permitted
- `[permissions]` block in `config.toml`; 5 new AppState fields
- **Tooltips** on all icon-only buttons (download, preview, trash, restore, delete forever, theme toggle)
- **Hero landing page**: Connection section is now full-viewport — large QR code (300 px), bold H3 slogan "Simple and **NiceTransfer** of files.", H5 call-to-action "Scan QR code to connect", animated scroll-down arrow
- **Header navigation**: Connection and Control appear as tabs for local users; stacked layout so Connection is above the fold and Control requires a short scroll
- **Control section** styled like all other sections — centered orange H5 title, same card pattern
- All section titles bumped to H5
- Logo: **Nice** bold + Transfer regular, no negative letter-spacing
- Logo link includes token for clients so clicking it never drops the session
- Hamburger menu items synced with tab visibility via shared timer — disabled sections disappear from both
- Manual updated: Trash, delete, client permissions, `[permissions]` config block, `pkill` stop command

→ [ec3a46a](https://github.com/joko-zauberzeug/nicetransfer/commit/ec3a46a)

## AI integration concept documented — Joko, 27. April 2026, 08:11

- Added `MCP.md` — concept and research notes for AI integration
- Three tiers: one-command MCP registration, in-chat paste, QR-based auto-discovery
- Aligned with 2026 standards: Streamable HTTP MCP at `/mcp`, Server Cards at `/.well-known/mcp/server-card.json`, OpenAPI at `/openapi.json`, `llms.txt`
- `claude mcp add --transport http nicetransfer http://localhost:7777` — the actual add command, no JSON editing
- Token independence: localhost needs no token; fixed token in `config.toml` for persistent remote MCP
- QR code stays unchanged — AI derives `/.well-known/mcp` from base URL by convention

→ [9c46b53](https://github.com/joko-zauberzeug/nicetransfer/commit/9c46b532c4a31918d9d4a0a2186e8a2873f889d3)

## MCP.md: HTML meta tag discovery — Joko, 27. April 2026, 08:26

- HTML `<meta>` tags in `<head>` as alternative to well-known URL convention
- Claude fetches URL → reads `<head>` → finds MCP pointer → no prior knowledge needed
- Why not HTTP headers: AI tools process HTML content, not raw HTTP headers
- NiceGUI's `ui.add_head_html()` makes dynamic injection trivial

→ [3f15bac](https://github.com/joko-zauberzeug/nicetransfer/commit/3f15bac4efe31a686f807f98fa173f7bd215e42c)

## Visual overhaul and mobile navigation — Joko, 26. April 2026, 11:22

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

→ [94dfe26](https://github.com/joko-zauberzeug/nicetransfer/commit/94dfe2607f364a5bb466c51b6fc90cfbf3e4c43c)

## Platform distribution notes — Joko, 25. April 2026, 23:35

- Added `PLATFORMS.md` — feasibility notes for macOS (.app bundle), Linux (AppImage, Flatpak), and Android (Termux)

→ [926553b](https://github.com/joko-zauberzeug/nicetransfer/commit/926553bfa419bac86d93046ad70f3396e797c89c)

## Manual update — Joko, 25. April 2026, 23:15

- NiceTransfer renamed consistently throughout (was nicetransfer)
- Built on [NiceGUI](https://nicegui.io) by Zauberzeug GmbH — mentioned in the intro
- Requirements clarified: only Python 3.9+ needed manually, all other dependencies (including NiceGUI) installed automatically by `./install.sh`
- Starting section: corrected default comment, added note that CLI flags override config
- Control panel: emoji replaced with description, ZIP download and multi-file selection documented
- Sections table simplified to ✓/— with a plain explanation — removes the ambiguous "Everyone vs. Clients" wording
- Features list updated: live sync and ZIP download added

→ [4b7428a](https://github.com/joko-zauberzeug/nicetransfer/commit/4b7428aa0f67718b1c2e0faab569fa7e968fc0ca)

## Live sync, config defaults, naming and polish — Joko, 25. April 2026, 22:38

- File list updates automatically on all connected clients within 3 seconds when any client uploads — no manual refresh needed
- New `[ui]` section in `config.toml`: set default theme (`auto` / `light` / `dark`) and which sections are shown on startup
- Default out of the box: Auto theme, Share section only
- Renamed to **NiceTransfer** (capital N and T) in logo, browser title, and terminal banner
- Section titles no longer forced uppercase — consistent with the control panel labels
- "Upload Files" → "Upload files" — consistent sentence case with "Drop files here"
- Removed the vertical separator between logo and navigation tabs
- CSS link gets a timestamp on each server start — no more stale browser cache after updates

→ [e2a329e](https://github.com/joko-zauberzeug/nicetransfer/commit/e2a329ebb9d7bc54f1dfa31d374eac6187093be4)

## UI polish: multi-select ZIP download, consistent sizing, CSS extracted — Joko, 25. April 2026, 21:43

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

## Drag & drop, image preview, color consistency — Joko, 25. April 2026, 14:53

- Drag & drop files directly onto the upload zone — visual highlight while dragging
- Image preview via NiceGUI dialog with base64 data URI — no new tab, no download dialog in Firefox
- File list: separate icon buttons for preview (🖼) and download (⬇), filename as plain text — prevents accidental double-tap on mobile
- Root cause of the Firefox download bug: preview icon and filename download link were adjacent tap targets
- Section title color unified to `#FF6D00` via `.nt-section-title` CSS class — consistent with the logo orange
- Preview dialog: dark gray background, no padding, no border

→ [e1805e6](https://github.com/joko-zauberzeug/nicetransfer/commit/e1805e68c04a6448566ff6615b6d2556850c0d74)

## README trimmed, Manual completed — Joko, 25. April 2026, 13:13

README is now a short pitch with a quick start — everything else lives in the Manual.

- README reduced to tagline, how it works, manual link, and installation
- Manual gains a Features section
- No duplicate content between the two documents

→ [40c6d2b](https://github.com/joko-zauberzeug/nicetransfer/commit/40c6d2bf94b15d154c0c5b2e1e083ce10fc62bf6)

## Documentation update — Joko, 25. April 2026, 12:54

README and Manual restructured with a clearer focus on what nicetransfer is and who uses it.

- New tagline: "Nice and simple local file transfer via browser"
- README keeps it short — hook, how it works, features, quick start
- Manual now clearly separated into server setup and client usage
- Link from README to the full manual on GitHub

→ [5eea327](https://github.com/joko-zauberzeug/nicetransfer/commit/5eea327dc5437ce556375fc0eb1d3c148a9a0358)

## Network awareness — Joko, 25. April 2026, 12:10

nicetransfer now detects network state at startup and while running.

- If no network is found on startup, a warning is shown in the terminal and in the web UI with platform-specific hotspot setup instructions (macOS, Linux, Windows)
- A background timer checks every 5 seconds whether the network IP has changed
- When the network drops or reconnects, both the terminal and the web UI show a notification
- Three cases are distinguished: network lost, reconnected with same IP (clients reconnect automatically), reconnected with new IP (clients must rescan the QR code)

→ [6ac5f9a](https://github.com/joko-zauberzeug/nicetransfer/commit/6ac5f9a17908936dc9e2914c258ba5e00ace82f8)

## First fixes after going public — Joko, 25. April 2026, 11:24

Several small issues discovered while preparing the repo for GitHub.

- Startup banner now adapts its width dynamically — no more broken box borders with long paths or URLs
- Hidden files (`.gitkeep`) are no longer shown in the file list
- Removed duplicate "no files" label — NiceGUI's table already handles this on its own
- Changelog page now renders each version as a separate card (blog-post style)

→ [742f563](https://github.com/joko-zauberzeug/nicetransfer/commit/742f5633487a254681b11a1dfd051a712ea4c2ee)

## v0.4 — Joko, 2026-04-25

### Changed
- Complete UI overhaul using native NiceGUI/Quasar components
- `ui.header()`, `ui.card()`, `ui.list()`, `ui.item()`, `ui.button_dropdown()`, `ui.tabs()` used throughout
- Custom CSS reduced to a minimum (logo color, QR code, scroll margin)
- Quasar color palette instead of custom hex
- Font: Quasar/Roboto default instead of IBM Plex
- Section navigation in header as tabs with smooth scroll
- Hamburger menu as native Quasar dropdown

## v0.3 — Joko, 2026-04-25

### New
- Header navigation with Manual and Changelog
- Light / Dark / Auto theme toggle
- File list sorting: Newest, Oldest, A→Z, Z→A
- Share section toggle
- Image preview for JPG, PNG, GIF, WebP, SVG
- CSS extracted to separate file (`nicetransfer.css`)

## v0.2 — Joko, 2026-04-25

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

## v0.1 — Joko, 2026-04-25

### Initial release
- Upload via browser
- QR code for easy access
- File list with auto-refresh
