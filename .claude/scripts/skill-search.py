#!/usr/bin/env python3
# Raven — Skill Search + Approval v1.0
# Sources: anthropics/skills (GitHub) + GitHub search
# Usage: skill-search.py --query "pdf" | --install "anthropics/skills/pdf" | --list

import argparse, json, sys, os, subprocess, shutil, urllib.request, urllib.parse

MANIFEST   = ".raven/manifest.json"
SKILLS_DIR = ".claude/skills"
G,Y,R,B,W,N = '\033[0;32m','\033[1;33m','\033[0;31m','\033[0;34m','\033[1m','\033[0m'

def load_manifest():
    try:
        return json.load(open(MANIFEST))
    except:
        return {}

def save_manifest(m):
    json.dump(m, open(MANIFEST,'w'), indent=2)

def gh_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"raven/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read()

def search(query):
    # Anthropic official
    official = [
        ("docx","anthropics/skills/docx","Word documents",117000),
        ("pdf","anthropics/skills/pdf","PDF toolkit",117000),
        ("pptx","anthropics/skills/pptx","PowerPoint",117000),
        ("xlsx","anthropics/skills/xlsx","Excel",117000),
        ("frontend-design","anthropics/skills/frontend-design","Production UI",117000),
        ("mcp-builder","anthropics/skills/mcp-builder","Build MCP servers",117000),
        ("webapp-testing","anthropics/skills/webapp-testing","Playwright testing",117000),
    ]
    results = [(n,fn,d,s,"anthropic") for n,fn,d,s in official
               if query.lower() in n or query.lower() in d.lower()]

    # GitHub search
    try:
        q = urllib.parse.quote(f"{query} SKILL.md filename:SKILL.md")
        data = json.loads(gh_fetch(
            f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=8"
        ))
        for i in data.get("items",[]):
            results.append((i["name"],i["full_name"],
                           (i.get("description") or "")[:50],
                           i["stargazers_count"],"github"))
    except:
        pass
    return results[:10]

def fetch_skill_md(full_name, source):
    try:
        if source == "anthropic":
            name = full_name.split("/")[-1]
            url = f"https://raw.githubusercontent.com/anthropics/skills/main/skills/{name}/SKILL.md"
        else:
            url = f"https://raw.githubusercontent.com/{full_name}/main/SKILL.md"
        return gh_fetch(url).decode()
    except:
        return ""

def audit(content):
    blocked, warns = False, []
    for pat,msg in [
        ("manifest.secrets","Reads secrets file"),
        (".env","Reads .env"),
        ("id_rsa","Reads SSH key"),
        ("ignore CLAUDE","Overrides CLAUDE.md"),
        ("ignore your rules","Overrides rules"),
    ]:
        if pat.lower() in content.lower():
            warns.append(f"❌ BLOCKED: {msg}"); blocked=True
    for pat,msg in [
        ("allowed-tools: Write","Requests Write access"),
        ("allowed-tools: Bash","Requests Bash access"),
        ("curl ","Network call"),
        ("wget ","Network call"),
    ]:
        if pat.lower() in content.lower():
            warns.append(f"⚠️  WARN: {msg}")
    return blocked, warns

def install(full_name, name, source):
    dest = os.path.join(SKILLS_DIR, name)
    os.makedirs(dest, exist_ok=True)
    content = fetch_skill_md(full_name, source)
    if content:
        open(os.path.join(dest,"SKILL.md"),'w').write(content)
        print(f"{G}✅ Installed → {dest}{N}")
    elif shutil.which("git"):
        subprocess.run(["git","clone","--depth=1",
                        f"https://github.com/{full_name}",dest],
                       check=True, capture_output=True)
        print(f"{G}✅ Cloned → {dest}{N}")
    else:
        print(f"{R}❌ Could not install — add manually{N}"); sys.exit(1)

def approve(name, source):
    m = load_manifest()
    bucket = "anthropic" if source=="anthropic" else "community"
    approved = m.setdefault("approved_skills",{})
    lst = approved.setdefault(bucket,[])
    if name not in lst:
        lst.append(name)
        save_manifest(m)
        print(f"{G}✅ {name} added to manifest.approved_skills.{bucket}{N}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query")
    p.add_argument("--install")
    p.add_argument("--list", action="store_true")
    args = p.parse_args()

    if args.list:
        m = load_manifest()
        for src,skills in m.get("approved_skills",{}).items():
            if isinstance(skills,list) and skills:
                print(f"\n{B}{src}:{N}")
                [print(f"  ✅ {s}") for s in skills]
        return

    if args.query:
        results = search(args.query)
        if not results:
            print(f"{Y}No results for '{args.query}'{N}"); return
        print(f"\n{'#':<3}{'Source':<12}{'Name':<26}{'Stars':<9}Description")
        print("─"*75)
        for i,(n,fn,d,s,src) in enumerate(results,1):
            print(f"{i:<3}{src:<12}{n:<26}★{s:<8,}{d[:30]}")
        print(f"\n{B}Install: python3 .claude/scripts/skill-search.py --install <full_name>{N}\n")
        return

    if args.install:
        fn = args.install
        name = fn.split("/")[-1]
        src = "anthropic" if "anthropics" in fn else "community"

        print(f"\n{W}Fetching + auditing: {fn}{N}\n")
        content = fetch_skill_md(fn, src)
        if not content:
            print(f"{R}❌ Could not fetch SKILL.md{N}"); sys.exit(1)

        blocked, warns = audit(content)
        [print(f"  {w}") for w in warns] if warns else print(f"  {G}✅ No issues{N}")

        print(f"\n{W}Preview (first 15 lines):{N}")
        [print(f"  {l}") for l in content.splitlines()[:15]]

        if blocked:
            print(f"\n{R}❌ BLOCKED — security audit failed. Not installed.{N}"); sys.exit(1)

        print(f"\n{Y}Approve install of '{name}' from {fn}? (yes/no):{N} ", end="")
        if input().strip().lower() != "yes":
            print(f"{Y}Cancelled.{N}"); return

        install(fn, name, src)
        approve(name, src)
        print(f"\n{G}Restart Claude Code to load '{name}'.{N}\n")

if __name__ == "__main__":
    main()
