#!/usr/bin/env python3
"""
Matter to gBrain Sync Script
Fetches articles (via public API) and notebook notes (via internal queue_feed API).

Usage:
    python3 sync_matter.py [--full] [--limit N]
    
Options:
    --full      Re-fetch all items (ignores sync log)
    --limit N   Only fetch N items (for testing)
    --notes     Sync notebook notes only
    --articles  Sync articles only (default: both)
"""

import os
import json
import time
import re
import argparse
from datetime import datetime
from pathlib import Path
import requests

# Configuration
PUBLIC_API_BASE = "https://api.getmatter.com/public/v1"
INTERNAL_API_BASE = "https://api.getmatter.app/api/v11"
API_TOKEN = "mat_f8e13ee38d374afc81c86c7b9f28d9691b56"
INTERNAL_TOKEN_PATH = Path.home() / ".matter_internal_tokens.json"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Rate limiting
RATE_LIMIT_SLEEP = 5.0
RETRY_429_DELAY = 60
MAX_RETRIES = 3

# Paths
GBRAIN_DIR = Path.home() / "gbrain"
ARTICLES_DIR = GBRAIN_DIR / "articles"
NOTES_DIR = GBRAIN_DIR / "notes"
SYNC_LOG = GBRAIN_DIR / "sync-log.json"
ANNOTATIONS_FILE = GBRAIN_DIR / "annotations.jsonl"


def load_internal_tokens():
    """Load OAuth tokens from QR login."""
    if INTERNAL_TOKEN_PATH.exists():
        with open(INTERNAL_TOKEN_PATH, "r") as f:
            return json.load(f)
    return None


def get_internal_headers():
    """Get headers with internal OAuth token."""
    tokens = load_internal_tokens()
    if not tokens:
        print("⚠️  No internal tokens found. Run QR login first.")
        return None
    return {"Authorization": f"Bearer {tokens['access_token']}", "Content-Type": "application/json"}


def ensure_dirs():
    """Create necessary directories."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    (ARTICLES_DIR / "inbox").mkdir(exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)


def load_sync_log():
    """Load previous sync state."""
    if SYNC_LOG.exists():
        with open(SYNC_LOG, 'r') as f:
            return json.load(f)
    return {"last_sync": None, "synced_items": {}, "synced_notes": {}}


def save_sync_log(log):
    """Save sync state."""
    with open(SYNC_LOG, 'w') as f:
        json.dump(log, f, indent=2)


def make_slug(title, item_id):
    """Create filesystem-safe slug from title."""
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    slug = slug[:100]
    return f"{slug}-{item_id}"


def save_note_to_file(note_item, sync_log):
    """Save a notebook note as a markdown file."""
    content = note_item["content"]
    note = content["my_note"]
    note_id = note["id"]
    content_id = content["id"]
    library_item_id = note_item["id"]
    
    # Check if already synced
    if not sync_log.get("synced_notes", {}).get(note_id) and not sync_log.get("synced_items", {}).get(content_id):
        pass  # Will be saved fresh
    
    # Create filename
    slug = make_slug(content.get("title", "Untitled"), content_id)
    filename = NOTES_DIR / f"{slug}.md"
    
    # Build markdown
    md_lines = ["---"]
    md_lines.append(f"title: {content.get('title', 'Untitled')}")
    md_lines.append(f"url: {content.get('url', '')}")
    md_lines.append(f"note_id: {note_id}")
    md_lines.append(f"content_id: {content_id}")
    md_lines.append(f"library_item_id: {library_item_id}")
    md_lines.append(f"created: {note['created_date']}")
    md_lines.append(f"modified: {note['modified_date']}")
    md_lines.append(f"source: matter")
    md_lines.append(f"date_synced: {datetime.now().isoformat()}")
    md_lines.append("---\n")
    
    md_lines.append(f"# {content.get('title', 'Untitled')}\n")
    md_lines.append(f"[Source]({content.get('url', '')})  \n")
    md_lines.append(f"_Saved: {note['created_date'][:10]}_\n")
    md_lines.append("\n## Notebook Note\n")
    md_lines.append(note["note"])
    md_lines.append("\n\n## Article Summary\n")
    
    # Try to get article excerpt from content
    excerpt = content.get("excerpt", "")
    if excerpt:
        md_lines.append(f"> {excerpt}\n")
    
    # Write file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    return filename


def sync_notes(sync_log):
    """Sync notebook notes from internal queue_feed API."""
    print("📝 Fetching notebook notes from Matter queue_feed...")
    
    headers = get_internal_headers()
    if not headers:
        return 0, 0
    
    try:
        r = requests.get(INTERNAL_API_BASE + "/library_items/queue_feed", headers=headers)
        if r.status_code != 200:
            print(f"⚠️  queue_feed returned {r.status_code}: {r.text[:200]}")
            return 0, 0
        
        d = r.json()
        feed = d.get("feed", [])
        
        note_items = [f for f in feed if f.get("content", {}).get("my_note")]
        print(f"   Found {len(note_items)} items with notebook notes in queue_feed")
        
        synced = 0
        skipped = 0
        
        for item in note_items:
            content = item["content"]
            note = content["my_note"]
            note_id = note["id"]
            content_id = content["id"]
            
            # Skip if already synced (check both notes and items logs)
            if sync_log.get("synced_notes", {}).get(note_id) or sync_log.get("synced_items", {}).get(content_id):
                skipped += 1
                continue
            
            filename = save_note_to_file(item, sync_log)
            print(f"   ✅ Saved note: {content.get('title', '')[:50]}...")
            
            # Update sync log
            if "synced_notes" not in sync_log:
                sync_log["synced_notes"] = {}
            sync_log["synced_notes"][note_id] = {
                "synced_at": datetime.now().isoformat(),
                "file": str(filename.relative_to(GBRAIN_DIR)),
                "content_id": content_id
            }
            
            synced += 1
        
        return synced, skipped
        
    except Exception as e:
        print(f"⚠️  Error fetching notes: {e}")
        return 0, 0


def annotate_article_to_file(item, highlights):
    """Write article highlights + notes to annotations.jsonl for Hermes memory indexing."""
    title = item.get('title', 'Untitled')
    url = item.get('url', '')
    article_id = item['id']

    if not highlights:
        return

    with open(ANNOTATIONS_FILE, 'a', encoding='utf-8') as f:
        for h in highlights:
            text = h.get('text', '').strip()
            note = h.get('note', '').strip()
            if not text:
                continue

            record = {
                'article_id': article_id,
                'title': title,
                'url': url,
                'highlight': text,
                'note': note,
                'date': h.get('created_at', '')[:10]
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def save_article(item, markdown_content, highlights=None):
    """Save article as markdown file with frontmatter."""
    if item.get('status') == 'inbox':
        folder = ARTICLES_DIR / "inbox"
    else:
        save_date = item.get('saved_at', item.get('created_at', ''))
        if save_date:
            year = save_date[:4]
            month = save_date[5:7] if len(save_date) > 7 else 'unknown'
            folder = ARTICLES_DIR / year / month
        else:
            folder = ARTICLES_DIR / "inbox"
    
    folder.mkdir(parents=True, exist_ok=True)
    
    slug = make_slug(item.get('title', 'Untitled'), item['id'])
    filename = folder / f"{slug}.md"
    
    author = item.get('author', '')
    if isinstance(author, dict):
        author = author.get('name', '')
    
    frontmatter = {
        'title': item.get('title', ''),
        'url': item.get('url', ''),
        'source': item.get('source', ''),
        'author': author,
        'date_published': item.get('published_at', ''),
        'date_saved': item.get('saved_at', ''),
        'date_synced': datetime.now().isoformat(),
        'tags': item.get('tags', []),
        'favorite': item.get('is_favorite', False),
        'status': item.get('status', 'unknown'),
        'highlights_count': item.get('annotations_count', 0),
        'matter_id': item['id'],
        'content_type': item.get('content_type', 'article'),
    }
    
    md_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            md_lines.append(f"{key}: {json.dumps(value)}")
        elif isinstance(value, bool):
            md_lines.append(f"{key}: {str(value).lower()}")
        else:
            md_lines.append(f"{key}: {value}")
    md_lines.append("---\n")
    md_lines.append(f"# {item.get('title', 'Untitled')}\n")
    
    if highlights:
        md_lines.append("\n## My Highlights & Notes\n")
        for h in highlights:
            text = h.get('text', '')
            note = h.get('note', '')
            md_lines.append(f"> **{text}**")
            if note:
                md_lines.append(f"> 📝 My note: *{note}*")
            created = h.get('created_at', '')
            if created:
                md_lines.append(f">    — {created[:10]}")
            md_lines.append("")
        
        annotate_article_to_file(item, highlights)
    
    if markdown_content:
        md_lines.append("\n## Article Content\n")
        md_lines.append(markdown_content)
    
    md_lines.append("\n## Processing Notes\n")
    md_lines.append("*Space for your thoughts during review*\n")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    return filename


def fetch_all_items():
    """Fetch all items from Matter public API with pagination."""
    items = []
    cursor = None
    page = 1
    
    print("📥 Fetching item list from Matter public API...")
    
    while True:
        params = {'limit': 100, 'status': 'all'}
        if cursor:
            params['cursor'] = cursor
        
        response = requests.get(f"{PUBLIC_API_BASE}/items", headers=HEADERS, params=params)
        response.raise_for_status()
        
        data = response.json()
        batch = data.get('results', [])
        items.extend(batch)
        
        print(f"  Page {page}: {len(batch)} items (total: {len(items)})")
        
        if not data.get('has_more', False):
            break
        
        cursor = data.get('next_cursor')
        page += 1
    
    print(f"✅ Found {len(items)} total items")
    return items


def fetch_item_with_markdown(item_id):
    """Fetch single item with markdown content. Retry on 429 errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                f"{PUBLIC_API_BASE}/items/{item_id}",
                headers=HEADERS,
                params={'include': 'markdown'}
            )
            
            if response.status_code == 429:
                print(f"      ⏳ Rate limited (429), waiting {RETRY_429_DELAY}s...")
                time.sleep(RETRY_429_DELAY)
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"      ⚠️  Error: {e}, retrying in 5s...")
                time.sleep(5)
            else:
                print(f"  ❌ Error fetching item {item_id}: {e}")
                return None
    
    return None


def fetch_highlights(item_id):
    """Fetch annotations/highlights for an item."""
    try:
        response = requests.get(
            f"{PUBLIC_API_BASE}/items/{item_id}/annotations",
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except requests.exceptions.RequestException:
        return []


def sync_articles(full_resync=False, limit=None):
    """Sync articles from public API."""
    ensure_dirs()
    sync_log = load_sync_log()
    
    print("📄 Syncing articles from Matter public API...")
    print(f"   Sync log: {SYNC_LOG}\n")
    
    items = fetch_all_items()
    
    if limit:
        items = items[:limit]
        print(f"⚠️  Limiting to {limit} items (test mode)\n")
    
    synced = 0
    skipped = 0
    failed = 0
    
    for i, item in enumerate(items, 1):
        item_id = item['id']
        
        if not full_resync and item_id in sync_log.get('synced_items', {}):
            print(f"  [{i}/{len(items)}] ⏭️  Skipping {item_id} (already synced)")
            skipped += 1
            continue
        
        print(f"  [{i}/{len(items)}] 📄 Processing: {item.get('title', 'Untitled')[:60]}...")
        
        full_item = fetch_item_with_markdown(item_id)
        if not full_item:
            failed += 1
            continue
        
        highlights = fetch_highlights(item_id)
        time.sleep(0.5)
        
        filename = save_article(full_item, full_item.get('markdown', ''), highlights)
        
        print(f"      ✅ Saved to {filename.relative_to(GBRAIN_DIR)}")
        
        sync_log['synced_items'][item_id] = {
            'synced_at': datetime.now().isoformat(),
            'file': str(filename.relative_to(GBRAIN_DIR))
        }
        
        synced += 1
        time.sleep(RATE_LIMIT_SLEEP)
    
    sync_log['last_sync'] = datetime.now().isoformat()
    save_sync_log(sync_log)
    
    print(f"\n✅ Article sync complete!")
    print(f"   Synced: {synced} new items")
    print(f"   Skipped: {skipped} already synced")
    print(f"   Failed: {failed} errors")
    
    return synced, skipped, failed


def load_annotations_into_memory():
    """Ingest annotations from JSONL into Hermes memory for cross-session search."""
    if not ANNOTATIONS_FILE.exists():
        return 0

    count = 0
    seen = set()

    with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                key = f"{record['article_id']}_{record['date']}"
                if key in seen:
                    continue
                seen.add(key)

                title = record.get('title', '')
                highlight = record.get('highlight', '')[:200]
                note = record.get('note', '')
                url = record.get('url', '')

                content = f"Scott's annotation on '{title}'"
                if note:
                    content += f" | Note: {note}"
                content += f" | Highlighted: {highlight}"
                if url:
                    content += f" | Source: {url}"
                content += f" | Date: {record.get('date', '')}"

                import subprocess
                result = subprocess.run(
                    ['hermes', 'memory', 'add', 'user', key, content],
                    capture_output=True, text=True
                )
                count += 1
            except Exception:
                pass

    return count


def sync(full_resync=False, limit=None, notes_only=False, articles_only=False):
    """Main sync function."""
    ensure_dirs()
    sync_log = load_sync_log()
    
    total_synced = 0
    
    # Sync notes if not articles-only mode
    if not articles_only:
        note_synced, note_skipped = sync_notes(sync_log)
        total_synced += note_synced
    
    # Sync articles if not notes-only mode
    if not notes_only:
        article_synced, article_skipped, article_failed = sync_articles(
            full_resync=full_resync, limit=limit
        )
        total_synced += article_synced
        
        # Ingest annotations into Hermes memory
        if article_synced > 0:
            annot_count = load_annotations_into_memory()
            if annot_count > 0:
                print(f"   📝 Ingested {annot_count} annotations into Hermes memory")
    
    save_sync_log(sync_log)
    
    print(f"\n🎉 All sync complete! Total new items: {total_synced}")
    print(f"📂 Articles: {ARTICLES_DIR}")
    print(f"📝 Notes: {NOTES_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sync Matter articles + notes to local gBrain')
    parser.add_argument('--full', action='store_true', help='Full resync (ignore sync log)')
    parser.add_argument('--limit', type=int, help='Limit number of articles (for testing)')
    parser.add_argument('--notes', action='store_true', help='Sync notebook notes only')
    parser.add_argument('--articles', action='store_true', help='Sync articles only')
    parser.add_argument('--load-memory', action='store_true', help='Load annotations into Hermes memory only')
    
    args = parser.parse_args()
    
    try:
        if args.load_memory:
            count = load_annotations_into_memory()
            print(f"📝 Loaded {count} annotations into Hermes memory")
        else:
            sync(full_resync=args.full, limit=args.limit, 
                 notes_only=args.notes, articles_only=args.articles)
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise