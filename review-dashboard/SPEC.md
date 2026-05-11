# gBrain Review Dashboard — System Spec

File: `~/gbrain/review_server.py`
Serves at: `http://127.0.0.1:8080`

---

## Overview

The gBrain Review Dashboard is a local web server that provides a browser-based UI for reviewing articles synced from read-later apps (Matter). It replaces the terminal-based `review_matter.py` interactive script with a visual, large-screen-friendly experience.

The dashboard is a **single-file Python application** that embeds its entire frontend (HTML, CSS, JavaScript) inside a Python triple-quoted string (`DASHBOARD_HTML`) and serves it via the standard library `http.server` module. No dependencies beyond Python stdlib.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  review_server.py                                       │
│                                                         │
│  ┌─────────────────────────────────────────┐            │
│  │  DASHBOARD_HTML (Python triple-quoted   │            │
│  │  string — ~25KB of HTML/CSS/JS)         │            │
│  │                                         │            │
│  │  <style>...</style>   ├── dark theme     │            │
│  │  <script>...</script> ├── frontend JS    │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  ┌─────────────────────────────────────────┐            │
│  │  Data Layer:                             │            │
│  │  · load_annotations()  ← annotations.jsonl│           │
│  │  · get_all_articles()  ← ~/gbrain/articles/│         │
│  │  · get_article_by_id() ← single article   │          │
│  │  · enqueue_action()    → action-queue.json│           │
│  │  · write_brainstorm()  → ~/gbrain/notes/ │           │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  ┌─────────────────────────────────────────┐            │
│  │  HTTP Handler: ReviewHandler            │            │
│  │  · GET  /              → HTML page      │            │
│  │  · GET  /api/articles  → article list   │            │
│  │  · GET  /api/articles/:id → full article│            │
│  │  · POST /api/action    → queue action   │            │
│  │  · POST /api/brainstorm → save note     │            │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
         │                                                │
         ▼ http://127.0.0.1:8080                           ▼
   Browser (Chrome/Safari)                     Filesystem (~/gbrain/)
```

---

## API Endpoints

### `GET /api/articles` — Article List (Sidebar)

Returns metadata for **all** articles, sorted newest-first by file modification time. Does **not** include full article content.

```json
{
  "total": 55,
  "annotated": 0,
  "unannotated": 55,
  "articles": [
    {
      "id": "itm_8FY7D",
      "title": "~2,000 miles from home",
      "url": "https://...",
      "source": "",
      "author": "Ahmad",
      "date_saved": "",
      "date_synced": "2026-05-10",
      "tags": "[]",
      "has_annotations": false,
      "annotation_count": 0,
      "path": "articles/inbox/..."
    }
  ]
}
```

**Response size**: ~21KB for 55 articles (down from 658KB after lazy-loading refactor).

**Data source**: Scans `~/gbrain/articles/inbox/*.md` — reads each file, parses YAML frontmatter for metadata, reads `~/gbrain/annotations.jsonl` for annotation counts. No full content returned.

### `GET /api/articles/:id` — Single Article (Reader Pane)

Returns a single article with full content. Triggered on-demand when user clicks an article in the sidebar.

```json
{
  "ok": true,
  "article": {
    "id": "itm_8FY7D",
    "title": "~2,000 miles from home",
    "url": "...",
    "source": "",
    "author": "Ahmad",
    "date_saved": "",
    "date_synced": "2026-05-10",
    "tags": "[]",
    "has_annotations": false,
    "annotation_count": 0,
    "annotations": [],
    "path": "articles/inbox/...",
    "full_content": "---\ntitle: ...\n---\n\n# Article body..."
  }
}
```

### `POST /api/action` — Queue an Action

Queues a review action (create task, save for later, archive) to `~/gbrain/action-queue.json`.

```json
// Request
{ "action": "create_task", "article_id": "itm_...", "title": "Article Title" }

// Response
{ "ok": true, "action": "create_task" }
```

### `POST /api/brainstorm` — Save a Brainstorm Note

Writes a themed idea note to `~/gbrain/notes/YYYYMMDD_HHMM-idea-slug.md`.

```json
// Request
{ "article_id": "...", "title": "...", "url": "...", "notes": "..." }

// Response
{ "ok": true, "path": "~/gbrain/notes/20260511_0015-idea-slug.md" }
```

---

## Frontend Architecture

### Tech Stack

No frameworks, no build step. Everything is vanilla JavaScript embedded as a Python string literal.

- **HTML**: Static template served from `DASHBOARD_HTML` Python string
- **CSS**: ~380 lines of dark-theme CSS (custom properties, GitHub-dark inspired palette)
- **JS**: ~200 lines of vanilla async JS

### Page Structure

```
┌─────────────────┬──────────────────────────────────┐
│   Sidebar       │   Main Pane                      │
│   (380px)       │                                  │
│                 │                                  │
│   📋 gBrain     │   [Select an article to review]  │
│   Review        │    or                             │
│   55 articles   │   [Article Content]               │
│                 │                                  │
│   [Search...]   │   Toolbar:                        │
│                 │   📌 Create Task                  │
│   Article 1     │   📥 Save                         │
│   Article 2     │   💡 Brainstorm                   │
│   Article 3     │   🗑️ Archive                      │
│   Article 4     │   [Open original →]               │
│   ...           │                                  │
└─────────────────┴──────────────────────────────────┘
```

### Key JS Functions

| Function | Role |
|---|---|
| `loadArticles()` | Fetches sidebar metadata from `/api/articles`, calls `renderSidebar()`. Called on page load. |
| `renderSidebar()` | Filters articles by search term, builds HTML for article list. Uses `escapeHtml()` for safe rendering. |
| `selectArticle(id)` | Fetches full content from `/api/articles/:id`, renders in main pane. Async — loads on click, not upfront. |
| `renderAnnotations(article)` | Builds the annotations section (highlights + notes). |
| `markdownToHtml(md)` | Simple regex-based markdown renderer (code blocks, bold, italic, links, headings, blockquotes, paragraphs). |
| `escapeHtml(str)` | Sanitizes strings for safe HTML insertion (&, <, >, "). |
| `queueAction(action)` | POSTs to `/api/action` to queue a task/save/archive. |
| `submitBrainstorm()` | POSTs to `/api/brainstorm` to save an idea note. |
| `showToast(msg)` | Shows a brief notification at bottom-right of viewport. |
| `filterArticles()` | Re-renders sidebar with search filter. |

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `t` | Create Task (queue) |
| `a` | Archive (queue) |
| `s` | Save for Later (queue) |
| `b` | Open Brainstorm modal |
| `Escape` | Close Brainstorm modal |

---

## Python String Escaping Gotcha

The frontend JS is embedded inside a Python **non-raw** triple-quoted string:

```python
DASHBOARD_HTML = """<!DOCTYPE html>
...
<script>
// JavaScript here
</script>
..."""
```

This means: **every `\n` in the JS source inside this string is eaten by Python as a newline character.** This applies to:

- **Regex literals**: `replace(/\n\n/g, ...)` becomes `replace(//g, ...)` on two/three lines → syntax error
- **JS string literals**: `'\n'` becomes a string broken across lines → syntax error

**Fix**: In the Python source, write `\\n` where the JS needs `\n` (backslash-n). Python's `\\` escape produces a single `\` in the output, so:

| Python source | Output (served JS) | JS interpretation |
|---|---|---|
| `\\n` | `\n` | newline character in regex/string |
| `\\s` | `\s` | regex whitespace class |
| `\\*` | `\*` | regex literal asterisk |
| `\\\\n` | `\\n` | literal backslash-n (WRONG for newlines) |

**Correct patterns in the current code:**

```javascript
// Line 632 — frontmatter strip regex: needs \\n* in Python → \n* in JS
const body = article.full_content.replace(/^---[\s\S]*?---\n*/, '');

// Line 662 — code block regex: needs \\n in Python → \n in JS
html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

// Line 676 — paragraph split regex: needs \\n\\n in Python → \n\n in JS
html = html.replace(/\n\n/g, '</p><p>');

// Line 634 — newline string: needs \\n in Python → \n in JS  
renderAnnotations(article) + '\n' + markdownToHtml(body);
```

---

## Data Sources

| File | Purpose | Format |
|---|---|---|
| `~/gbrain/articles/inbox/*.md` | Synced article files from Matter | Markdown with YAML frontmatter |
| `~/gbrain/annotations.jsonl` | User highlights and personal notes | JSONL (one JSON object per line) |
| `~/gbrain/action-queue.json` | Pending Todoist actions (not yet wired) | JSON array |
| `~/gbrain/notes/` | Braindump/brainstorm notes | Markdown |

Article frontmatter example:
```yaml
---
title: Article Title
url: https://...
source:
author: Author Name
date_published:
date_saved:
date_synced: 2026-05-10T03:01:55.465856
tags: []
favorite: false
status: queue
highlights_count: 0
matter_id: itm_XXXXX
content_type: article
---
```

---

## Performance Characteristics

| Metric | Original | Current |
|---|---|---|
| Sidebar API response size | 658 KB (all 55 full articles) | ~21 KB (metadata only) |
| Single article fetch | N/A (bundled in sidebar) | ~0.5–150 KB (on demand) |
| JS file size (embedded) | ~6.5 KB | ~6.7 KB |
| Server startup | Instant | Instant |
| Browser memory (initial load) | ~700 KB JSON parse | ~25 KB JSON parse |

---

## Known Limitations

1. **No WebSockets** — each action requires a full HTTP round-trip; no real-time updates.
2. **Single-threaded** — Python `http.server` blocks on each request; one slow article read blocks all other requests.
3. **No article diff/pagination** — single article content is loaded in one chunk; very large articles (newsletters) can be slow to render.
4. **Minimal markdown rendering** — regex-based; doesn't handle nested markdown, tables, images (embedded images are raw `<img>` tags in the source).
5. **Annotations.jsonl dependency** — annotations only show if `annotations.jsonl` exists and is populated; notebook notes from Matter's internal API are not included.
6. **No session persistence** — refreshing the page loses state; no restore from previous session.

## Known Security Issues (Not Yet Fixed)

1. **XSS via article ID injection** — The sidebar renders `a.id` directly into an inline `onclick="selectArticle('${a.id}')"` handler without escaping. A crafted `matter_id` in frontmatter can inject arbitrary JavaScript. Fix pending — requires switching to `data-` attributes with `escapeHtml()`.

2. **Directory traversal in brainstorm** — `write_brainstorm_note()` constructs filenames from article titles without sanitizing path separators. A title like `../../../tmp/foo` escapes the notes directory. Fix pending — requires `re.sub(r'[^a-zA-Z0-9_-]', '', title)` on the slug.

3. **Unhandled ValueError on Content-Length** — `int(self.headers.get("Content-Length", 0))` crashes on malformed headers. Trivial fix — wrap in try/except.

4. **No file locking on action queue** — Concurrent POSTs to `/api/action` can lose entries due to read-modify-write without locking. Low risk for single-user app.

---

## Startup & Usage

```bash
cd ~/gbrain
python3 review_server.py              # Port 8080
python3 review_server.py --port 9000  # Custom port
python3 review_server.py --open       # Auto-open browser
```

Server logs only `/api/` requests. Press `Ctrl+C` to stop.