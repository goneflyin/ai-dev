#!/usr/bin/env python3
"""
Todoist API helper for Hermes' personal task management system.

Usage (from execute_code or terminal):
    from hermes_tools import terminal
    terminal("python3 ~/gbrain/todoist_helper.py create 'Buy milk' --project personal")
    terminal("python3 ~/gbrain/todoist_helper.py create 'Review PR' --project work --priority 4")
    terminal("python3 ~/gbrain/todoist_helper.py create 'Read article' --project misc --due tomorrow --url https://...")
    terminal("python3 ~/gbrain/todoist_helper.py list")  # view tasks
    terminal("python3 ~/gbrain/todoist_helper.py projects")  # view projects
"""

import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = "https://api.todoist.com/api/v1"

PROJECT_MAP = {
    "inbox": "6Crf5Gc48crVjMq9",
    "work": "6gFgv9qCG9944X5c",
    "personal": "6gFgv9pQJcchprmW",
    "misc": "6gFgv9pMjXhrJWQW",
    "closet": "6gFgx48hX5c8Gwpf",
    "tools": "6gFjFwCrHjpFFMm7",
    "apartment": "6gFjFwCHwV589JmG",
    "archive": "6gFgv9r9Ppg24wGx",
}

def get_token():
    token = os.environ.get("HERMES_TODOIST_TOKEN")
    if not token:
        # Fallback: try from .env
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("HERMES_TODOIST_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break
    if not token:
        sys.exit("Error: HERMES_TODOIST_TOKEN not set")
    return token

def api_request(method, path, data=None):
    token = get_token()
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            if raw:
                return json.loads(raw)
            return {"status": "ok"}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        sys.exit(f"HTTP {e.code}: {body}")
    except Exception as e:
        sys.exit(f"Error: {e}")

def create_task(content, project=None, priority=1, due=None, url=None, labels=None):
    body = {"content": content, "priority": priority}
    if project:
        pid = PROJECT_MAP.get(project.lower())
        if not pid:
            sys.exit(f"Unknown project: {project}. Options: {', '.join(PROJECT_MAP.keys())}")
        body["project_id"] = pid
    if due:
        body["due_string"] = due
    if url:
        body["description"] = url
    if labels:
        body["labels"] = labels if isinstance(labels, list) else [labels]
    result = api_request("POST", "/tasks", body)
    print(f"✅ Created: {result.get('content', content)}")
    if project:
        print(f"   Project: {project}")
    print(f"   ID: {result.get('id', 'unknown')}")
    return result

def list_tasks(project=None):
    path = "/tasks"
    if project:
        pid = PROJECT_MAP.get(project.lower())
        if pid:
            path += f"?project_id={pid}"
    tasks = api_request("GET", path)
    results = tasks.get("results", tasks if isinstance(tasks, list) else [])
    if not results:
        print("No tasks found.")
        return
    for t in results:
        due_str = f"  Due: {t.get('due', {}).get('string', 'none')}" if t.get('due') else ""
        print(f"  [{t.get('priority', 1)}] {t.get('content')}{due_str}")

def list_projects():
    result = api_request("GET", "/projects")
    projects = result.get("results", result if isinstance(result, list) else [])
    print("Projects:")
    for p in projects:
        name = p.get("name", "?")
        pid = p.get("id", "?")
        inbox = " (Inbox)" if p.get("inbox_project") else ""
        arch = " (archived)" if p.get("is_archived") else ""
        print(f"  {pid}  {name}{inbox}{arch}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create":
        if len(sys.argv) < 3:
            sys.exit("Usage: todoist_helper.py create <task content> [--project <name>] [--priority N] [--due <string>] [--url <url>]")

        content = sys.argv[2]
        project = None
        priority = 1
        due = None
        url = None
        labels = None

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--project" and i + 1 < len(sys.argv):
                project = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                priority = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--due" and i + 1 < len(sys.argv):
                due = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--url" and i + 1 < len(sys.argv):
                url = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--labels" and i + 1 < len(sys.argv):
                labels = sys.argv[i + 1].split(",")
                i += 2
            else:
                i += 1

        create_task(content, project, priority, due, url, labels)

    elif cmd == "list":
        project = sys.argv[2] if len(sys.argv) > 2 else None
        list_tasks(project)

    elif cmd == "projects":
        list_projects()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)