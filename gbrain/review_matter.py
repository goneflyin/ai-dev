#!/usr/bin/env python3
"""
gBrain Review Session
Two-pass review of captured articles.

Pass 1: Annotated articles (high priority) — each with your notes + highlight
Pass 2: Unannotated captures — scan and react to anything relevant

Actions per article:
  c   → Create task (Todoist — queued until API wired up)
  a   → Archive (remove from inbox / mark addressed)
  s   → Save for later (leave in place)
  n   → Skip (do nothing this session)
  q   → Quit session

Usage:
    python3 review_matter.py [--limit N] [--pass 1|2]
    python3 review_matter.py --nudge     # Send nudge only
"""

import os
import json
import sys
import argparse
import urllib.parse
from pathlib import Path
from datetime import datetime

# Paths
GBRAIN_DIR = Path.home() / "gbrain"
ARTICLES_DIR = GBRAIN_DIR / "articles"
ANNOTATIONS_FILE = GBRAIN_DIR / "annotations.jsonl"
ACTION_QUEUE = GBRAIN_DIR / "action-queue.json"

# Telegram config
TELEGRAM_CHAT_ID = os.environ.get("HERMES_HOME_CHAT_ID", "1759092294")

# ANSI colors (fallback if no colorama)
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
DIM = "\033[2m"


def load_articles():
    """Load all article markdown files."""
    articles = []
    for md_path in ARTICLES_DIR.rglob("*.md"):
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        articles.append({'path': md_path, 'content': content})
    return articles


def parse_frontmatter(content):
    """Extract YAML frontmatter fields."""
    lines = content.split('\n')
    if not lines or lines[0] != '---':
        return {}
    end = content.index('\n---\n', 4)
    fm_text = content[4:end]
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key = line.split(':', 1)[0].strip()
            val = line.split(':', 1)[1].strip()
            fm[key] = val
    return fm


def extract_highlights(content):
    """Pull My Highlights section from article markdown."""
    highlights = []
    in_section = False
    for line in content.split('\n'):
        if line.strip() == '## My Highlights & Notes':
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_line := in_section and line.strip():
            highlights.append(line.strip())
    return highlights


def get_article_title(content):
    """Get title from markdown (first H1 or frontmatter)."""
    fm = parse_frontmatter(content)
    if fm.get('title'):
        return fm['title']
    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return 'Untitled'


def is_annotated(article):
    """Check if article has annotations from annotations.jsonl."""
    if not ANNOTATIONS_FILE.exists():
        return False
    fm = parse_frontmatter(article['content'])
    matter_id = fm.get('matter_id', '')
    if not matter_id:
        return False
    with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                if record.get('article_id') == matter_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def get_annotations_for_article(matter_id):
    """Get all annotation records for a given article."""
    annotations = []
    if not ANNOTATIONS_FILE.exists():
        return annotations
    with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                if record.get('article_id') == matter_id:
                    annotations.append(record)
            except json.JSONDecodeError:
                continue
    return annotations


def get_article_url(article):
    """Get URL from frontmatter."""
    fm = parse_frontmatter(article['content'])
    return fm.get('url', 'No URL')


def enqueue_action(action_type, article, note=""):
    """Write action to the pending action queue."""
    fm = parse_frontmatter(article['content'])
    entry = {
        'action': action_type,
        'timestamp': datetime.now().isoformat(),
        'matter_id': fm.get('matter_id', ''),
        'title': get_article_title(article['content']),
        'url': get_article_url(article),
        'note': note,
    }
    if ANNOTATIONS_FILE.exists():
        matter_id = fm.get('matter_id', '')
        anns = get_annotations_for_article(matter_id)
        if anns:
            entry['annotations'] = anns

    queue = []
    if ACTION_QUEUE.exists():
        with open(ACTION_QUEUE, 'r') as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = []

    queue.append(entry)
    with open(ACTION_QUEUE, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    return entry


def display_annotated_pass(articles):
    """Pass 1: Review annotated articles."""
    annotated = [a for a in articles if is_annotated(a)]
    if not annotated:
        print(f"\n{BOLD}{DIM}No annotated articles this session.{RESET}")
        return []

    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  PASS 1 — Annotated Articles ({len(annotated)}){RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{DIM}  These have your personal notes. Quick decision.{RESET}\n")

    results = []
    for i, article in enumerate(annotated, 1):
        title = get_article_title(article['content'])
        url = get_article_url(article)
        fm = parse_frontmatter(article['content'])
        matter_id = fm.get('matter_id', '')
        annotations = get_annotations_for_article(matter_id)

        print(f"{BOLD}{i}. {title}{RESET}")
        if url and url != 'No URL':
            print(f"   {DIM}{url}{RESET}")
        print(f"   ID: {matter_id}")

        if annotations:
            print(f"\n   {BOLD}{YELLOW}📝 Your annotations:{RESET}")
            for ann in annotations:
                if ann.get('note'):
                    print(f"   {YELLOW}→ Note: {ann['note']}{RESET}")
                print(f"   {DIM}> {ann.get('highlight', '')[:200]}{RESET}")
                if ann.get('date'):
                    print(f"   {DIM}  — {ann['date']}{RESET}")
                print()

        print(f"   {GREEN}[c]{RESET} Create task  {GREEN}[a]{RESET} Archive  {GREEN}[s]{RESET} Save for later  {GREEN}[n]{RESET} Skip  {GREEN}[q]{RESET} Quit")

        while True:
            try:
                response = input(f"   Your choice: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n\nSession interrupted.")
                sys.exit(0)

            if response == 'q':
                print("\nQuitting session.")
                sys.exit(0)
            elif response in ('c', 'a', 's', 'n'):
                break
            else:
                print(f"   {RED}Unknown choice. Use c, a, s, n, or q.{RESET}")
                print(f"   Your choice: ", end="")

        if response == 'q':
            sys.exit(0)

        if response != 'n':
            entry = enqueue_action(
                {'c': 'create_task', 'a': 'archive', 's': 'save_for_later'}[response],
                article
            )
            action_labels = {'create_task': '→ Task queued', 'archive': '→ Archived', 'save_for_later': '→ Saved for later'}
            print(f"   {GREEN}{action_labels[response]}{RESET}")
            results.append((response, entry))

        print()

    return results


def display_unannotated_pass(articles, limit=20):
    """Pass 2: Scan unannotated captures."""
    unannotated = [a for a in articles if not is_annotated(a)]
    if not unannotated:
        print(f"\n{BOLD}{DIM}No unannotated captures this session.{RESET}")
        return []

    # Paginate
    total = len(unannotated)
    page = 0
    page_size = limit
    results = []

    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  PASS 2 — Unannotated Captures ({total} total){RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{DIM}  These caught your eye but without notes.{RESET}")
    print(f"{DIM}  Scan the titles. React if anything jumps out.{RESET}\n")

    while True:
        start = page * page_size
        end = min(start + page_size, total)
        batch = unannotated[start:end]

        print(f"{BOLD}Showing {start + 1}–{end} of {total}{RESET}\n")
        for i, article in enumerate(batch, start + 1):
            title = get_article_title(article['content'])
            url = get_article_url(article)
            print(f"  {BOLD}{i}.{RESET} {title}")
            if url and url != 'No URL':
                print(f"      {DIM}{url[:80]}{RESET}")
            print()

        # Prompt for reaction
        print(f"  {GREEN}[r]{RESET} React to a number  {GREEN}[n]{RESET} Nothing here, next  {GREEN}[q]{RESET} Quit")

        while True:
            try:
                response = input(f"  Your choice: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nSession interrupted.")
                sys.exit(0)

            if response == 'q':
                print("\nQuitting session.")
                sys.exit(0)
            elif response in ('n', 'r'):
                break
            else:
                print(f"  {RED}Use r (react), n (next/skip), or q (quit).{RESET}")
                print(f"  Your choice: ", end="")

        if response == 'q':
            sys.exit(0)

        if response == 'n':
            # Nothing from this page — check if more pages
            if end < total:
                page += 1
                continue
            else:
                print(f"\n  {DIM}Done with unannotated pass.{RESET}")
                break

        if response == 'r':
            # React to a specific number
            while True:
                try:
                    num_str = input(f"  Article number to react to ({start + 1}–{end}): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    sys.exit(0)
                if not num_str:
                    break
                try:
                    num = int(num_str)
                    if start < num <= end:
                        selected = batch[num - start - 1]
                        break
                    else:
                        print(f"  {RED}Number out of range.{RESET}")
                        continue
                except ValueError:
                    print(f"  {RED}Enter a number.{RESET}")
                    continue

            if not num_str:
                continue

            selected = batch[num - start - 1]
            sel_num = num  # global index

            title = get_article_title(selected['content'])
            url = get_article_url(selected)
            print(f"\n  {BOLD}Selected: {title}{RESET}")
            if url and url != 'No URL':
                print(f"  {DIM}{url}{RESET}")
            print(f"\n  {GREEN}[c]{RESET} Create task  {GREEN}[a]{RESET} Archive  {GREEN}[s]{RESET} Save for later  {GREEN}[n]{RESET} Skip")

            while True:
                try:
                    action = input(f"  Your choice: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    sys.exit(0)
                if action in ('c', 'a', 's', 'n'):
                    break
                else:
                    print(f"  {RED}Use c, a, s, or n.{RESET}")
                    print(f"  Your choice: ", end="")

            if action in ('c', 'a', 's'):
                entry = enqueue_action(
                    {'c': 'create_task', 'a': 'archive', 's': 'save_for_later'}[action],
                    selected
                )
                action_labels = {'create_task': '→ Task queued', 'archive': '→ Archived', 'save_for_later': '→ Saved for later'}
                print(f"  {GREEN}{action_labels[action]}{RESET}")
                results.append((action, entry))
            print()

            # Continue to next page
            if end < total:
                page += 1
                continue
            else:
                break

    return results


def run_review_session():
    """Run the full two-pass review session."""
    print(f"\\n{BOLD}{GREEN}🧠 gBrain Review Session{RESET}")
    print(f"{DIM}Started at {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}\n")

    articles = load_articles()
    print(f"Loaded {len(articles)} articles from gbrain\n")

    results = []

    # Pass 1: Annotated
    annotated_results = display_annotated_pass(articles)
    results.extend(annotated_results)

    # Pass 2: Unannotated
    unannotated_results = display_unannotated_pass(articles)
    results.extend(unannotated_results)

    # Summary
    created = sum(1 for r, _ in results if r == 'c')
    archived = sum(1 for r, _ in results if r == 'a')
    saved = sum(1 for r, _ in results if r == 's')
    skipped = sum(1 for r, _ in results if r == 'n')
    total = len(results)

    print(f"\n{BOLD}{GREEN}{'═' * 60}{RESET}")
    print(f"{BOLD}{GREEN}  Session Complete{RESET}")
    print(f"{BOLD}{GREEN}{'═' * 60}{RESET}")
    if total == 0:
        print(f"  {DIM}No actions taken.{RESET}")
    else:
        print(f"  Tasks created: {BOLD}{created}{RESET}")
        print(f"  Archived: {BOLD}{archived}{RESET}")
        print(f"  Saved for later: {BOLD}{saved}{RESET}")
        print(f"  Skipped: {skipped}")
    print(f"\n  Action queue: {ACTION_QUEUE}")

    return results


# ── CLI ─────────────────────────────────────────────────────────────────────────────

def get_recent_unannotated(articles, count=3):
    """Pick the most recently synced unannotated articles for highlighting."""
    unannotated = [a for a in articles if not is_annotated(a)]
    
    # Try to sort by date_synced descending
    def sort_key(a):
        fm = parse_frontmatter(a['content'])
        ds = fm.get('date_synced', '') or fm.get('date_saved', '') or ''
        return ds
    
    unannotated.sort(key=sort_key, reverse=True)
    return unannotated[:count]


def format_highlights(articles):
    """Build the [nudge_highlights] block from a list of articles."""
    lines = []
    for a in articles:
        content = a['content']
        title = get_article_title(content)
        fm = parse_frontmatter(content)
        source = fm.get('source', '') or fm.get('author', '') or ''
        source_str = source[:40] if source else ''
        saved = (fm.get('date_saved', '') or fm.get('date_synced', '') or '')[:10]
        lines.append(f"title: {title} | source: {source_str} | saved: {saved}")
    return lines


def send_telegram_nudge(annotated_count, unannotated_count, article_highlights=None):
    """Send the daily nudge via Hermes send_message tool.
    
    When run as part of a Hermes cron job, this function outputs the counts
    and highlights in a parseable format. The cron job's agent uses Hermes' 
    send_message tool to actually deliver to Telegram.
    
    When run standalone (e.g., terminal), sends via Telegram Bot API directly.
    """
    total = annotated_count + unannotated_count

    # Output format: Hermes cron agents can parse this
    print(f"[nudge_counts] annotated={annotated_count} unannotated={unannotated_count} total={total}")
    
    if article_highlights:
        print("[nudge_highlights]")
        for hl in article_highlights:
            print(hl)

    # Build message with highlights if available
    if annotated_count > 0:
        msg = f"📋 *{annotated_count} annotated captures* worth a look"
    elif article_highlights and unannotated_count > 0:
        msg = f"📋 *Morning check — {unannotated_count} in queue*"
        for hl in article_highlights[:2]:
            parts = hl.split(" | ")
            title = parts[0].replace("title: ", "") if len(parts) > 0 else ""
            source = parts[1].replace("source: ", "") if len(parts) > 1 else ""
            msg += f"\n• *{title}*"
            if source:
                msg += f" — {source}"
    else:
        msg = f"📋 *gBrain Review* — {total} captures in queue"

    # Try Hermes send_message first (works in cron job context)
    try:
        from hermes_tools import send_message as _sm
        if _sm and callable(_sm):
            _sm(action='send', message=msg, target="telegram:1759092294")
            print("[nudge] Sent via Hermes send_message")
            return True
    except (ImportError, Exception):
        pass

    # Fallback: direct Telegram Bot API
    tg_token = os.environ.get("HERMES_TELEGRAM_TOKEN", "")
    chat_id = TELEGRAM_CHAT_ID

    if not tg_token:
        print("[nudge] No HERMES_TELEGRAM_TOKEN set — counts logged above for cron agent to pick up")
        return False

    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': msg,
        'parse_mode': 'Markdown',
    }).encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tg_token}/sendMessage",
        data=data,
        method='POST'
    )
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"[nudge] Sent via Telegram Bot API")
                return True
    except Exception as e:
        print(f"[nudge] Telegram API failed: {e}")

    return False


if __name__ == "__main__":
    import urllib.parse

    parser = argparse.ArgumentParser(description='gBrain Review Session')
    parser.add_argument('--nudge', action='store_true', help='Send Telegram nudge only')
    parser.add_argument('--limit', type=int, default=20, help='Unannotated pass page size')
    args = parser.parse_args()

    if args.nudge:
        articles = load_articles()
        annotated = [a for a in articles if is_annotated(a)]
        unannotated = [a for a in articles if not is_annotated(a)]
        highlights = get_recent_unannotated(articles, count=3)
        hl_formatted = format_highlights(highlights)
        send_telegram_nudge(len(annotated), len(unannotated), article_highlights=hl_formatted)
    else:
        run_review_session()