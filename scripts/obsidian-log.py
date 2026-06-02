#!/usr/bin/env python3
"""
obsidian-log.py v2 — Raven Stop hook
Three-layer session logging:
  A) AI summary via claude -p (if CLI available)
  B) Real content from session transcript (tool calls, files touched)
  C) Git state (recent commits, uncommitted changes)

Writes to ~/RavenVault/sessions/YYYY-MM-DD-<project>.md
Never reads secrets. Never transmits data. Local file write only.
"""
import os, sys, json, datetime, pathlib, subprocess
from collections import Counter

VAULT = pathlib.Path.home() / "RavenVault" / "sessions"
VAULT.mkdir(parents=True, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd, **kw):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                       text=True, **kw).strip()
    except:
        return ""

def get_project():
    remote = run(["git", "remote", "get-url", "origin"])
    if remote:
        return remote.rstrip("/").split("/")[-1].replace(".git", "")
    return pathlib.Path.cwd().name

# ── Read hook stdin ────────────────────────────────────────────────────────────

try:
    hook_input = json.load(sys.stdin)
except:
    hook_input = {}

session_id     = hook_input.get("session_id", "")
transcript_path = hook_input.get("transcript_path", "")

# Fallback: find transcript by session_id in ~/.claude/projects/
if not transcript_path and session_id:
    for p in pathlib.Path.home().glob(f".claude/projects/**/{session_id}.jsonl"):
        transcript_path = str(p)
        break

# ── Option B: Parse transcript for real content ────────────────────────────────

files_written  = []
files_read     = []
bash_cmds      = []
tool_counts    = Counter()
skills_used    = []

if transcript_path and pathlib.Path(transcript_path).exists():
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    msg = entry.get("message", {})
                    if not isinstance(msg, dict): continue
                    if msg.get("role") != "assistant": continue
                    for block in (msg.get("content") or []):
                        if not isinstance(block, dict): continue
                        if block.get("type") != "tool_use": continue
                        name = block.get("name", "")
                        inp  = block.get("input", {})
                        tool_counts[name] += 1
                        if name in ("Write", "Edit", "MultiEdit"):
                            fp = inp.get("file_path", "")
                            if fp and fp not in files_written:
                                files_written.append(fp)
                        elif name == "Read":
                            fp = inp.get("file_path", "")
                            if fp and fp not in files_read:
                                files_read.append(fp)
                        elif name == "Bash":
                            cmd = inp.get("command", "")[:80]
                            if cmd: bash_cmds.append(cmd)
                        elif name == "Skill":
                            sk = inp.get("skill", "")
                            if sk and sk not in skills_used:
                                skills_used.append(sk)
                except:
                    pass
    except:
        pass

# Keep only meaningful files (not temp, not .git internals)
def clean_files(lst):
    return [f for f in lst if f and not any(x in f for x in [".git/", "/tmp/", "__pycache__"])]

files_written = clean_files(files_written)[:20]
files_read    = clean_files(files_read)[:10]

# ── Option C: Git state ────────────────────────────────────────────────────────

git_log = run(["git", "log", "--oneline", "-7"])
git_status = run(["git", "status", "--short"])
git_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
git_diff_stat = run(["git", "diff", "--stat", "HEAD"])

# ── Option A: AI summary via claude CLI ───────────────────────────────────────

ai_summary = ""

context_for_ai = f"""Session context for summarisation:
Project: {get_project()}
Branch: {git_branch}

Recent commits:
{git_log or '(none)'}

Files written/edited this session:
{chr(10).join(f'  - {f}' for f in files_written[:10]) or '  (none detected)'}

Tool calls made:
{chr(10).join(f'  - {k}: {v}' for k, v in tool_counts.most_common(8))}

Skills activated:
{', '.join(skills_used) or '(none)'}
"""

try:
    result = subprocess.run(
        ["claude", "-p",
         f"In 3-5 crisp bullets (≤15 words each), summarise what was accomplished in this coding session. No preamble. Just bullets starting with •.\n\n{context_for_ai}"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0 and result.stdout.strip():
        ai_summary = result.stdout.strip()
except:
    pass

# ── Build Obsidian entry ───────────────────────────────────────────────────────

project   = get_project()
date      = datetime.date.today().isoformat()
timestamp = datetime.datetime.now().strftime("%H:%M")
note_path = VAULT / f"{date}-{project}.md"

# Tool stats line
total_tools = sum(tool_counts.values())
top_tools   = ", ".join(f"{k}×{v}" for k, v in tool_counts.most_common(5))

entry_parts = [f"\n---\n## Session Entry — {timestamp}\n",
               f"**Project:** {project}  ",
               f"**Branch:** {git_branch or 'unknown'}  ",
               f"**CWD:** {os.getcwd()}  ",
               f"**Tools used:** {total_tools} ({top_tools})\n"]

# A — AI summary
if ai_summary:
    entry_parts.append("### AI Summary")
    entry_parts.append(ai_summary)
    entry_parts.append("")

# B — Files touched
if files_written:
    entry_parts.append("### Files Written / Edited")
    for f in files_written:
        entry_parts.append(f"- `{f}`")
    entry_parts.append("")

if skills_used:
    entry_parts.append("### Skills Activated")
    entry_parts.append(", ".join(f"`{s}`" for s in skills_used))
    entry_parts.append("")

# C — Git state
if git_log:
    entry_parts.append("### Recent Commits")
    for line in git_log.splitlines():
        entry_parts.append(f"- `{line}`")
    entry_parts.append("")

if git_status:
    entry_parts.append("### Uncommitted Changes")
    entry_parts.append(f"```\n{git_status}\n```")
    entry_parts.append("")

entry = "\n".join(entry_parts) + "\n"

# ── Write to vault ─────────────────────────────────────────────────────────────

if not note_path.exists():
    note_path.write_text(f"# Session — {date} — {project}\n\n[[projects/{project}]]\n")

with open(note_path, "a") as f:
    f.write(entry)

# Update index last-session pointer
index_path = pathlib.Path.home() / "RavenVault" / "index" / "README.md"
if index_path.exists():
    content = index_path.read_text()
    marker  = "## Last Session"
    if marker in content:
        before, after = content.split(marker, 1)
        rest = after.split("\n\n", 1)[-1] if "\n\n" in after else ""
        index_path.write_text(
            f"{before}{marker}\n[[sessions/{date}-{project}]] — {timestamp}\n\n{rest}"
        )

print(f"✅ Session logged → RavenVault/sessions/{date}-{project}.md")
if ai_summary:
    print("   ✅ AI summary included (Option A)")
if files_written:
    print(f"   ✅ {len(files_written)} files tracked from transcript (Option B)")
if git_log:
    print(f"   ✅ Git state captured (Option C)")
