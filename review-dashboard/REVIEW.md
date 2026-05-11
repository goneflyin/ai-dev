# Codex Review — gBrain Review Dashboard

Reviewer: Codex CLI
Files reviewed: `review_server.py` (source), `2026-05-11-0018-gbrain-review-dashboard-spec.md` (spec)

---

## Summary

**11 issues claimed → 2 false positives → 9 real issues (4 critical/high, 5 medium/low)**

---

## False Positive

### Issue #1 (claimed: "Escaping over-escaped") — FALSE POSITIVE

The review claimed all four `\n` patterns have `\\\\n` (4 backslashes in file) producing `\\n` in JS output. This was a misreading of the bytes repr. **The file actually has `\\n` (2 backslashes in file = `\n` in JS output = correct newline escape).** Verified by hex dump and by serving the JS and checking it with `node --check` (zero syntax errors).

---

## Real Issues

### CRITICAL

#### 1. XSS via `a.id` in sidebar onclick handler (line 602)

`onclick="selectArticle('${a.id}')"` — article ID is interpolated directly into an inline onclick handler without escaping. If a `matter_id` in frontmatter contains a single quote, arbitrary JS executes.

**Fix:** Use `data-article-id="${escapeHtml(a.id)}"` with `addEventListener` instead of inline onclick.

#### 2. CSS selector injection in `querySelector` (line 624)

`.article-item[onclick*="'${id}'"]` — article ID is interpolated into a CSS attribute selector without sanitization. Coupled to the onclick format above; fixing the onclick also fixes this.

### HIGH

#### 3. Directory traversal in `write_brainstorm_note` (line 158)

Slug is built from `article_title.lower().replace(' ', '-')[:40]` — no sanitization of path separators. Article title `../../../etc/passwd` escapes the notes directory.

**Fix:** `re.sub(r'[^a-zA-Z0-9_-]', '', safe_title)[:40]`

#### 4. Unhandled `ValueError` from malformed `Content-Length` (line 822)

`int(self.headers.get("Content-Length", 0))` raises `ValueError` if header is garbage. Not caught — would crash the handler for a single POST request.

**Fix:** Wrap in try/except, default to 0.

### MEDIUM

#### 5. Race condition in `enqueue_action` (lines 143-151)

Read-modify-write pattern without locking. Two near-simultaneous POSTs can overwrite each other. Low risk for single-user local app.

#### 6. Naive YAML frontmatter parser (lines 48-63)

Doesn't handle multi-line values, YAML lists, or quoted strings with colons. If Matter outputs complex YAML, metadata silently goes missing.

#### 7. `get_article_by_id` is O(n) full file scan (line 109)

Re-rglob and re-reads every `.md` on every article click. Not a problem at 55 articles, but doesn't scale.

#### 8. Missing Content-Type on 404 (line 816-818)

No `Content-Type` header on fallback 404 responses. Trivial to fix.

### SPEC OMNISSIONS

#### 9. Article scan scope is wrong in spec

Spec says `~/gbrain/articles/inbox/*.md` but code uses `ARTICLES_DIR.rglob("*.md")` — recursive, all subdirectories.

#### 10. Error states undocumented

Spec doesn't describe behavior when `annotations.jsonl` or `articles/` directory is missing.

---

## Verdict

The review was **valuable** — it caught 7 code issues I'd have missed (especially the XSS and directory traversal). Its main claim about broken escaping was wrong, but the other findings are real and worth fixing. The dashboard is functional but has security and correctness issues that should be addressed before it's more than a single-user local tool.