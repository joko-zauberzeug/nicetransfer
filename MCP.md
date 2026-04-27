# AI integration — ideas and concepts

Ideas for making NiceTransfer accessible to AI assistants (Claude and others).
Nothing implemented yet — this document captures the concepts for later.

---

## Standards that already exist (2026)

The core ideas below are not invented from scratch — most align with emerging or
established standards:

| Concept | Standard | Endpoint |
|---------|----------|----------|
| AI-readable capability description | MCP Server Cards (SEP-1649) | `/.well-known/mcp/server-card.json` |
| MCP server over HTTP | Streamable HTTP (MCP spec 2025-03-26) | `/mcp` |
| API → MCP tools automatically | OpenAPI → MCP | `/openapi.json` |
| AI-readable site description | llms.txt | `/llms.txt` |

HTTP+SSE (the older MCP transport) is deprecated as of 2026-03-26 and unsupported
after June 30, 2026. NiceTransfer should use Streamable HTTP from the start.

---

## The core idea

NiceTransfer exposes its functionality via HTTP. An AI that knows the URL, token,
and endpoint structure can immediately upload, download, and list files — no special
protocol required. The question is how to get that information to the AI conveniently.

---

## Three integration tiers

### Tier 1 — One command (low barrier, persistent)

```bash
claude mcp add --transport http nicetransfer http://localhost:7777
```

One command, no JSON editing. After this, Claude Desktop always has NiceTransfer
available as a tool. Works via the Streamable HTTP endpoint at `/mcp`.

For remote access (non-localhost), a fixed token must be set in `config.toml`
so the registration stays valid across restarts. Localhost already requires no token.

### Tier 2 — In the chat (zero setup, most users)

NiceTransfer shows a **"Copy for Claude"** button in the control panel.
Clicking it copies a ready-to-paste text to the clipboard — the network URL,
token, and a short description of the available endpoints. Paste into any Claude
chat → Claude can immediately interact with NiceTransfer for that session.

### Tier 3 — Auto-discovery via QR code

The QR code stays unchanged (just the web URL — no size increase).
The AI-readable description lives at a predictable well-known URL:

```
http://192.168.x.x:7777/.well-known/mcp/server-card.json
```

An AI that receives the base URL (e.g. by scanning the QR code) can derive
the server card URL by convention. No larger QR code, no compatibility issues.

**Why not embed the description in the QR code?**
QR codes have practical size limits. A URL fits; a full description does not.
Multi-record QR codes (`WEB:... AI:...`) are not reliably parsed by iOS/Android
standard readers — they either show raw text or only parse the first record.

---

## Endpoints NiceTransfer would expose

| Endpoint | Purpose |
|----------|---------|
| `/mcp` | Streamable HTTP MCP server — tools for list, upload, download, status |
| `/.well-known/mcp/server-card.json` | Machine-readable capability description (MCP Server Cards standard) |
| `/openapi.json` | OpenAPI spec — auto-generates MCP tool definitions |
| `/llms.txt` | Plain-text AI-readable description of what NiceTransfer does |

---

## MCP tools (sketch)

| Tool | Description |
|------|-------------|
| `list_files(section)` | List files in upload / download / share |
| `upload_file(path, section)` | Upload a local file to a section |
| `download_file(name, section, destination)` | Download a file to a local path |
| `get_status()` | Server URL, active sections, token hint |

The implementation would be a thin layer over the existing NiceTransfer logic —
the file handling is already there. The Python `mcp` SDK makes this straightforward.

---

## Open questions / next steps

- Implement `/mcp` Streamable HTTP endpoint (Python `mcp` SDK)
- Implement `/.well-known/mcp/server-card.json`
- Implement `/openapi.json` (FastAPI can generate this automatically)
- Implement `/llms.txt`
- Add "Copy for Claude" button to the control panel
- Test: `claude mcp add --transport http nicetransfer http://localhost:7777`
- Test: scan QR with Claude app → derive `/.well-known/mcp` → Claude uses NiceTransfer
