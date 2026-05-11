#!/usr/bin/env python3
"""
gBrain Review Dashboard — Local web server.
Opens a browser-based dashboard for reviewing captured articles on a large screen.

Usage:
    python3 review_server.py           # Start on default port 8080
    python3 review_server.py --port 9000
    python3 review_server.py --open    # Auto-open browser
"""

import json
import os
import sys
import argparse
import http.server
import re
import urllib.parse
from pathlib import Path
from datetime import datetime

GBRAIN_DIR = Path.home() / "gbrain"
ARTICLES_DIR = GBRAIN_DIR / "articles"
ANNOTATIONS_FILE = GBRAIN_DIR / "annotations.jsonl"
ACTION_QUEUE = GBRAIN_DIR / "action-queue.json"
NOTES_DIR = GBRAIN_DIR / "notes"
TODOIST_HELPER = GBRAIN_DIR / "todoist_helper.py"


# ── Data Layer ──────────────────────────────────────────────────────────────────


def load_annotations():
    """Load all annotation records from JSONL."""
    annotations = {}
    if ANNOTATIONS_FILE.exists():
        with open(ANNOTATIONS_FILE) as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    aid = rec.get("article_id", "")
                    if aid:
                        annotations.setdefault(aid, []).append(rec)
                except json.JSONDecodeError:
                    pass
    return annotations


def parse_frontmatter(content):
    """Extract YAML frontmatter as a dict."""
    lines = content.split("\n")
    if not lines or lines[0] != "---":
        return {}
    try:
        end = content.index("\n---\n", 4)
        fm_text = content[4:end]
    except ValueError:
        return {}
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip("'\"")
    return fm


def get_title(content, fm):
    """Extract title from frontmatter or first H1."""
    if fm.get("title"):
        return fm["title"]
    for line in content.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return "Untitled"


def get_article_meta(md_path, annotations):
    """Extract metadata from one article (lightweight — no full content)."""
    content = md_path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(content)
    matter_id = fm.get("matter_id", "")
    anns = annotations.get(matter_id, [])
    return {
        "id": matter_id or md_path.stem,
        "title": get_title(content, fm),
        "url": fm.get("url", ""),
        "source": fm.get("source", ""),
        "author": fm.get("author", ""),
        "date_saved": fm.get("date_saved", "")[:10],
        "date_synced": fm.get("date_synced", "")[:10],
        "tags": fm.get("tags", ""),
        "has_annotations": len(anns) > 0,
        "annotation_count": len(anns),
        "path": str(md_path.relative_to(GBRAIN_DIR)),
    }


def get_all_articles():
    """Get article metadata list (no full content — sidebar only)."""
    annotations = load_annotations()
    articles = []
    for md_path in sorted(ARTICLES_DIR.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        articles.append(get_article_meta(md_path, annotations))
    return articles


def get_article_by_id(article_id):
    """Get a single article with full content."""
    annotations = load_annotations()
    for md_path in ARTICLES_DIR.rglob("*.md"):
        content = md_path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        matter_id = fm.get("matter_id", "")
        if matter_id == article_id or md_path.stem == article_id:
            anns = annotations.get(matter_id, [])
            return {
                "id": matter_id or md_path.stem,
                "title": get_title(content, fm),
                "url": fm.get("url", ""),
                "source": fm.get("source", ""),
                "author": fm.get("author", ""),
                "date_saved": fm.get("date_saved", "")[:10],
                "date_synced": fm.get("date_synced", "")[:10],
                "tags": fm.get("tags", ""),
                "has_annotations": len(anns) > 0,
                "annotation_count": len(anns),
                "annotations": anns,
                "path": str(md_path.relative_to(GBRAIN_DIR)),
                "full_content": content,
            }
    return None


def enqueue_action(action_type, article_id, title, note=""):
    """Queue an action for later processing."""
    entry = {
        "action": action_type,
        "timestamp": datetime.now().isoformat(),
        "matter_id": article_id,
        "title": title,
        "note": note,
    }

    queue = []
    if ACTION_QUEUE.exists():
        try:
            queue = json.loads(ACTION_QUEUE.read_text())
        except (json.JSONDecodeError, Exception):
            queue = []

    queue.append(entry)
    ACTION_QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))
    return entry


def write_brainstorm_note(article_title, article_url, notes_text):
    """Write a brainstorm/idea note to gbrain notes/ideas/."""
    now = datetime.now()
    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "", article_title.lower().replace(" ", "-"))
    slug = f"idea-{safe_title[:40]}"
    fname = f"{now.strftime('%Y%m%d_%H%M')}-{slug}.md"
    ideas_dir = NOTES_DIR / "ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    note_path = ideas_dir / fname
    
    lines = [
        "---",
        f"date: {now.strftime('%Y-%m-%d')}",
        f"time: {now.strftime('%H:%M')}",
        f"topic: Idea from: {article_title}",
        f"source: {article_url or 'inbox'}",
        "tags: [idea, brainstorm]",
        "---",
        "",
        f"# Idea: {article_title}",
        "",
        f"*Sourced from: [{article_title}]({article_url})*" if article_url else "",
        "",
        notes_text,
        "",
        "---",
        f"*Generated on {now.strftime('%Y-%m-%d at %H:%M')}*",
    ]
    
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return str(note_path)


# ── HTTP Server ─────────────────────────────────────────────────────────────────


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gBrain Review Dashboard</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface-hover: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --yellow: #d29922;
    --red: #f85149;
    --purple: #bc8cff;
    --radius: 8px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    width: 380px;
    min-width: 380px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-header h1 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
  }
  .sidebar-header .stats {
    font-size: 13px;
    color: var(--text-muted);
  }
  .sidebar-search {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-search input {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 13px;
    outline: none;
  }
  .sidebar-search input:focus {
    border-color: var(--accent);
  }
  .article-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }
  .article-item {
    padding: 10px 20px;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: background 0.1s;
  }
  .article-item:hover {
    background: var(--surface-hover);
  }
  .article-item.active {
    background: var(--surface-hover);
    border-left-color: var(--accent);
  }
  .article-item .title {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 2px;
    line-height: 1.3;
  }
  .article-item .meta {
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .article-item .meta .date { }
  .article-item .meta .source { color: var(--accent); }
  .article-item .badge {
    display: inline-block;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 500;
  }
  .badge-annotated { background: #1a3a1a; color: var(--green); }
  .badge-unread { background: #1a2a3a; color: var(--accent); }
  .badge-idea { background: #2a1a3a; color: var(--purple); }

  /* Main content */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .main-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 16px;
    text-align: center;
    padding: 40px;
  }
  .main-placeholder span { opacity: 0.5; }

  .article-view {
    display: none;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }
  .article-view.visible { display: flex; }

  .article-toolbar {
    padding: 12px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
    background: var(--surface);
  }
  .article-toolbar .article-url {
    font-size: 12px;
    color: var(--accent);
    text-decoration: none;
    margin-left: auto;
  }
  .article-toolbar .article-url:hover { text-decoration: underline; }

  .btn {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .btn:hover { background: var(--surface-hover); border-color: var(--text-muted); }
  .btn-primary { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .btn-primary:hover { background: #388bfd; }
  .btn-green { background: #238636; border-color: #238636; color: #fff; }
  .btn-green:hover { background: #2ea043; }
  .btn-purple { background: #5a2d82; border-color: #5a2d82; color: #fff; }
  .btn-purple:hover { background: #6e40a3; }
  .btn-danger { background: #da3633; border-color: #da3633; color: #fff; }
  .btn-danger:hover { background: #f85149; }

  .article-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px 32px;
    line-height: 1.7;
    font-size: 15px;
  }
  .article-content h1 {
    font-size: 26px;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .article-content h2 {
    font-size: 20px;
    font-weight: 600;
    margin: 24px 0 12px;
  }
  .article-content h3 {
    font-size: 16px;
    font-weight: 600;
    margin: 20px 0 8px;
  }
  .article-content p { margin-bottom: 12px; }
  .article-content a { color: var(--accent); }
  .article-content blockquote {
    border-left: 3px solid var(--border);
    padding-left: 16px;
    color: var(--text-muted);
    margin: 12px 0;
  }
  .article-content code {
    background: var(--surface);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }
  .article-content pre {
    background: var(--surface);
    padding: 16px;
    border-radius: var(--radius);
    overflow-x: auto;
    margin: 12px 0;
  }

  /* Annotations section */
  .annotations-section {
    margin: 20px 0;
    padding: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .annotations-section h3 {
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--green);
    margin-bottom: 12px;
  }
  .annotation-card {
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
  }
  .annotation-card:last-child { border-bottom: none; }
  .annotation-card .highlight {
    font-style: italic;
    color: var(--yellow);
    font-size: 14px;
  }
  .annotation-card .note {
    margin-top: 4px;
    font-size: 14px;
    color: var(--text);
  }
  .annotation-card .date {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  /* Modal */
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 100;
    align-items: center;
    justify-content: center;
  }
  .modal-overlay.visible { display: flex; }
  .modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    width: 500px;
    max-width: 90vw;
    max-height: 80vh;
    overflow-y: auto;
  }
  .modal h2 { font-size: 18px; margin-bottom: 16px; }
  .modal label {
    display: block;
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 4px;
  }
  .modal textarea {
    width: 100%;
    min-height: 120px;
    padding: 10px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 14px;
    resize: vertical;
    outline: none;
    margin-bottom: 16px;
  }
  .modal textarea:focus { border-color: var(--accent); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; }

  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    padding: 12px 20px;
    background: #238636;
    color: #fff;
    border-radius: var(--radius);
    font-size: 14px;
    z-index: 200;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.3s;
  }
  .toast.visible { opacity: 1; transform: translateY(0); }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

  @media (max-width: 768px) {
    .sidebar { width: 100%; min-width: 100%; }
    .main { display: none; }
  }
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <h1>📋 gBrain Review</h1>
    <div class="stats" id="stats">Loading...</div>
  </div>
  <div class="sidebar-search">
    <input type="text" id="search" placeholder="Search articles..." oninput="filterArticles()">
  </div>
  <div class="article-list" id="articleList"></div>
</div>

<div class="main">
  <div class="main-placeholder" id="placeholder">
    <span>Select an article to review</span>
  </div>

  <div class="article-view" id="articleView">
    <div class="article-toolbar" id="toolbar">
      <button class="btn btn-primary" onclick="queueAction('create_task')">📌 Create Task</button>
      <button class="btn btn-green" onclick="queueAction('save_for_later')">📥 Save</button>
      <button class="btn btn-purple" onclick="openBrainstorm()">💡 Brainstorm</button>
      <button class="btn btn-danger" onclick="queueAction('archive')">🗑️ Archive</button>
      <a class="article-url" id="articleUrl" target="_blank" href="#">Open original →</a>
    </div>
    <div class="article-content" id="articleContent"></div>
  </div>
</div>

<!-- Brainstorm Modal -->
<div class="modal-overlay" id="brainstormModal">
  <div class="modal">
    <h2>💡 Brainstorm from this article</h2>
    <label>Your thoughts, ideas, or connections:</label>
    <textarea id="brainstormNotes" placeholder="What does this make you think about? Any ideas, projects, or actions it sparks?"></textarea>
    <div class="modal-actions">
      <button class="btn" onclick="closeBrainstorm()">Cancel</button>
      <button class="btn btn-purple" onclick="submitBrainstorm()">Save as Braindump</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
let articles = [];
let currentArticle = null;
let currentQueue = [];

async function loadArticles() {
  try {
    const resp = await fetch('/api/articles');
    const data = await resp.json();
    articles = data.articles;
    renderSidebar();
    document.getElementById('stats').textContent = 
      `${articles.length} articles · ${articles.filter(a => a.has_annotations).length} annotated`;
  } catch (e) {
    document.getElementById('stats').textContent = 'Failed to load';
  }
}

function renderSidebar() {
  const list = document.getElementById('articleList');
  const search = document.getElementById('search').value.toLowerCase();
  
  const filtered = articles.filter(a => 
    a.title.toLowerCase().includes(search) ||
    a.source.toLowerCase().includes(search)
  );
  
  list.innerHTML = filtered.map(a => {
    const isActive = currentArticle && a.id === currentArticle.id;
    const badge = a.has_annotations 
      ? '<span class="badge badge-annotated">📝 annotated</span>'
      : '<span class="badge badge-unread">📄 unread</span>';
    return `
      <div class="article-item ${isActive ? 'active' : ''}" data-article-id="${escapeHtml(a.id)}">
        <div class="title">${escapeHtml(a.title)}</div>
        <div class="meta">
          ${a.date_saved ? `<span class="date">${a.date_saved}</span>` : ''}
          ${a.source ? `<span class="source">${escapeHtml(a.source)}</span>` : ''}
          ${badge}
        </div>
      </div>
    `;
  }).join('');
}

async function selectArticle(id) {
  try {
    const resp = await fetch('/api/articles/' + encodeURIComponent(id));
    const data = await resp.json();
    if (!data.ok) { showToast('❌ Article not found'); return; }
    const article = data.article;
    currentArticle = article;
    
    // Update sidebar
    document.querySelectorAll('.article-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.article-item').forEach(el => {
      if (el.dataset.articleId === id) el.classList.add('active');
    });
    
    // Show view
    document.getElementById('placeholder').style.display = 'none';
    document.getElementById('articleView').classList.add('visible');
    
    // Render content
    const body = article.full_content.replace(/^---[\\s\\S]*?---\\n*/, '');
    document.getElementById('articleContent').innerHTML = 
      renderAnnotations(article) + '\\n' + markdownToHtml(body);
    
    document.getElementById('articleUrl').href = article.url || '#';
    document.getElementById('articleUrl').textContent = article.url ? 'Open original →' : '';
  } catch (e) {
    showToast('❌ Failed to load article');
  }
}

function renderAnnotations(article) {
  if (!article.annotations || article.annotations.length === 0) return '';
  
  let html = '<div class="annotations-section"><h3>📝 Your Highlights & Notes</h3>';
  article.annotations.forEach(ann => {
    html += '<div class="annotation-card">';
    if (ann.highlight) html += `<div class="highlight">"${escapeHtml(ann.highlight)}"</div>`;
    if (ann.note) html += `<div class="note">${escapeHtml(ann.note)}</div>`;
    if (ann.date) html += `<div class="date">${ann.date}</div>`;
    html += '</div>';
  });
  html += '</div>';
  return html;
}

function markdownToHtml(md) {
  // Simple markdown rendering (enough for article content)
  let html = md;
  // Code blocks
  html = html.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold/italic
  html = html.replace(/\\*\\*\\*(.+?)\\*\\*\\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  html = html.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
// Images (before links so they don't get caught by the link regex)
  html = html.replace(/!\\[([^\\]]*)\\]\\(([^)]+)\\)/g, '<img src=\"$2\" alt=\"$1\" style=\"max-width:100%;height:auto;border-radius:8px\">');
  // Links
  html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href=\"$2\" target=\"_blank\">$1</a>');
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Paragraphs
  html = html.replace(/\\n\\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  // Clean up nested paragraphs
  html = html.replace(/<p><\\/p>/g, '');
  // Blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  return html;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
}

function filterArticles() {
  renderSidebar();
}

async function queueAction(action) {
  if (!currentArticle) return;
  
  try {
    const resp = await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        action: action,
        article_id: currentArticle.id,
        title: currentArticle.title,
      }),
    });
    const data = await resp.json();
    if (data.ok) {
      showToast(`✅ ${action === 'create_task' ? 'Task queued' : action === 'save_for_later' ? 'Saved for later' : action === 'archive' ? 'Archived' : action} — ${currentArticle.title}`);
    }
  } catch (e) {
    showToast('❌ Failed to queue action');
  }
}

function openBrainstorm() {
  if (!currentArticle) return;
  document.getElementById('brainstormNotes').value = '';
  document.getElementById('brainstormModal').classList.add('visible');
}

function closeBrainstorm() {
  document.getElementById('brainstormModal').classList.remove('visible');
}

async function submitBrainstorm() {
  const notes = document.getElementById('brainstormNotes').value.trim();
  if (!notes) {
    showToast('⚠️ Write something before saving');
    return;
  }
  
  try {
    const resp = await fetch('/api/brainstorm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        article_id: currentArticle.id,
        title: currentArticle.title,
        url: currentArticle.url,
        notes: notes,
      }),
    });
    const data = await resp.json();
    if (data.ok) {
      showToast(`💡 Braindump saved — ${data.path}`);
      closeBrainstorm();
    }
  } catch (e) {
    showToast('❌ Failed to save brainstorm');
  }
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 3000);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if (e.key === 't') queueAction('create_task');
  if (e.key === 'a') queueAction('archive');
  if (e.key === 's') queueAction('save_for_later');
  if (e.key === 'b') openBrainstorm();
  if (e.key === 'Escape') closeBrainstorm();
});

document.getElementById('articleList').addEventListener('click', (e) => {
  const item = e.target.closest('.article-item');
  if (item) {
    const id = item.dataset.articleId;
    if (id) selectArticle(id);
  }
});

loadArticles();
</script>
</body>
</html>
"""


class ReviewHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for dashboard and API."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        if parsed.path == "/api/articles":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            all_articles = get_all_articles()
            resp = json.dumps({
                "total": len(all_articles),
                "annotated": sum(1 for a in all_articles if a["has_annotations"]),
                "unannotated": sum(1 for a in all_articles if not a["has_annotations"]),
                "articles": all_articles,
            })
            self.wfile.write(resp.encode("utf-8"))
            return

        if parsed.path.startswith("/api/articles/"):
            article_id = parsed.path[len("/api/articles/"):]
            article = get_article_by_id(article_id)
            if article:
                self._json_response(200, {"ok": True, "article": article})
            else:
                self._json_response(404, {"ok": False, "error": "Article not found"})
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_len = 0
        body = self.rfile.read(content_len).decode("utf-8") if content_len else "{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json_response(400, {"ok": False, "error": "Invalid JSON"})
            return

        if parsed.path == "/api/action":
            action = data.get("action", "")
            article_id = data.get("article_id", "")
            title = data.get("title", "")
            note = data.get("note", "")
            enqueue_action(action, article_id, title, note)
            self._json_response(200, {"ok": True, "action": action})
            return

        if parsed.path == "/api/brainstorm":
            article_id = data.get("article_id", "")
            title = data.get("title", "")
            url = data.get("url", "")
            notes = data.get("notes", "")
            path = write_brainstorm_note(title, url, notes)
            self._json_response(200, {"ok": True, "path": path})
            return

        self._json_response(404, {"ok": False, "error": "Not found"})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="gBrain Review Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    args = parser.parse_args()

    server = http.server.HTTPServer(("127.0.0.1", args.port), ReviewHandler)
    
    print(f"")
    print(f"  📋 gBrain Review Dashboard")
    print(f"  ─────────────────────────")
    print(f"  Serving at: http://127.0.0.1:{args.port}")
    print(f"  Open this in your browser on a large screen.")
    print(f"  Press Ctrl+C to stop.")
    print(f"")

    if args.open:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
