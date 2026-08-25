#!/usr/bin/env python3
"""
xray.py — Raven Code-XRay: deterministic JSON code tree of the repo (no LLM).

The codebase is the skeleton; commit "whys" and session touches are
annotations pinned to the exact node they describe. AST + paths + docstrings
+ git only. Spec: docs/AUDIT/APPLY-PROMPT-code-tree-enterprise.md

Usage:
  python3 code-xray.py --build                      full scan → .raven/code-tree.json
  python3 code-xray.py --delta [--files f1 f2 …] [--session ID] [--commit SHA]
  python3 code-xray.py --digest [--for-prompt "…"]  ≤1500-token context payload
  python3 code-xray.py --html [--open]              self-contained tree view HTML
"""
from __future__ import annotations

import argparse
import ast
import datetime
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = pathlib.Path(
    os.environ.get("CLAUDE_PROJECT_DIR") or pathlib.Path(__file__).resolve().parent.parent.parent
)
TREE_PATH = REPO / ".raven" / "code-xray.json"
VAULT = pathlib.Path(os.environ.get("RAVEN_VAULT", str(pathlib.Path.home() / "RavenVault")))
TREES_DIR = VAULT / "dashboard" / "trees"
HTML_PATH = TREES_DIR / (REPO.name + ".html")

HISTORY_CAP = 5
SESSIONS_CAP = 10
COMMIT_CAP = 20
SYMBOL_DIFF_COMMITS = 5
OKF_SCHEMA = 1
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".raven", "dist", "build"}
SOURCE_EXT = {".py", ".js", ".ts", ".sh", ".md", ".yaml", ".yml", ".json", ".html", ".css"}
CONV_RX = re.compile(r"^(feat|fix|docs|refactor|test|chore|perf|style|ci|build)\(?([^):]*)\)?:\s*(.+)$")

ROLE_RULES = [
    (re.compile(r"-guard\.py$"), "guard"),
    (re.compile(r"-router\.py$"), "router"),
    (re.compile(r"(^|/)\.claude/skills/.*SKILL\.md$"), "skill"),
    (re.compile(r"(^|/)hooks/"), "hook"),
    (re.compile(r"(^|/)scripts/.*\.py$"), "script"),
    (re.compile(r"(^|/)docs/"), "doc"),
]

ROLE_COLORS = {
    "guard": "#e05252", "router": "#e0a030", "hook": "#4a90d9",
    "skill": "#9b6dd6", "script": "#8a949e", "doc": "#5aa87a",
    "entrypoint": "#38b2ac", "": "#8a949e",
}


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _hook_roles() -> dict[str, str]:
    """Map script path → hook:<Event> from .claude/settings.json."""
    out: dict[str, str] = {}
    try:
        cfg = json.loads((REPO / ".claude" / "settings.json").read_text())
        for event, groups in (cfg.get("hooks") or {}).items():
            for g in groups or []:
                for h in g.get("hooks") or []:
                    for m in re.finditer(r"([\w./-]+\.py)", h.get("command", "")):
                        name = pathlib.Path(m.group(1)).name
                        out.setdefault(name, f"hook:{event}")
    except Exception:
        pass
    return out


def _role(rel: str, hook_roles: dict[str, str]) -> str:
    name = pathlib.Path(rel).name
    if name in hook_roles:
        return hook_roles[name]
    for rx, role in ROLE_RULES:
        if rx.search(rel):
            return role
    return ""


def _purpose(path: pathlib.Path) -> tuple[str, list[str], list[str]]:
    """Return (purpose, functions, imports) for a file — AST for .py, first line otherwise."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return "", [], []
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
            doc = (ast.get_docstring(tree) or "").strip().splitlines()
            purpose = doc[0][:120] if doc else ""
            if purpose and len(doc) > 1 and len(purpose) < 30:
                purpose = " ".join(doc[:2])[:120]
            funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            imports: list[str] = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports += [a.name.split(".")[0] for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.module:
                    imports.append(n.module.split(".")[0])
            local = {p.stem for p in path.parent.glob("*.py")}
            imports = sorted({i for i in imports if i in local and i != path.stem})
            return purpose, funcs[:20], imports
        except SyntaxError:
            return "", [], []
    for line in text.splitlines()[:10]:
        s = line.strip().lstrip("#/<!-* \t").rstrip("->")
        if s and not s.startswith(("---", "!", "{", "import", "from")):
            return s[:120], [], []
    return "", [], []


def _git_history(rel: str, limit: int = HISTORY_CAP) -> list[dict]:
    raw = _run(["git", "log", f"-{limit}", "--follow", "--format=%h|%as|%s", "--", rel])
    out = []
    for line in raw.splitlines():
        try:
            sha, date, subj = line.split("|", 2)
        except ValueError:
            continue
        m = CONV_RX.match(subj)
        if m:
            out.append({"commit": sha, "kind": m.group(1), "scope": m.group(2), "why": m.group(3)[:150], "date": date})
        else:
            out.append({"commit": sha, "kind": "other", "scope": "", "why": subj[:150], "date": date})
    return out


def _churn_30d() -> dict[str, int]:
    since = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    raw = _run(["git", "log", f"--since={since}", "--name-only", "--format="])
    counts: dict[str, int] = {}
    for line in raw.splitlines():
        if line.strip():
            counts[line.strip()] = counts.get(line.strip(), 0) + 1
    return counts


def _tracked_files() -> list[str]:
    raw = _run(["git", "ls-files"])
    files = []
    for f in raw.splitlines():
        p = pathlib.Path(f)
        if p.suffix not in SOURCE_EXT:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(f)
    return files


def _py_symbols(rel: str) -> list[dict]:
    path = REPO / rel
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except (OSError, SyntaxError):
        return []
    out = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(n, ast.ClassDef) else "function"
            out.append({"id": f"sym:{rel}:{n.name}", "name": n.name, "kind": kind,
                        "file": rel, "line": getattr(n, "lineno", 1)})
    return out


def _commits(limit: int = COMMIT_CAP) -> list[dict]:
    raw = _run(["git", "log", f"-{limit}", "--format=%H|%h|%as|%s"])
    rows = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        full, short, date, subj = parts
        files = [f for f in _run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", full]).splitlines() if f]
        rows.append({"id": f"commit:{short}", "sha": full, "short": short, "date": date,
                     "subject": subj[:200], "files": files})
    return rows


def _symbol_names_at(rel: str, rev: str) -> set[str]:
    raw = _run(["git", "show", f"{rev}:{rel}"])
    if not raw or not rel.endswith(".py"):
        return set()
    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return set()
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
    return names


def build_okf(file_nodes: dict[str, dict]) -> dict:
    nodes: list[dict] = [{"id": f"project:{REPO.name}", "type": "project", "label": REPO.name}]
    edges: list[dict] = []
    for rel, fn in file_nodes.items():
        nodes.append({
            "id": f"file:{rel}", "type": "file", "label": rel, "role": fn.get("role", ""),
            "purpose": fn.get("purpose", ""), "churn_30d": fn.get("churn_30d", 0),
            "history": fn.get("history") or [],
        })
        edges.append({"from": f"project:{REPO.name}", "to": f"file:{rel}", "type": "contains", "tag": "EXTRACTED"})
        for imp in fn.get("imports") or []:
            # local import is module stem; match files
            for other in file_nodes:
                if pathlib.Path(other).stem == imp and other != rel:
                    edges.append({"from": f"file:{rel}", "to": f"file:{other}", "type": "imports", "tag": "EXTRACTED"})
        for sym in _py_symbols(rel):
            nodes.append({**sym, "type": "symbol", "label": f"{sym['name']} ({sym['kind']})"})
            edges.append({"from": f"file:{rel}", "to": sym["id"], "type": "defines", "tag": "EXTRACTED"})
    node_ids = {n["id"] for n in nodes}
    for i, c in enumerate(_commits()):
        nodes.append({
            "id": c["id"], "type": "commit", "label": c["short"], "sha": c["sha"],
            "date": c["date"], "subject": c["subject"], "files": c["files"],
            "summary": f"{c['short']} {c['date']} — {c['subject']}",
        })
        parent = _run(["git", "rev-parse", f"{c['sha']}^"]) or ""
        do_syms = i < SYMBOL_DIFF_COMMITS
        for rel in c["files"]:
            if f"file:{rel}" in node_ids:
                edges.append({"from": c["id"], "to": f"file:{rel}", "type": "touches", "tag": "EXTRACTED"})
            if do_syms and rel.endswith(".py") and parent:
                before = _symbol_names_at(rel, parent)
                after = _symbol_names_at(rel, c["sha"])
                for name in sorted(after.symmetric_difference(before)):
                    sid = f"sym:{rel}:{name}"
                    if sid in node_ids:
                        edges.append({"from": c["id"], "to": sid, "type": "changes_symbol", "tag": "EXTRACTED"})
    head = _run(["git", "rev-parse", "--short", "HEAD"])
    return {"schema": OKF_SCHEMA, "git_head": head, "nodes": nodes, "edges": edges}


def _okf(payload: dict | None = None) -> dict:
    t = payload or _load() or {}
    okf = t.get("okf")
    if okf and okf.get("nodes"):
        return okf
    return {"schema": OKF_SCHEMA, "git_head": "", "nodes": [], "edges": []}


EDGE_TYPES = {"touches", "imports", "defines", "changes_symbol", "contains"}


def resolve_commit_ref(ref: str) -> str:
    """HEAD / @ / full SHA → short SHA used on commit: nodes."""
    if not ref:
        return ""
    key = ref.strip()
    if key.upper() in ("HEAD", "@"):
        return _run(["git", "rev-parse", "--short", "HEAD"]) or key
    if len(key) >= 7 and all(c in "0123456789abcdef" for c in key.lower()):
        short = _run(["git", "rev-parse", "--short", key])
        return short or key[:7]
    return key


def query_graph(okf: dict, **filt) -> list[dict]:
    ntype = (filt.get("type") or "").strip()
    glob = (filt.get("path_glob") or "").strip()
    commit = (filt.get("commit") or "").strip()
    if ntype in EDGE_TYPES:
        src = None
        if commit:
            src = get_node(okf, commit)
        hits = []
        for e in okf.get("edges") or []:
            if e.get("type") != ntype:
                continue
            if e.get("tag") and e.get("tag") != "EXTRACTED":
                continue
            if src and e.get("from") != src["id"] and e.get("to") != src["id"]:
                continue
            hits.append(e)
        return hits[:80]
    out = []
    for n in okf.get("nodes") or []:
        if ntype and n.get("type") != ntype:
            continue
        if glob and glob not in (n.get("label") or n.get("id") or ""):
            continue
        out.append(n)
    return out[:80]


def get_node(okf: dict, nid: str) -> dict | None:
    if not nid:
        return None
    resolved = resolve_commit_ref(nid) if nid.upper() in ("HEAD", "@") or len(nid) >= 7 else nid
    keys = {nid, resolved, f"commit:{nid}", f"commit:{resolved}", f"file:{nid}"}
    for n in okf.get("nodes") or []:
        if n.get("id") in keys or n.get("label") == nid or n.get("short") in keys:
            return n
        sha = n.get("sha") or ""
        short = n.get("short") or ""
        if n.get("type") == "commit" and short and (
            nid.startswith(short) or short.startswith(nid) or (sha and sha.startswith(nid))
        ):
            return n
    return None


def get_neighbors(okf: dict, nid: str, edge_type: str = "") -> list[dict]:
    ids = {nid}
    node = get_node(okf, nid)
    if node:
        ids.add(node["id"])
    hits = []
    for e in okf.get("edges") or []:
        if edge_type and e.get("type") != edge_type:
            continue
        if e.get("from") in ids or e.get("to") in ids:
            hits.append(e)
    return hits[:80]


def shortest_path(okf: dict, a: str, b: str) -> list[str]:
    na, nb = get_node(okf, a), get_node(okf, b)
    if not na or not nb:
        return []
    start, goal = na["id"], nb["id"]
    adj: dict[str, list[str]] = {}
    for e in okf.get("edges") or []:
        adj.setdefault(e["from"], []).append(e["to"])
        adj.setdefault(e["to"], []).append(e["from"])
    q = [start]
    prev = {start: None}
    while q:
        cur = q.pop(0)
        if cur == goal:
            break
        for nxt in adj.get(cur, []):
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    if goal not in prev:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def commit_impact(okf: dict, sha: str) -> dict:
    node = get_node(okf, sha)
    if not node:
        return {"error": "commit not in OKF", "sha": resolve_commit_ref(sha) or sha}
    neigh = get_neighbors(okf, node["id"])
    files = [e["to"] for e in neigh if e["type"] == "touches"]
    syms = [e["to"] for e in neigh if e["type"] == "changes_symbol"]
    return {"commit": node, "files": files, "symbols": syms, "summary": node.get("summary", "")}


def find_gaps(okf: dict) -> list[dict]:
    gaps = []
    defined = {n["id"] for n in okf.get("nodes") or [] if n.get("type") == "symbol"}
    imported_files = {e["to"] for e in okf.get("edges") or [] if e.get("type") == "imports"}
    for n in okf.get("nodes") or []:
        if n.get("type") == "file" and str(n.get("label", "")).endswith(".py") and not n.get("purpose"):
            gaps.append({"kind": "no_purpose", "id": n["id"], "detail": n.get("label")})
        if n.get("type") == "file" and n.get("churn_30d", 0) and n["id"] not in imported_files and n.get("role") not in ("entrypoint",):
            if n.get("label", "").endswith(".py") and "/scripts/" not in str(n.get("label")):
                pass  # too noisy; skip generic
    # commits that touch two files with no imports edge
    file_ids = {n["id"] for n in okf.get("nodes") or [] if n.get("type") == "file"}
    import_pairs = {(e["from"], e["to"]) for e in okf.get("edges") or [] if e.get("type") == "imports"}
    for n in okf.get("nodes") or []:
        if n.get("type") != "commit":
            continue
        files = [f"file:{f}" for f in (n.get("files") or []) if f"file:{f}" in file_ids]
        if len(files) < 2:
            continue
        linked = False
        for i, a in enumerate(files):
            for b in files[i + 1 :]:
                if (a, b) in import_pairs or (b, a) in import_pairs:
                    linked = True
        if not linked and len(files) >= 2:
            gaps.append({"kind": "commit_unlinked_modules", "id": n["id"], "detail": n.get("subject", "")[:80]})
    return gaps[:40]


def _file_node(rel: str, hook_roles: dict, churn: dict) -> dict:
    purpose, funcs, imports = _purpose(REPO / rel)
    return {
        "id": rel, "type": "program", "role": _role(rel, hook_roles),
        "purpose": purpose, "functions": funcs, "imports": imports,
        "history": _git_history(rel), "churn_30d": churn.get(rel, 0), "sessions": [],
    }


def _to_tree(file_nodes: dict[str, dict]) -> dict:
    root = {"id": REPO.name, "type": "project", "children": []}
    dirs: dict[str, dict] = {"": root}

    def ensure_dir(d: str) -> dict:
        if d in dirs:
            return dirs[d]
        parent = ensure_dir(str(pathlib.PurePosixPath(d).parent) if "/" in d else "")
        node = {"id": d, "type": "module", "children": []}
        parent["children"].append(node)
        dirs[d] = node
        return node

    for rel in sorted(file_nodes):
        d = str(pathlib.PurePosixPath(rel).parent)
        parent = ensure_dir("" if d == "." else d)
        parent["children"].append(file_nodes[rel])
    return root


def _flatten(node: dict, out: dict[str, dict]) -> None:
    if node.get("type") == "program":
        out[node["id"]] = node
    for c in node.get("children", []):
        _flatten(c, out)


def _atomic_write(payload: dict) -> None:
    TREE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(TREE_PATH.parent), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, indent=1)
    os.replace(tmp, TREE_PATH)


def _load() -> dict | None:
    try:
        return json.loads(TREE_PATH.read_text())
    except Exception:
        return None


def live_git_head() -> str:
    """Short SHA of live HEAD for this REPO. Empty on failure."""
    return _run(["git", "rev-parse", "--short", "HEAD"])


def baked_git_head(tree: dict | None = None) -> str:
    """SHA stored on the last OKF bake (not history[0])."""
    t = tree if tree is not None else _load()
    if not t:
        return ""
    return str((t.get("okf") or {}).get("git_head") or "")


def head_drifted(tree: dict | None = None) -> bool:
    """True when baked okf.git_head differs from live HEAD (or bake missing)."""
    live = live_git_head()
    if not live:
        return False
    baked = baked_git_head(tree)
    return (not baked) or baked != live


def build(*, if_stale: int = 0) -> dict:
    if if_stale:
        old = _load()
        head = live_git_head()
        if old and (old.get("okf") or {}).get("git_head") == head:
            return old
    hook_roles = _hook_roles()
    churn = _churn_30d()
    file_nodes = {rel: _file_node(rel, hook_roles, churn) for rel in _tracked_files()}
    payload = {
        "version": 1,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "repo": REPO.name,
        "root": _to_tree(file_nodes),
        "okf": build_okf(file_nodes),
    }
    _atomic_write(payload)
    return payload


def delta(files: list[str], session: str | None, commit: str | None) -> int:
    tree = _load()
    if tree is None:
        build()
        return -1
    if not files:
        changed = _run(["git", "diff", "--name-only", "HEAD~1"]).splitlines()
        changed += [l[3:] for l in _run(["git", "status", "--short"]).splitlines() if len(l) > 3]
        files = [f.strip() for f in changed if f.strip()]
    flat: dict[str, dict] = {}
    _flatten(tree["root"], flat)
    hook_roles = _hook_roles()
    churn = _churn_30d()
    touched = 0
    rebuilt_nodes = dict(flat)
    for rel in files:
        p = REPO / rel
        if pathlib.Path(rel).suffix not in SOURCE_EXT or any(part in SKIP_DIRS for part in pathlib.Path(rel).parts):
            continue
        if not p.exists():
            if rel in rebuilt_nodes:
                rebuilt_nodes[rel]["deleted"] = True
                touched += 1
            continue
        node = _file_node(rel, hook_roles, churn)
        old = rebuilt_nodes.get(rel, {})
        node["sessions"] = old.get("sessions", [])
        if session and session not in node["sessions"]:
            node["sessions"] = (node["sessions"] + [session])[-SESSIONS_CAP:]
        rebuilt_nodes[rel] = node
        touched += 1
    live = {k: v for k, v in rebuilt_nodes.items() if not v.get("deleted")}
    tree["root"] = _to_tree(live)
    tree["okf"] = build_okf(live)
    tree["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    _atomic_write(tree)
    return touched


def digest(for_prompt: str | None = None) -> str:
    tree = _load() or build()
    flat: dict[str, dict] = {}
    _flatten(tree["root"], flat)
    lines = ["🩻 Raven Code-XRay (.raven/code-xray.json)"]
    mods: dict[str, int] = {}
    for rel in flat:
        top = rel.split("/")[0] if "/" in rel else "(root)"
        mods[top] = mods.get(top, 0) + 1
    lines.append("Shape: " + " · ".join(f"{m}({n})" for m, n in sorted(mods.items(), key=lambda x: -x[1])[:8]))
    hot = sorted(flat.values(), key=lambda n: -n.get("churn_30d", 0))[:10]
    lines.append("Hot nodes (30d churn · latest why):")
    for n in hot:
        if n.get("churn_30d", 0) == 0:
            break
        why = n["history"][0]["why"] if n.get("history") else "(no commits)"
        lines.append(f"  • {n['id']} ×{n['churn_30d']} — {why}")
    missing = [n["id"] for n in flat.values() if not n.get("purpose") and n["id"].endswith(".py")]
    if missing:
        lines.append(f"⚠ No purpose statement: {', '.join(missing[:6])}" + (" …" if len(missing) > 6 else ""))
    if for_prompt:
        low = for_prompt.lower()
        matched = [n for rel, n in flat.items()
                   if pathlib.Path(rel).name.lower() in low or rel.lower() in low][:3]
        for n in matched:
            lines.append(f"\nNode {n['id']}:")
            lines.append(json.dumps({k: n[k] for k in ("role", "purpose", "history", "sessions", "imports")}, indent=1))
    lines.append("Read the relevant subtree of .raven/code-xray.json before editing a file.")
    text = "\n".join(lines)
    return text[:6000]  # ~1500 tokens hard cap


def repo_summary() -> str:
    """First meaningful paragraph from README — what this repo is."""
    for name in ("README.md", "readme.md"):
        p = REPO / name
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("**") and s.endswith("**") and len(s) > 40:
                return s.strip("* ")[:400]
            if s.startswith("#"):
                continue
            if s.startswith("<"):
                continue
            if len(s) > 80:
                return s[:400]
    return ""


VIEWER_DIR = pathlib.Path(__file__).resolve().parent
OKF_JSON_RX = re.compile(
    r'<script[^>]*id=["\']okf["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def enrich_nodes(nodes: list) -> list:
    out = list(nodes or [])
    try:
        from icons import data_uri as icon_data_uri, emoji_for, resolve_icon_key
        for n in out:
            key = resolve_icon_key(
                ntype=n.get("type") or "",
                label=n.get("label") or "",
                node_id=n.get("id") or "",
                path=n.get("label") or "",
            )
            n["icon"] = key
            n["icon_uri"] = icon_data_uri(key)
            n["icon_emoji"] = emoji_for(key)
    except Exception:
        for n in out:
            n.setdefault("icon", "code")
            n.setdefault("icon_emoji", "💻")
    return out


def publish_viewer() -> pathlib.Path:
    dest = VAULT / "dashboard"
    dest.mkdir(parents=True, exist_ok=True)
    TREES_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("okf-viewer.js", "okf-viewer.css"):
        src = VIEWER_DIR / name
        if src.is_file():
            text = src.read_text(encoding="utf-8")
            (dest / name).write_text(text, encoding="utf-8")
            (TREES_DIR / name).write_text(text, encoding="utf-8")
    return dest


def stub_html(payload: dict) -> str:
    data = json.dumps(payload).replace("<", "\\u003c")
    repo_title = html.escape(str(payload.get("repo") or "repo"))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{repo_title} — code graph</title>
<link rel="stylesheet" href="okf-viewer.css">
</head><body>
<div id="banner">
  <h1 id="title">{repo_title}</h1>
  <div class="sum" id="sum"></div>
  <div class="meta">EXTRACTED graph · <span id="head"></span> ·
    <span class="dot" style="background:#38bdf8"></span>file
    <span class="dot" style="background:#a78bfa"></span>commit
    · click a node · not the old folder tree
  </div>
  <div><button class="on" id="bboth" onclick="setGraphMode('both')">Graph</button>
       <button id="bfile" onclick="setGraphMode('file')">Files</button>
       <button id="bcommit" onclick="setGraphMode('commit')">Commits</button></div>
  <div class="search">
    <input id="okfQ" placeholder="Search this repo — filename or keyword"/>
    <button type="button" id="okfQgo">Search</button>
    <span class="meta" id="okfQmsg"></span>
  </div>
</div>
<div id="row">
  <svg id="canvas" xmlns="http://www.w3.org/2000/svg"></svg>
  <div id="side"><div class="meta">Click a node for summary</div><pre id="out"></pre></div>
</div>
<script type="application/json" id="okf">{data}</script>
<script src="okf-viewer.js"></script>
</body></html>
"""


def extract_okf_payload(text: str) -> dict | None:
    m = OKF_JSON_RX.search(text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _hub_local(stem: str) -> str:
    hub = VAULT / "projects" / f"{stem}.md"
    try:
        text = hub.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r"(?im)^[\s\-*]*Local:\s*(.+)$", text)
    if not m:
        return ""
    p = pathlib.Path(m.group(1).strip().strip("`")).expanduser()
    return str(p.resolve()) if p.exists() else ""


def _find_clone(stem: str) -> str:
    hit = _hub_local(stem)
    if hit:
        return hit
    bases = [
        pathlib.Path.home() / "AntiGravity_Projects",
        pathlib.Path.home() / "projects",
        pathlib.Path.home(),
    ]
    needle = stem.lower()
    for base in bases:
        if not base.is_dir():
            continue
        try:
            for p in base.iterdir():
                if p.is_dir() and p.name.lower() == needle and (p / ".git").exists():
                    return str(p.resolve())
        except OSError:
            continue
        try:
            for p in base.glob("*/*"):
                if p.is_dir() and p.name.lower() == needle and (p / ".git").exists():
                    return str(p.resolve())
            for p in base.glob("*/*/*"):
                if p.is_dir() and p.name.lower() == needle and (p / ".git").exists():
                    return str(p.resolve())
        except OSError:
            continue
    return ""


def rebake_tree_htmls() -> int:
    """Rewrite every trees/*.html as a stub that loads the shared viewer.

    Keeps each repo's OKF JSON. Does not re-run git. One viewer update
    applies to Aryx, Rex, … the next time this function runs.
    """
    publish_viewer()
    trees = TREES_DIR
    if not trees.is_dir():
        return 0
    n = 0
    for path in trees.glob("*.html"):
        if not re.match(r"^[A-Za-z0-9._-]+$", path.stem):
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        payload = extract_okf_payload(raw)
        if not payload:
            continue
        payload["nodes"] = enrich_nodes(payload.get("nodes") or [])
        if not payload.get("repo"):
            payload["repo"] = path.stem
        root = str(payload.get("root") or "")
        if not root or not pathlib.Path(root).is_dir():
            payload["root"] = _find_clone(path.stem) or _find_clone(str(payload.get("repo") or ""))
        path.write_text(stub_html(payload), encoding="utf-8")
        n += 1
    return n


def render_html(open_after: bool = False) -> pathlib.Path:
    """Graphify-style node/edge canvas + repo summary. Not a folder tree.

    Rebuilds OKF when live HEAD ≠ baked okf.git_head so the panel tracks
    current checkout (not a stale history[0] commit).
    """
    live = live_git_head()
    tree = _load()
    if tree is None or head_drifted(tree):
        tree = build()
    okf = tree.get("okf") or build_okf(_flat_dict(tree))
    baked = str(okf.get("git_head") or "")
    summary = repo_summary()
    nodes_out = enrich_nodes(list(okf.get("nodes") or []))
    payload = {
        "nodes": nodes_out,
        "edges": okf.get("edges", []),
        "git_head": baked,
        "live_head": live or baked,
        "repo": tree.get("repo") or REPO.name,
        "root": str(REPO.resolve()),
        "summary": summary,
    }
    publish_viewer()
    page = stub_html(payload)
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(page)
    (TREE_PATH.with_name("code-xray.html")).write_text(page)
    try:
        man = json.loads((REPO / ".raven" / "manifest.json").read_text())
        raw = man.get("project")
        if isinstance(raw, dict):
            raw = raw.get("name") or raw.get("project") or ""
        pname = str(raw or "").strip()
        if re.match(r"^[A-Za-z0-9._-]+$", pname):
            (HTML_PATH.parent / f"{pname}.html").write_text(page)
    except Exception:
        pass
    if open_after:
        subprocess.Popen(["open", str(HTML_PATH)], start_new_session=True)
    return HTML_PATH


def _flat_dict(tree: dict) -> dict:
    flat: dict[str, dict] = {}
    _flatten(tree.get("root") or {}, flat)
    return flat



def _flat_items(tree: dict):
    flat: dict[str, dict] = {}
    _flatten(tree["root"], flat)
    return flat.items()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--delta", action="store_true")
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--files", nargs="*", default=None)
    ap.add_argument("--session", default=None)
    ap.add_argument("--commit", default=None)
    ap.add_argument("--for-prompt", default=None)
    ap.add_argument("--repo", default=None, help="build for another repo root (writes code-tree-<name>.html)")
    ap.add_argument("--node", default=None)
    ap.add_argument("--neighbors", default=None)
    ap.add_argument("--path-from", default=None)
    ap.add_argument("--path-to", default=None)
    ap.add_argument("--impact", default=None, help="commit SHA / short")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--query-type", default="", help="node type or edge type (touches, imports, …)")
    ap.add_argument("--if-stale", type=int, default=0, metavar="N", help="skip rebuild if git_head matches HEAD")
    args = ap.parse_args()

    if args.repo:
        global REPO, TREE_PATH, HTML_PATH
        REPO = pathlib.Path(args.repo).resolve()
        if not (REPO / ".git").exists():
            print(f"code-tree: {REPO} is not a git repo", file=sys.stderr)
            return
        TREE_PATH = REPO / ".raven" / "code-xray.json"
        HTML_PATH = TREES_DIR / f"{REPO.name}.html"

    if args.build:
        t = build(if_stale=args.if_stale)
        flat = dict(_flat_items(t))
        print(f"code-tree: built {len(flat)} nodes → {TREE_PATH}")
    query_commit = args.commit if (args.query_type or args.impact) else None
    if args.delta and not query_commit:
        n = delta(args.files or [], args.session, args.commit)
        print(f"code-tree: {'full rebuild (no tree existed)' if n < 0 else f'{n} node(s) patched'}")
    if args.digest:
        print(digest(args.for_prompt))
    if args.html:
        p = render_html(args.open)
        print(f"code-tree: HTML → {p}")
    okf = (_load() or {}).get("okf")
    if args.node or args.neighbors or args.path_from or args.impact or args.gaps or args.query_type:
        if not okf:
            t = _load() or build()
            okf = t.get("okf") or {}
        if args.query_type:
            print(json.dumps(
                query_graph(okf, type=args.query_type, commit=query_commit or args.impact or ""),
                indent=1,
            ))
        elif query_commit and not args.impact:
            print(json.dumps(commit_impact(okf, query_commit), indent=1))
        if args.node:
            print(json.dumps(get_node(okf, args.node), indent=1))
        if args.neighbors:
            print(json.dumps(get_neighbors(okf, args.neighbors), indent=1))
        if args.path_from and args.path_to:
            print(json.dumps(shortest_path(okf, args.path_from, args.path_to), indent=1))
        if args.impact:
            print(json.dumps(commit_impact(okf, args.impact), indent=1))
        if args.gaps:
            print(json.dumps(find_gaps(okf), indent=1))
    if not any([args.build, args.delta, args.digest, args.html, args.node, args.neighbors,
                args.path_from, args.impact, args.gaps, args.query_type]):
        ap.print_help()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"code-tree fail-soft: {e}", file=sys.stderr)
        sys.exit(0)
