"""
Tests for review_server.py — corresponds to:
  features/server.feature
  features/articles_api.feature
  features/error_handling.feature
  features/markdown.feature
"""

import json
import sys
import http.client
import http.server
import socket
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import review_server


TEST_ARTICLE = """\
---
matter_id: test-article-001
title: Test Article
url: https://example.com/test
source: example.com
author: Test Author
date_saved: 2024-01-15T12:00:00
date_synced: 2024-01-16T12:00:00
tags: test, python
---

# Test Article

This is the article body with **bold** and *italic* text.

Here is a [link](https://example.com) and an image:
![alt text](https://example.com/img.png)

## Code Section

```python
print("hello world")
```

> This is a blockquote
"""


@pytest.fixture(scope="module")
def article_dir(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp("gbrain")
    articles = tmpdir / "articles"
    articles.mkdir()
    (articles / "test-article-001.md").write_text(TEST_ARTICLE)
    return tmpdir


@pytest.fixture(scope="module")
def server(article_dir):
    """Start server on a free port, yield (host, port), then shut down."""
    review_server.GBRAIN_DIR = article_dir
    review_server.ARTICLES_DIR = article_dir / "articles"
    review_server.ANNOTATIONS_FILE = article_dir / "annotations.jsonl"
    review_server.ACTION_QUEUE = article_dir / "action-queue.json"
    review_server.NOTES_DIR = article_dir / "notes"

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    httpd = http.server.HTTPServer(("127.0.0.1", port), review_server.ReviewHandler)
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()
    time.sleep(0.1)

    yield ("127.0.0.1", port)

    httpd.shutdown()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get(host, port, path):
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("GET", path)
    return conn.getresponse()


def _post(host, port, path, body_bytes, extra_headers=None):
    conn = http.client.HTTPConnection(host, port, timeout=5)
    headers = {"Content-Type": "application/json", "Content-Length": str(len(body_bytes))}
    if extra_headers:
        headers.update(extra_headers)
    conn.request("POST", path, body=body_bytes, headers=headers)
    return conn.getresponse()


# ── Feature: Server starts and responds ──────────────────────────────────────


class TestServerStart:
    """features/server.feature"""

    def test_root_returns_200(self, server):
        resp = _get(*server, "/")
        assert resp.status == 200

    def test_root_returns_html_content_type(self, server):
        resp = _get(*server, "/")
        assert "text/html" in resp.getheader("Content-Type", "")

    def test_dashboard_path_returns_200(self, server):
        resp = _get(*server, "/dashboard")
        assert resp.status == 200

    def test_html_body_contains_title(self, server):
        resp = _get(*server, "/")
        body = resp.read().decode("utf-8")
        assert "gBrain Review Dashboard" in body


# ── Feature: Article list API ────────────────────────────────────────────────


class TestArticleListAPI:
    """features/articles_api.feature — article list scenarios"""

    def test_articles_returns_200(self, server):
        resp = _get(*server, "/api/articles")
        assert resp.status == 200

    def test_articles_returns_json_content_type(self, server):
        resp = _get(*server, "/api/articles")
        assert "application/json" in resp.getheader("Content-Type", "")

    def test_articles_schema_has_required_keys(self, server):
        resp = _get(*server, "/api/articles")
        data = json.loads(resp.read())
        for key in ("total", "articles", "annotated", "unannotated"):
            assert key in data, f"Missing top-level key: {key}"

    def test_articles_list_contains_required_fields(self, server):
        resp = _get(*server, "/api/articles")
        data = json.loads(resp.read())
        assert data["total"] >= 1
        article = data["articles"][0]
        for field in ("id", "title", "url", "source", "has_annotations", "annotation_count"):
            assert field in article, f"Article missing field: {field}"

    def test_articles_list_does_not_include_full_content(self, server):
        resp = _get(*server, "/api/articles")
        data = json.loads(resp.read())
        for article in data["articles"]:
            assert "full_content" not in article


# ── Feature: Single article API ──────────────────────────────────────────────


class TestSingleArticleAPI:
    """features/articles_api.feature — single article scenarios"""

    def test_existing_article_returns_200(self, server):
        resp = _get(*server, "/api/articles/test-article-001")
        assert resp.status == 200

    def test_existing_article_has_ok_true(self, server):
        resp = _get(*server, "/api/articles/test-article-001")
        data = json.loads(resp.read())
        assert data["ok"] is True

    def test_existing_article_has_full_content(self, server):
        resp = _get(*server, "/api/articles/test-article-001")
        data = json.loads(resp.read())
        assert "full_content" in data["article"]

    def test_full_content_is_non_empty(self, server):
        resp = _get(*server, "/api/articles/test-article-001")
        data = json.loads(resp.read())
        assert len(data["article"]["full_content"]) > 0

    def test_article_title_matches_frontmatter(self, server):
        resp = _get(*server, "/api/articles/test-article-001")
        data = json.loads(resp.read())
        assert data["article"]["title"] == "Test Article"


# ── Feature: Error handling ───────────────────────────────────────────────────


class TestErrorHandling:
    """features/error_handling.feature"""

    def test_missing_article_returns_404(self, server):
        resp = _get(*server, "/api/articles/nonexistent-id-xyz")
        assert resp.status == 404

    def test_missing_article_returns_error_json(self, server):
        resp = _get(*server, "/api/articles/nonexistent-id-xyz")
        data = json.loads(resp.read())
        assert data["ok"] is False
        assert "error" in data

    def test_unknown_path_returns_404(self, server):
        resp = _get(*server, "/api/notarealendpoint")
        assert resp.status == 404

    def test_bad_content_length_handled_gracefully(self, server):
        body = b'{"action":"test","article_id":"x","title":"y"}'
        resp = _post(*server, "/api/action", body, extra_headers={"Content-Length": "notanumber"})
        assert resp.status in (200, 400, 500)

    def test_invalid_json_body_returns_400(self, server):
        body = b"not valid json"
        resp = _post(*server, "/api/action", body)
        assert resp.status == 400

    def test_invalid_json_body_has_ok_false(self, server):
        body = b"not valid json"
        resp = _post(*server, "/api/action", body)
        data = json.loads(resp.read())
        assert data["ok"] is False


# ── Feature: JavaScript parse verification ────────────────────────────────────


class TestJavaScriptParse:
    """features/markdown.feature — JavaScript parse verification"""

    def test_module_imports_without_syntax_error(self):
        # If we got here, the module imported cleanly
        assert review_server.DASHBOARD_HTML is not None

    def test_dashboard_html_is_non_empty_string(self):
        assert isinstance(review_server.DASHBOARD_HTML, str)
        assert len(review_server.DASHBOARD_HTML) > 1000

    def test_markdown_to_html_function_present(self):
        assert "function markdownToHtml" in review_server.DASHBOARD_HTML

    def test_load_articles_function_present(self):
        assert "function loadArticles" in review_server.DASHBOARD_HTML

    def test_select_article_function_present(self):
        assert "function selectArticle" in review_server.DASHBOARD_HTML

    def test_escape_html_function_present(self):
        assert "function escapeHtml" in review_server.DASHBOARD_HTML

    def test_filter_articles_function_present(self):
        assert "function filterArticles" in review_server.DASHBOARD_HTML


# ── Feature: Markdown rendering patterns ─────────────────────────────────────


class TestMarkdownRendering:
    """features/markdown.feature — Markdown rendering scenarios"""

    def test_link_pattern_produces_anchor_tags(self):
        assert 'target="_blank"' in review_server.DASHBOARD_HTML

    def test_code_block_produces_pre_code(self):
        html = review_server.DASHBOARD_HTML
        assert "<pre><code>" in html

    def test_image_pattern_is_present(self):
        # The JS function should render ![alt](url) as <img src=...>
        html = review_server.DASHBOARD_HTML
        assert "img src" in html

    def test_paragraph_double_newline_replacement(self):
        html = review_server.DASHBOARD_HTML
        assert "</p><p>" in html

    def test_h1_heading_pattern(self):
        html = review_server.DASHBOARD_HTML
        assert "<h1>" in html

    def test_h2_heading_pattern(self):
        html = review_server.DASHBOARD_HTML
        assert "<h2>" in html

    def test_h3_heading_pattern(self):
        html = review_server.DASHBOARD_HTML
        assert "<h3>" in html
