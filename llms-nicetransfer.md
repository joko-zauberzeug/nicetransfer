# NiceTransfer — AI Development Guide

> Project-specific guide for AI assistants working on NiceTransfer.
> Read this alongside `llms.md` (NiceGUI reference).

---

## What NiceTransfer Is

Local file transfer hub — browser UI, no cloud, no accounts. Transfers files between devices on the same Wi-Fi network. Single Python file (`nicetransfer.py`) + shell scripts + CSS.

**Sections:** `share` (bidirectional), `upload` (receive only), `download` (serve only), `trash` (soft delete with restore). All sections can be toggled at runtime via the Control panel.

**Interfaces:**
- Browser UI at `http://<ip>:<port>/?token=<token>`
- HTTP endpoints for AI: `/files`, `/upload`, `/download`, `/delete`, `/restore`, `/shutdown`, `/check-updates`, `/manual.md`, etc. — documented in `/llms.txt`
- MCP server at `/mcp?token=<token>` (optional, for native MCP clients)

---

## Starting NiceTransfer (for development)

```bash
./run.sh
```

The startup banner prints the token. **Immediately** fetch `llms.txt` with that token to get current operating instructions:

```bash
curl "http://127.0.0.1:7777/llms.txt?token=<token>"
# or for local-only extended instructions:
curl "http://127.0.0.1:7777/llms-local.txt?token=<token>"
```

**Before starting:** check if already running:
```bash
cat .nicetransfer.pid 2>/dev/null
```

**Stopping:**
```bash
curl -s -X POST "http://127.0.0.1:7777/shutdown?token=<token>"
```

**Never** redirect startup output to `/tmp` or world-readable files — the banner contains the token.

For automated/headless starts use fixed parameters and suppress the browser tab:
```bash
./run.sh --port 7756 --token <testtoken> --no-open
```

**Never kill a NiceTransfer instance the user may have started** (check `pgrep -fl nicetransfer.py` and the PID file) — ask first. Only one instance can run per directory (PID-file lock); multiple instances from different directories are fine (each gets its own port and token).

---

## Systematic Testing (run before a release or after dependency updates)

Four layers, in this order. All were needed to find real bugs — HTTP tests alone missed a client-side 500 (see CHANGELOG v1.6).

### 1. Fresh install

```bash
rm -rf .venv run.sh uv.lock && ./install.sh
```
Expect: uv found, `uv sync` resolves, run.sh + config.toml generated. Watch for resolver warnings (e.g. a dependency extra that no longer exists).

### 2. HTTP API (curl)

Start via `./run.sh --no-open` in the background, read the banner, then fetch `llms-local.txt` and test **every endpoint documented there** — do not guess URLs. Minimum roundtrip: `/status` → upload → `/files` (check the `url` field) → download → DELETE (to trash) → `/files/trash` → restore or purge → `/check-updates` → `POST /shutdown` (expect exit 0).

### 3. Source-package loop (tests packaging + installer end-to-end)

Download `/download/source` into the scratchpad, unzip, run `install.sh` there, start the copy (own port/token — parallel instances from different directories are fine), hit `/status` on it, shut it down. This catches incomplete `_SOURCE_FILES` lists and installer regressions.

### 4. Browser UI (Claude Preview tools)

`.claude/launch.json` (gitignored) is set up with `./run.sh --port 7756 --no-open`. Then: `preview_start` → token from `preview_logs` → navigate to `/?token=...` via `preview_eval`. Checklist:

- Main page in a **fresh session** must render (this is where the NiceGUI prune-race 500 appeared — a browser with an old session cookie hides it, curl can't reproduce it)
- Toggle a section in the Control panel, cross-check with `GET /status` that the server state changed
- Theme cycle auto → light → dark; navigate to another page and verify the theme persisted (tests user-storage read *and* write)
- Subpages `/manual`, `/changelog`, `/get` render without "Server error"
- `preview_console_logs` (level warn): must be empty
- `preview_logs` (level error): must be empty
- `preview_resize` to mobile (375px): no horizontal scroll (`document.documentElement.scrollWidth <= clientWidth`)

Notes: runtime toggles are not persisted (config.toml stays untouched); shut the preview server down cleanly afterwards; file-chooser uploads cannot be automated — cover uploads via the HTTP API instead.

---

## Architecture

**Single file by design.** `nicetransfer.py` is ~1700 lines and intentionally not split into modules. The goal is a self-contained script that works with a plain `python nicetransfer.py` after installing dependencies. Do not refactor into multiple files unless there is a strong reason.

**Global `AppState` is intentional.** The `state = AppState()` object at module level is shared between NiceGUI UI handlers and MCP tool functions. `app.storage` cannot serve this purpose because MCP tools run outside the NiceGUI request context. Do not move state into `app.storage` without understanding this constraint.

**Token middleware applies to everything**, including localhost requests. Always include `?token=TOKEN` in any generated URL or link — there are no public endpoints except NiceGUI internals (`/_nicegui`, `/static`).

**Python and dependencies are managed by uv.** `pyproject.toml` declares the dependencies (nicegui, qrcode, mcp; `requires-python >= 3.11`); `uv sync` creates `.venv`; `run.sh` starts via `uv run --project`. `uv.lock` is deliberately gitignored — dependencies resolve to the latest matching versions at install time. The uv-created venv has no pip; use `uv sync` / `uv sync --upgrade-package <pkg>` for dependency changes.

**`run.sh` is generated by `install.sh`** and its template is duplicated in `upgrade.sh` (`EXPECTED_RUN` — keep both byte-identical). Scripts locate themselves via `${BASH_SOURCE[0]}`. Do not hardcode absolute paths.

---

## Coding Conventions

Beyond what `llms.md` covers, NiceTransfer specifically:

- **`background_tasks.create()`** — never `asyncio.create_task()` or `asyncio.ensure_future()`
- **`ui.clipboard.write(text)`** — never `ui.run_javascript("navigator.clipboard...")`
- **`ui.button().props('tag=a href=...')`** — never `ui.html('<a href=...')`  for styled links
- **`.classes()`** over `.style()`** — use Tailwind or Quasar utility classes (`gap-2`, `opacity-60`, `break-all`, `pl-5`, etc.); `.style()` only for values with no class equivalent (custom rgba, `max-width:95vw`)
- **`.props("dark")`** on cards/dialogs instead of `background:#2a2a2a`
- **`ui.separator()`** before footer elements instead of `border-top` in `.style()`
- **Single quotes** for Python strings (NiceGUI project convention)

---

## Commit Workflow

**Never commit and push automatically.** Always wait for the user to test and explicitly request a commit.

1. **Test** — start with `./run.sh`, verify the changed functionality works
2. **Check MANUAL.md** — if any user-facing behavior changed (new feature, renamed option, changed endpoint, corrected description), update the relevant section before committing
3. **Bundle** — one commit per logical change set, not one per small fix
4. **Update CHANGELOG.md** before committing:
   - Add the hash of the *previous* HEAD commit to the bottom of its changelog entry:
     `→ [<shorthash>](https://github.com/joko-zauberzeug/nicetransfer/commit/<fullhash>)`
   - Get with: `git rev-parse HEAD` (short: `git rev-parse --short HEAD`)
   - Write a new blog-style entry at the top (below `# Changelog`):
     `## <title> — <author>, <date>` — author from `git config user.name`, real date from `date "+%d. %B %Y, %H:%M"`
   - No commit link in the new entry yet — it gets added before the *next* push
5. **Commit** everything together (code + CHANGELOG.md + MANUAL.md if changed)
6. **Never push** unless the user explicitly says so

**Changelog format:**
```
## Meaningful title — <author>, 30. April 2026, 14:22

- **Feature name** — description of what changed and why
- **Another change** — description

→ [abc1234](https://github.com/joko-zauberzeug/nicetransfer/commit/abc1234fullhash)
```

---

## Versioning

Plain `1.x` version numbers. `VERSION` constant in `nicetransfer.py` (line ~129).

- Do **not** bump the version for every commit — only when ready to ship a release
- A release = version bump + git tag `v1.x` + push
- Between releases, `VERSION` stays at the last released number
- The update check compares `VERSION` against the latest git tag — leaving it at the last release is correct behavior

---

## AI Interface Philosophy

**This is a core design decision. Do not change this without understanding the reasoning.**

NiceTransfer's primary AI interface is **plain HTTP + `llms.txt`** — not MCP.

### The principle

When an AI opens the NiceTransfer URL, the HTML `<head>` contains meta tags pointing to `llms.txt`. That file documents everything: what NiceTransfer does, which HTTP endpoints exist, what each one does, and how to use them. The AI makes plain HTTP calls — no MCP client setup, no protocol handshake, no special tooling required. Any AI that can fetch a URL and read text can operate NiceTransfer.

### Why not MCP as primary interface

MCP requires the AI client to have the server URL configured before it can do anything — no prior configuration, no access. Plain HTTP + `llms.txt` requires nothing: the AI opens the URL, finds the meta tag, fetches `llms.txt`, and immediately knows all available operations.

An AI could technically call the MCP endpoint directly via HTTP POST with JSON-RPC messages — MCP Streamable HTTP is just HTTP under the hood. But that means the AI must construct JSON-RPC envelopes, understand the protocol framing, and unpack wrapped responses. Plain REST is the same thing without the protocol overhead.

### No parallel AI-specific implementations

The AI uses what already exists. HTTP endpoints are built for the application; the AI simply uses them too. `llms.txt` is the documentation layer — it tells the AI what the endpoints are, what they do, and how to call them.

**Example:** To check for updates, the AI calls `POST /check-updates?token=...`. It does not guess GitHub API URLs or rely on training data. The endpoint is documented in `llms.txt` and wraps the same tested function the GUI uses.

### Operator controls stay in the GUI

The Control panel (section toggles, permissions, timeout) is not part of the AI interface. These are operator settings — NiceGUI handles them reactively, in real time, with immediate feedback across all connected browsers. Adding HTTP endpoints for them would mean maintaining two full interfaces for operator functions, which defeats the purpose of using NiceGUI.

The AI works within what the operator has configured. If a section is disabled, the AI gets 404 — same as a human client. It does not reconfigure the server.

### MCP overlap is acceptable

Some operations exist in both HTTP and MCP (list, upload, download, shutdown). This is not duplicated code — both paths call the same underlying Python functions. MCP remains for AI clients that natively support it; HTTP is the universal fallback.

When AI clients implement dynamic MCP discovery via the `<meta name="mcp-server">` tag already in every NiceTransfer page, the HTTP overlap will matter less. That infrastructure is already in place.

### The broader pattern

Serve a well-structured `llms.txt` that documents existing HTTP endpoints. AI assistants interact via plain HTTP — no dedicated MCP infrastructure, no client configuration. The `<meta name="llms-txt">` tag is the discovery mechanism. Applicable to any web application.

---

## What to Avoid

- **Splitting `nicetransfer.py`** into multiple files (breaks the self-contained design)
- **Moving `AppState` to `app.storage`** (MCP tools can't access it there)
- **Absolute paths in shell scripts** (breaks portability)
- **Token-less URLs** in any generated link, even localhost
- **Redirecting startup output** to files (token exposure)
- **Auto-committing or auto-pushing** without explicit user request
- **Bypassing the HTTP interface** — for any operation on a running instance, use the endpoints in `llms.txt`; do not reach for shell commands, PID files, or process management
