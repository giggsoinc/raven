#!/usr/bin/env python3
"""Build the Claude plugin directory edition of Raven into directory/raven/.

Instruction-only: Markdown skills/commands/agents + plugin.json + icon.
No hooks, scripts, local MCP servers, inline shell or allowed-tools.
Submit the folder directory/raven (not the repo root).
"""
import re, shutil, json, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "directory" / "raven"
VERSION = "6.1.4"

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)

def flat_desc(fm: str) -> str:
    m = re.search(r"^description:\s*(.*?)(?=^\S|\Z)", fm, re.S | re.M)
    if not m:
        return ""
    d = " ".join(m.group(1).split()).strip()
    if len(d) > 1 and d[0] == d[-1] and d[0] in "\"'":
        d = d[1:-1]
    return d

def q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def clean(text: str, kind: str, stem: str) -> str:
    text = text.replace("\r\n", "\n").replace("\x00", "")
    m = FM.match(text)
    body = text[m.end():] if m else text
    desc = flat_desc(m.group(1)) if m else ""
    nm = re.search(r"^name:\s*(\S+)", m.group(1), re.M) if m else None
    lines = ["---"]
    if kind == "skill":
        lines.append(f"name: {nm.group(1).strip(chr(34)+chr(39)) if nm else stem}")
    if desc:
        lines.append(f"description: {q(desc)}")
    lines.append("---")
    body = re.sub(r"^\s*!`.*?`\s*$",
                  "Read `.raven/manifest.json` if it exists (stack, libraries, mode) before continuing.",
                  body, flags=re.M)
    # multi-line !` blocks
    body = re.sub(r"^\s*!`[^`]*`\s*$", "Read `.raven/manifest.json` if it exists before continuing.", body, flags=re.M)
    body = re.sub(r"^(\s*)```(bash|sh|shell|zsh|powershell|ps1|console)\b.*$",
                  r"\1Commands for the user to review and run themselves:\n\1```text", body, flags=re.M)
    body = re.sub(r"curl\s+-\S+\s+https?://\S+", "the tool's official install instructions", body)
    body = re.sub(r"^allowed-tools:.*\n", "", body, flags=re.M)
    body = body.replace("npm i -g playwright && npx playwright install chromium",
                        "install Playwright following its official documentation")
    return "\n".join(lines) + "\n" + body.lstrip("\n")

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / ".claude-plugin").mkdir(parents=True)
    n = 0
    for kind, src in (("command", "commands"), ("agent", "agents")):
        for f in sorted((ROOT / src).glob("*.md")):
            dst = OUT / src / f.name
            dst.parent.mkdir(exist_ok=True)
            dst.write_text(clean(f.read_text(encoding="utf-8"), kind, f.stem), encoding="utf-8"); n += 1
    for sd in sorted((ROOT / "skills").iterdir()):
        if not (sd / "SKILL.md").exists():
            continue
        for f in sd.rglob("*.md"):
            dst = OUT / "skills" / sd.name / f.relative_to(sd)
            dst.parent.mkdir(parents=True, exist_ok=True)
            txt = f.read_text(encoding="utf-8")
            dst.write_text(clean(txt, "skill", sd.name) if f.name == "SKILL.md" else
                           clean(txt, "ref", f.stem).split("---\n", 2)[-1] if FM.match(txt) else clean(txt, "ref", f.stem).split("---\n", 2)[-1],
                           encoding="utf-8"); n += 1
    # icon: square 1024 PNG from banner, padded
    b = Image.open(ROOT / "assets" / "raven-banner.png").convert("RGB")
    bg = b.getpixel((2, 2)); s = max(b.size)
    sq = Image.new("RGB", (s, s), bg); sq.paste(b, ((s - b.width) // 2, (s - b.height) // 2))
    sq.resize((512, 512)).save(OUT / ".claude-plugin" / "icon.png", compress_level=6)
    pj = {
        "name": "raven-coder",
        "displayName": "Raven Coder",
        "version": VERSION,
        "description": "Discipline layer for AI coding: Andie plan-first orchestration, 61 specialist skills and slash commands for planning, debugging, security review and scaffolding. Instruction-only; runs nothing on your machine.",
        "author": {"name": "Giggso Inc.", "email": "rv@giggso.com", "url": "https://github.com/giggsoinc/raven"},
        "homepage": "https://github.com/giggsoinc/raven",
        "repository": "https://github.com/giggsoinc/raven",
        "license": "MIT",
        "keywords": ["security", "governance", "planning", "debugging", "specialists", "andie"],
        "icon": "./.claude-plugin/icon.png",
    }
    (OUT / ".claude-plugin" / "plugin.json").write_text(json.dumps(pj, indent=2) + "\n", encoding="utf-8")
    shutil.copy(ROOT / "LICENSE", OUT / "LICENSE")
    (OUT / "README.md").write_text(
        "# Raven Coder (directory edition)\n\nInstruction-only edition of Raven: skills, slash commands and agents "
        "(Markdown). It installs no hooks, scripts or local servers and sends no data anywhere.\n\n"
        "Install: `/plugin install raven-coder --marketplace giggsoinc/raven`\n\nSkills mention hook- and script-based enforcement; that lives in the full Raven install from "
        "https://github.com/giggsoinc/raven and is not part of this edition.\n\nLicense: MIT.\n",
        encoding="utf-8")
    print("files:", sum(1 for p in OUT.rglob("*") if p.is_file()), "md processed:", n)

main()
