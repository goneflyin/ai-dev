# Review Dashboard

A single-file Python web server that provides a browser-based UI for reviewing articles synced from read-later apps (Matter).

**Source:** `review_server.py`
**Spec:** `SPEC.md`
**Codex Review:** `REVIEW.md`

## What It Does

Serves a dark-themed dashboard at `http://127.0.0.1:8080` with:

- **Sidebar** — article list with search, sorted newest-first (metadata only, ~21KB)
- **Reader pane** — on-demand article content fetch, rendered as HTML
- **Toolbar** — queue tasks, save for later, archive, brainstorm ideas
- **Keyboard shortcuts** — `t` (task), `a` (archive), `s` (save), `b` (brainstorm)

### API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` or `/dashboard` | GET | Serves the HTML dashboard |
| `/api/articles` | GET | Returns article metadata list (no full content) |
| `/api/articles/:id` | GET | Returns a single article with full content |
| `/api/action` | POST | Queues a review action (task/archive/save) |
| `/api/brainstorm` | POST | Writes an idea note to `~/gbrain/notes/ideas/` |

## Running

```bash
python3 review_server.py           # Port 8080
python3 review_server.py --port 9000
python3 review_server.py --open    # Auto-open browser
```

## Architecture

- **Python stdlib only** — no dependencies beyond Python standard library
- **Embedded frontend** — HTML/CSS/JS is embedded as a Python triple-quoted string (`DASHBOARD_HTML`)
- **Lazy loading** — article content only fetched on click, not upfront

## Testing

```bash
# Verify JS parses
node --check /tmp/check.js

# Verify API
curl -s http://127.0.0.1:8080/api/articles | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total'], 'articles')"
```

## Installation

```bash
make install   # Copies review_server.py to ~/gbrain/
```