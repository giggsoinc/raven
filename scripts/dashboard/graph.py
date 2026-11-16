#!/usr/bin/env python3
"""
knowledge_graph.py — scan RavenVault markdown → knowledge-graph.json
TRACKED: docs/DEPRECATIONS.md — vault note map, not code OKF; do not delete this version.

Usage:
  python3 knowledge_graph.py
  python3 knowledge_graph.py --project fin-processor
  python3 knowledge_graph.py --days 30
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import time

_PKG_DIR = pathlib.Path(__file__).resolve().parent
_SCRIPT_DIR = _PKG_DIR.parent  # scripts/ — vault_common lives here
for _d in (str(_PKG_DIR), str(_SCRIPT_DIR)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

_HERE = __import__('pathlib').Path(__file__).resolve().parent
for _d in (_HERE, _HERE.parent / 'memory', _HERE.parent / 'routing'):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))
from vault_common import (  # noqa: E402
    CONCEPTS,
    DECISIONS,
    GRAPH_DIR,
    PROJECTS,
    SESSIONS,
    VAULT,
    ensure_dirs,
    extract_wikilinks,
    parse_frontmatter,
)

TYPE_DIRS = {
    "project": PROJECTS,
    "concept": CONCEPTS,
    "decision": DECISIONS,
    "session": SESSIONS,
}


def _node_id(rel: str) -> str:
    rel = rel.replace("\\", "/").lstrip("./")
    if rel.endswith(".md"):
        rel = rel[:-3]
    # normalize wikilink targets
    return rel.split("|")[0].strip()


def _session_too_old(path: pathlib.Path, days: int | None) -> bool:
    if days is None:
        return False
    try:
        mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        return mtime < datetime.datetime.now() - datetime.timedelta(days=days)
    except OSError:
        return False


_LOCAL_ROOTS = (
    "AntiGravity_Projects",
    "Projects",
    "Developer",
    "src",
    "code",
)
_SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".tox",
    "site-packages",
}


_DISCOVERY_CACHE: dict = {"at": 0.0, "depth": None, "rows": None, "error": ""}
LAST_DISCOVERY_ERROR = ""


def discovery_error() -> str:
    """Empty when the last local-repo scan succeeded."""
    return LAST_DISCOVERY_ERROR


def list_local_git_repos(max_depth: int = 3) -> list[dict]:
    """Git repos and Raven projects under the known local roots, plus the registry.

    A directory counts when it has `.git` or `.raven/manifest.json`. Results are
    cached for 60 seconds so one dashboard render does not walk the tree three times.
    One row per case-insensitive folder name. Shallower path wins.
    """
    global LAST_DISCOVERY_ERROR
    now = time.monotonic()
    cached = _DISCOVERY_CACHE
    if cached["rows"] is not None and cached["depth"] == max_depth and now - cached["at"] < 60:
        LAST_DISCOVERY_ERROR = cached["error"]
        return list(cached["rows"])
    try:
        rows = _scan_local_repos(max_depth)
    except Exception as exc:
        LAST_DISCOVERY_ERROR = f"{type(exc).__name__}: {exc}"
        cached.update(at=now, depth=max_depth, rows=[], error=LAST_DISCOVERY_ERROR)
        return []
    LAST_DISCOVERY_ERROR = ""
    cached.update(at=now, depth=max_depth, rows=rows, error="")
    return list(rows)


def _scan_local_repos(max_depth: int) -> list[dict]:
    found: dict[str, dict] = {}

    def consider(path: pathlib.Path) -> None:
        has_git = (path / ".git").exists()
        has_raven = (path / ".raven" / "manifest.json").is_file()
        if not has_git and not has_raven:
            return
        key = path.name.casefold()
        row = {"name": path.name, "path": str(path.resolve())}
        current = found.get(key)
        if current is None or len(pathlib.Path(row["path"]).parts) < len(pathlib.Path(current["path"]).parts):
            found[key] = row

    for root_name in _LOCAL_ROOTS:
        root = pathlib.Path.home() / root_name
        if not root.is_dir():
            continue
        for dirpath, dirnames, _files in os.walk(root, followlinks=False):
            current = pathlib.Path(dirpath)
            try:
                depth = len(current.relative_to(root).parts)
            except ValueError:
                depth = 0
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            if depth > max_depth:
                dirnames[:] = []
                continue
            consider(current)

    registry = pathlib.Path.home() / ".raven" / "registry.json"
    if registry.is_file():
        try:
            payload = json.loads(registry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        projects = payload.get("projects") if isinstance(payload, dict) else None
        rows = []
        if isinstance(projects, dict):
            rows = list(projects.values())
        elif isinstance(projects, list):
            rows = projects
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw = row.get("path") or row.get("root") or ""
            if not raw:
                continue
            registered = pathlib.Path(raw).expanduser()
            if (registered / ".git").exists():
                consider(registered)
            elif registered.is_dir():
                key = registered.name.casefold()
                found.setdefault(key, {"name": registered.name, "path": str(registered.resolve())})

    return sorted(found.values(), key=lambda item: item["name"].casefold())


def build_graph(project_filter: str | None = None, session_days: int | None = 30) -> dict:
    ensure_dirs()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(
        nid: str,
        ntype: str,
        path: str,
        label: str | None = None,
        tags=None,
        icon: str | None = None,
    ):
        if nid in nodes:
            # upgrade unknown stubs if we learn a better type/icon later
            existing = nodes[nid]
            if existing.get("type") in (None, "unknown") and ntype and ntype != "unknown":
                existing["type"] = ntype
            if icon and not existing.get("icon"):
                existing["icon"] = icon
            if label and existing.get("label") == nid.split("/")[-1]:
                existing["label"] = label
            return
        nodes[nid] = {
            "id": nid,
            "label": label or nid.split("/")[-1],
            "type": ntype,
            "path": path,
            "tags": tags or [ntype],
            "icon": icon,
        }

    for ntype, folder in TYPE_DIRS.items():
        if not folder.exists():
            continue
        for path in folder.glob("*.md"):
            if ntype == "session" and _session_too_old(path, session_days):
                continue
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            meta, body = parse_frontmatter(text)
            rel_id = f"{folder.name}/{path.stem}"
            proj = meta.get("project") or ""
            if project_filter:
                if ntype == "project" and path.stem != project_filter:
                    # still include if linked later — skip primary filter for non-matching project hubs
                    continue
                if ntype != "project":
                    if proj and proj != project_filter and project_filter not in path.stem:
                        continue
                    if not proj and project_filter not in path.stem and project_filter not in text[:500]:
                        continue
            ntype_final = meta.get("type") or ntype
            tags = []
            if "tags" in meta:
                raw = meta["tags"].strip("[]")
                tags = [t.strip() for t in raw.split(",") if t.strip()]
            add_node(
                rel_id,
                ntype_final,
                (str(path.relative_to(VAULT)) if str(path).startswith(str(VAULT)) else str(path)),
                label=meta.get("name") or meta.get("title") or path.stem,
                tags=tags or [ntype_final],
                icon=meta.get("icon"),
            )
            for link in extract_wikilinks(text):
                target = _node_id(link)
                if not target:
                    continue
                # skip anchors only
                if target.startswith("#"):
                    continue
                # ensure target node stub
                if target not in nodes:
                    ttype = "unknown"
                    if target.startswith("projects/"):
                        ttype = "project"
                    elif target.startswith("concepts/"):
                        ttype = "concept"
                    elif target.startswith("decisions/"):
                        ttype = "decision"
                    elif target.startswith("sessions/"):
                        ttype = "session"
                    add_node(target, ttype, f"{target}.md", label=target.split("/")[-1])
                edges.append(
                    {"source": rel_id, "target": target, "rel": "wikilink"}
                )
            # frontmatter related:
            if meta.get("related"):
                for part in re.split(r"[, ]+", meta["related"]):
                    t = _node_id(part)
                    if t:
                        edges.append(
                            {"source": rel_id, "target": t, "rel": "related"}
                        )

    # Local clones that never got a RavenVault hub still appear as project nodes.
    if not project_filter:
        known = {nid.split("/")[-1].casefold() for nid in nodes if nid.startswith("projects/")}
        for repo in list_local_git_repos():
            if repo["name"].casefold() in known:
                continue
            add_node(
                f"projects/{repo['name']}",
                "project",
                repo["path"],
                label=repo["name"],
                tags=["project", "local-repo"],
            )
            known.add(repo["name"].casefold())

    # Attach vibe-coder icons (data-URI + emoji) for dashboard / exporters
    try:
        from kg_icons import enrich_node  # type: ignore
    except ImportError:
        try:
            from scripts.kg_icons import enrich_node  # type: ignore
        except ImportError:
            enrich_node = None  # type: ignore

    node_list = list(nodes.values())
    if enrich_node:
        node_list = [enrich_node(n) for n in node_list]

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project_filter": project_filter,
        "session_days": session_days,
        "nodes": node_list,
        "edges": edges,
    }


def write_graph(graph: dict, out: pathlib.Path | None = None) -> pathlib.Path:
    ensure_dirs()
    out = out or (GRAPH_DIR / "knowledge-graph.json")
    out.write_text(json.dumps(graph, indent=2))
    return out


def main() -> None:
    print(
        "graph.py writes vault *notes* JSON only. Code dashboard is xray.render_html → raven-dashboard.html.",
        file=sys.stderr,
    )
    ap = argparse.ArgumentParser(description="Build RavenVault knowledge-graph.json (notes, not code OKF)")
    ap.add_argument("--project", default=None)
    ap.add_argument("--days", type=int, default=30, help="Session node window (default 30)")
    ap.add_argument("--all-sessions", action="store_true", help="Include all sessions")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    days = None if args.all_sessions else args.days
    g = build_graph(project_filter=args.project, session_days=days)
    if args.stdout:
        print(json.dumps(g, indent=2))
    else:
        path = write_graph(g)
        print(f"Wrote {path} ({len(g['nodes'])} nodes, {len(g['edges'])} edges)")


if __name__ == "__main__":
    main()
