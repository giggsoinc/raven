#!/usr/bin/env python3
"""
Raven — SessionStart Hook
Auto-discovers models, classifies project as brownfield or greenfield,
and injects context into the session before the user types anything.

Outputs JSON with additionalContext — consumed by Claude Code SessionStart hook.
Never prompts interactively. Never reads .env or credential files.
"""

import json, os, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

# ── Domain → Skill Map ────────────────────────────────────────────────────────
# Maps detected project domain to the Raven specialist skill to invoke.
# Order matters — first match wins.

DOMAIN_SKILL_MAP = [
    # Salesforce — unambiguous marker files
    {
        "name":    "Salesforce",
        "skill":   "raven:salesforce-specialist",
        "markers": ["sfdx-project.json", ".forceignore"],
        "dirs":    ["force-app"],
        "globs":   [],
    },
    # Odoo — __manifest__.py is the canonical Odoo module marker
    {
        "name":    "Odoo",
        "skill":   "raven:odoo-specialist",
        "markers": ["odoo.conf", ".odoo_upgrade.json"],
        "dirs":    [],
        "globs":   ["**/__manifest__.py"],  # checked with limit
    },
    # Terraform
    {
        "name":    "Terraform",
        "skill":   "raven:terraform-specialist",
        "markers": [],
        "dirs":    [],
        "globs":   ["*.tf", "**/*.tf"],
    },
    # Kubernetes / Helm
    {
        "name":    "Kubernetes",
        "skill":   "raven:k8s-specialist",
        "markers": [],
        "dirs":    ["k8s", "kubernetes", "helm", "charts"],
        "globs":   [],
    },
    # Kafka — check requirements or docker-compose
    {
        "name":    "Kafka",
        "skill":   "raven:kafka-specialist",
        "markers": [],
        "dirs":    [],
        "globs":   [],
        "keyword_files": ["requirements.txt", "docker-compose.yml", "pyproject.toml"],
        "keyword":       "kafka",
    },
    # Oracle — APEX / DB
    {
        "name":    "Oracle",
        "skill":   "raven:oracle-db-specialist",
        "markers": [],
        "dirs":    [],
        "globs":   ["**/*.pkb", "**/*.pks", "**/*.sql"],
        "keyword_files": ["requirements.txt"],
        "keyword":       "cx_Oracle",
    },
    # AWS / Cloud
    {
        "name":    "AWS",
        "skill":   "raven:aws-specialist",
        "markers": ["cdk.json", "serverless.yml", "serverless.yaml", "sam.yaml", "template.yaml"],
        "dirs":    [],
        "globs":   [],
    },
    # FastAPI / Python web
    {
        "name":    "FastAPI",
        "skill":   "raven:fastapi-specialist",
        "markers": [],
        "dirs":    [],
        "globs":   [],
        "keyword_files": ["requirements.txt", "pyproject.toml"],
        "keyword":       "fastapi",
    },
]


def detect_domain(cwd: Path) -> tuple[str | None, str | None]:
    """Detect the project's primary domain. Returns (skill, label) or (None, None)."""
    for entry in DOMAIN_SKILL_MAP:
        # Check marker files
        for marker in entry.get("markers", []):
            if (cwd / marker).exists():
                return entry["skill"], entry["name"]
        # Check marker directories
        for d in entry.get("dirs", []):
            if (cwd / d).is_dir():
                return entry["skill"], entry["name"]
        # Check glob patterns (with a hard limit to stay fast)
        for pattern in entry.get("globs", []):
            try:
                found = next(iter(cwd.glob(pattern)), None)
                if found:
                    return entry["skill"], entry["name"]
            except Exception:
                pass
        # Check keyword in specific files
        keyword = entry.get("keyword", "")
        if keyword:
            for kf in entry.get("keyword_files", []):
                kf_path = cwd / kf
                if kf_path.exists():
                    try:
                        if keyword.lower() in kf_path.read_text(errors="ignore").lower():
                            return entry["skill"], entry["name"]
                    except Exception:
                        pass
    return None, None


# ── Brownfield / Greenfield Detection ─────────────────────────────────────────

def detect_project_type() -> dict:
    signals = []
    project_type = "greenfield"
    confidence = "LOW"

    cwd = Path(".")

    # Git history depth
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        commit_count = int(result.stdout.strip()) if result.returncode == 0 else 0
        if commit_count > 50:
            signals.append(f"git: {commit_count} commits")
            project_type = "brownfield"
            confidence = "HIGH"
        elif commit_count > 5:
            signals.append(f"git: {commit_count} commits")
            project_type = "brownfield"
            confidence = "MEDIUM"
        elif commit_count > 0:
            signals.append(f"git: {commit_count} commits (new repo)")
    except Exception:
        signals.append("git: no repo detected")

    # Raven manifest
    if (cwd / ".raven" / "manifest.json").exists():
        signals.append("raven: manifest present")
        project_type = "brownfield"
        confidence = "HIGH"

    # Language / framework signals
    lang_signals = {
        "package.json":      "Node.js",
        "requirements.txt":  "Python",
        "pyproject.toml":    "Python",
        "Cargo.toml":        "Rust",
        "go.mod":            "Go",
        "pom.xml":           "Java/Maven",
        "build.gradle":      "Java/Gradle",
        "Gemfile":           "Ruby",
        "composer.json":     "PHP",
        "pubspec.yaml":      "Dart/Flutter",
    }
    detected_langs = []
    for file, lang in lang_signals.items():
        if (cwd / file).exists():
            detected_langs.append(lang)

    if detected_langs:
        signals.append(f"stack: {', '.join(detected_langs[:3])}")
        if project_type == "greenfield":
            project_type = "brownfield"
            confidence = "MEDIUM"

    # File count (rough proxy for existing codebase)
    try:
        src_extensions = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".cs"}
        src_files = [
            f for f in cwd.rglob("*")
            if f.suffix in src_extensions
            and ".git" not in f.parts
            and "node_modules" not in f.parts
            and "__pycache__" not in f.parts
        ]
        file_count = len(src_files)
        if file_count > 100:
            signals.append(f"codebase: {file_count} source files")
            project_type = "brownfield"
            confidence = "HIGH"
        elif file_count > 10:
            signals.append(f"codebase: {file_count} source files")
        elif file_count > 0:
            signals.append(f"codebase: {file_count} source file(s)")
    except Exception:
        pass

    # Infrastructure signals
    infra_signals = {
        "terraform": "Terraform",
        ".github/workflows": "GitHub Actions",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "kubernetes": "Kubernetes",
        "helm": "Helm",
    }
    detected_infra = []
    for path, label in infra_signals.items():
        if (cwd / path).exists():
            detected_infra.append(label)
    if detected_infra:
        signals.append(f"infra: {', '.join(detected_infra[:3])}")

    return {
        "type":       project_type,
        "confidence": confidence,
        "signals":    signals,
        "langs":      detected_langs,
    }


# ── Model Discovery ────────────────────────────────────────────────────────────

CLOUD_PROVIDERS = {
    "anthropic": {
        "env_keys": ["ANTHROPIC_API_KEY"],
        "models":   ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"],
        "tiers":    {"claude-haiku-4-5": "low", "claude-sonnet-4-5": "medium", "claude-opus-4-5": "high"},
    },
    "openai": {
        "env_keys": ["OPENAI_API_KEY"],
        "models":   ["gpt-4o-mini", "gpt-4o", "o3-mini"],
        "tiers":    {"gpt-4o-mini": "low", "gpt-4o": "medium", "o3-mini": "medium"},
    },
    "groq": {
        "env_keys": ["GROQ_API_KEY"],
        "models":   ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        "tiers":    {"llama-3.1-8b-instant": "low", "llama-3.3-70b-versatile": "low"},
    },
    "gemini": {
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "models":   ["gemini-2.0-flash", "gemini-1.5-pro"],
        "tiers":    {"gemini-2.0-flash": "low", "gemini-1.5-pro": "medium"},
    },
    "together": {
        "env_keys": ["TOGETHER_API_KEY"],
        "models":   ["meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
        "tiers":    {"meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": "low"},
    },
}

LOCAL_PROVIDERS = {
    "ollama":   "http://localhost:11434/api/tags",
    "lmstudio": "http://localhost:1234/v1/models",
}


def discover_cloud() -> list[dict]:
    found = []
    for name, cfg in CLOUD_PROVIDERS.items():
        key = next((os.environ.get(k) for k in cfg["env_keys"] if os.environ.get(k)), None)
        if key:
            found.append({
                "provider": name,
                "models":   cfg["models"],
                "tiers":    cfg["tiers"],
                "source":   "env",
            })
    return found


def discover_local() -> list[dict]:
    found = []
    for name, endpoint in LOCAL_PROVIDERS.items():
        try:
            req = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
            models = []
            if name == "ollama":
                models = [m["name"] for m in data.get("models", [])]
            elif name == "lmstudio":
                models = [m["id"] for m in data.get("data", [])]
            if models:
                found.append({
                    "provider": name,
                    "models":   models,
                    "tiers":    {m: "free" for m in models},
                    "source":   "local",
                })
        except Exception:
            pass
    return found


def build_routing(providers: list[dict]) -> dict:
    free    = [(p["provider"], m) for p in providers for m, t in p["tiers"].items() if t == "free"]
    low     = [(p["provider"], m) for p in providers for m, t in p["tiers"].items() if t == "low"]
    medium  = [(p["provider"], m) for p in providers for m, t in p["tiers"].items() if t == "medium"]
    high    = [(p["provider"], m) for p in providers for m, t in p["tiers"].items() if t == "high"]

    def pick(lst, fallback=None):
        return lst[0] if lst else fallback

    local_pick   = pick(free)
    simple_pick  = pick(low,    local_pick)
    medium_pick  = pick(medium, simple_pick)
    complex_pick = pick(high,   medium_pick)

    def fmt(t): return f"{t[0]}/{t[1]}" if t else "anthropic/claude-sonnet-4-5"

    return {
        "LOCAL_ONLY": fmt(local_pick),
        "SIMPLE":     fmt(simple_pick),
        "MEDIUM":     fmt(medium_pick),
        "COMPLEX":    fmt(complex_pick),
    }


def write_model_env(providers: list[dict], routing: dict):
    model_env = Path(".model.env")
    lines = [
        "# Raven — Model Capabilities",
        "# Auto-generated by session-start.py — safe to commit (no secrets)",
        "# Edit manually to override routing decisions",
        "",
        "[routing]",
        f"LOCAL_ONLY = {routing['LOCAL_ONLY']}",
        f"SIMPLE     = {routing['SIMPLE']}",
        f"MEDIUM     = {routing['MEDIUM']}",
        f"COMPLEX    = {routing['COMPLEX']}",
        "",
    ]
    for p in providers:
        lines.append(f"[{p['provider']}]")
        lines.append("available = true")
        lines.append(f"source    = {p['source']}")
        lines.append(f"models    = {', '.join(p['models'][:5])}")
        for model, tier in list(p["tiers"].items())[:5]:
            lines.append(f"tier.{model} = {tier}")
        lines.append("")

    model_env.write_text("\n".join(lines))

    # Ensure gitignored
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        if ".model.env" not in content:
            gitignore.write_text(content.rstrip() + "\n.model.env\n")


# ── Format output ──────────────────────────────────────────────────────────────

def format_context(project: dict, providers: list[dict], routing: dict, model_env_written: bool, domain_skill: tuple = (None, None)) -> str:
    lines = []

    # Project classification
    badge = "🟤 BROWNFIELD" if project["type"] == "brownfield" else "🟢 GREENFIELD"
    lines.append(f"{badge}  [{project['confidence']} confidence]")
    if project["signals"]:
        lines.append("  Signals: " + " · ".join(project["signals"]))

    lines.append("")

    # Model landscape
    if providers:
        local_p  = [p for p in providers if p["source"] == "local"]
        cloud_p  = [p for p in providers if p["source"] == "env"]

        if local_p:
            lines.append(f"⚡ LOCAL: " + ", ".join(
                f"{p['provider']} ({len(p['models'])} model{'s' if len(p['models'])!=1 else ''})"
                for p in local_p
            ))
        if cloud_p:
            lines.append(f"☁️  CLOUD: " + ", ".join(p["provider"] for p in cloud_p))

        lines.append("")
        lines.append("Model routing:")
        lines.append(f"  LOCAL_ONLY → {routing['LOCAL_ONLY']}")
        lines.append(f"  SIMPLE     → {routing['SIMPLE']}")
        lines.append(f"  MEDIUM     → {routing['MEDIUM']}")
        lines.append(f"  COMPLEX    → {routing['COMPLEX']}")

        if model_env_written:
            lines.append("  .model.env written ✓")

        # ── 💰 Cost meter — show prior session spend if available ──────────────
        try:
            session_file = Path(".raven/.model-session.json")
            if session_file.exists():
                session_data = json.loads(session_file.read_text())
                tok = session_data.get("session_tokens", 0)
                cost = session_data.get("session_cost_usd", 0.0)
                tier_breakdown = session_data.get("tier_counts", {})
                if tok > 0:
                    lines.append("")
                    lines.append(f"💰 Last session: ~{tok:,} tok · ~${cost:.3f}")
                    if tier_breakdown:
                        breakdown = " · ".join(f"{k}:{v}" for k, v in tier_breakdown.items() if v > 0)
                        lines.append(f"   Tiers used: {breakdown}")
        except Exception:
            pass  # Cost meter is best-effort, never blocks session start
    else:
        lines.append("☁️  No additional model providers detected.")
        lines.append("   Claude (current session) is your active model.")
        lines.append("   To add: set ANTHROPIC_API_KEY, GROQ_API_KEY, or start Ollama.")

    # ── 🔎 Transparency banner — make Raven VISIBLE (T4.4) ────────────────────
    # Fresh grads can't trust what they can't see. Show what's active, plainly.
    cwd = Path(".")
    has_manifest  = (cwd / ".raven" / "manifest.json").exists()
    has_claude_md = (cwd / ".claude" / "CLAUDE.md").exists() or (cwd / "CLAUDE.md").exists()
    try:
        lines.append("")
        lines.append("🔎 What's active right now:")
        lines.append("   🛡️  Guards: secret-scan + CVE check run at every commit (block on hit)")
        lines.append("   🧠  Helpers on call: /andie (plan) · /andie-jr (debug) — ask anytime")
        # memory status
        sessions_dir = Path.home() / "RavenVault" / "sessions"
        n_sessions = len(list(sessions_dir.glob("*.md"))) if sessions_dir.exists() else 0
        if n_sessions:
            lines.append(f"   💾  Memory: {n_sessions} prior session note(s) available for carry-forward")
        else:
            lines.append("   💾  Memory: will start logging session notes to ~/RavenVault/")
        lines.append("   (Nothing here is silent — guards announce themselves when they fire.)")
    except Exception:
        pass  # transparency banner is best-effort, never blocks session start

    # ── MANDATORY GREETING — fires for BOTH greenfield and brownfield ──────────
    # First message after install ALWAYS shows the Welcome greeting before any routing.
    # This is hook-enforced, not description-based. Claude cannot skip.
    lines.append("")
    lines.append("━━━ [GREETING REQUIRED] — MANDATORY FIRST RESPONSE ━━━")
    lines.append("On the FIRST user message of this session, Claude MUST respond")
    lines.append("with the EXACT greeting below — no other text, no analysis, no routing yet:")
    lines.append("")
    lines.append('    "Welcome to Raven — your Enterprise Discipline for AI-based Vibe Coding.')
    lines.append("")
    lines.append('     Do you want me to tell you what I can do, or just say — Let\'s Go!"')
    lines.append("")
    lines.append("After user responds:")
    lines.append("  ├─ If user asks 'what can you do' / curious / capabilities:")
    lines.append("  │     → Use PROGRESSIVE DISCLOSURE — do NOT dump all 61 skills.")
    lines.append("  │       Present three tiers, plain English:")
    lines.append("  │       • Always on:  secret + CVE guards at commit · cost-aware routing")
    lines.append("  │       • Just ask:   /andie (plan/design) · /andie-jr (debug a bug)")
    lines.append("  │       • Deep bench: 61 domain specialists load only when your work matches")
    lines.append("  │     → End with: 'Ready? Say Let\\'s Go.'")
    lines.append("  │")
    lines.append("  └─ If user says 'Let\\'s Go' / 'go' / states a task:")
    if not has_manifest:
        lines.append("       → AUTO-INVOKE `andie` skill — its Branch A onboarding fork fires:")
        lines.append("         Andie offers: 1) 2-min tour  2) just set me up  3) explain (Guru).")
        lines.append("         Then Setup Flow: brownfield self-discovers (≤2 Qs), greenfield")
        lines.append("         asks 5-7 Qs, proposes manifest, hands off to raven-init.")
        lines.append("         (Exact text lives in skills/andie/SKILL.md Branch A — follow it.)")
    else:
        lines.append("       → BROWNFIELD path: manifest.json ✅ present. Load it, trust stack.")
        lines.append("         Then route by prompt class:")
        lines.append("           [symptom]      → triage-router → andie-jr")
        lines.append("           [architecture] → architect-router → andie")
        skill, domain_label = domain_skill
        if skill:
            lines.append(f"           [domain task]  → {skill} ({domain_label})")
        else:
            lines.append("           [domain task]  → matching specialist (see manifest.stack)")
    lines.append("")
    lines.append("DO NOT skip the greeting. DO NOT route before greeting. DO NOT give")
    lines.append("install instructions — Raven IS installed.")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    # ── Brownfield-specific advisory (after greeting context) ─────────────────
    if project["type"] == "brownfield":
        lines.append("📋 Existing project — Raven IS installed and active.")
        if project["langs"]:
            lines.append(f"   Stack: {', '.join(project['langs'])}")
        skill, domain_label = domain_skill
        if skill:
            lines.append("")
            lines.append(f"⚡ DOMAIN DETECTED: {domain_label}")
            lines.append(f"   After greeting + Let's Go: invoke `{skill}` for domain tasks.")
    else:
        lines.append("🚀 New project — manifest will be created via Andie's Branch A on Let's Go.")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # SessionStart hook — read stdin (may be empty or contain session info)
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    # 1. Detect project type
    project = detect_project_type()

    # 2. Detect domain → skill mapping
    domain_skill = detect_domain(Path("."))

    # 3. Discover models
    local_providers = discover_local()
    cloud_providers = discover_cloud()
    all_providers   = local_providers + cloud_providers

    # 4. Build routing table
    routing = build_routing(all_providers)

    # 5. Write .model.env if missing or if local providers newly found
    model_env = Path(".model.env")
    model_env_written = False
    if not model_env.exists() and all_providers:
        try:
            write_model_env(all_providers, routing)
            model_env_written = True
        except Exception:
            pass  # Non-critical — session continues regardless

    # 6. Format context string
    context = format_context(project, all_providers, routing, model_env_written, domain_skill)

    # 6. Build compact system notification (always shown in Claude Code UI)
    badge_short = "BROWNFIELD" if project["type"] == "brownfield" else "GREENFIELD"
    skill, domain_label = domain_skill
    skill_line = f" · {domain_label} → {skill}" if skill else ""
    lang_short = ", ".join(project["langs"][:2]) if project["langs"] else ""
    stack_line = f" · {lang_short}" if lang_short else ""

    providers_short = ""
    local_p = [p for p in all_providers if p["source"] == "local"]
    cloud_p = [p for p in all_providers if p["source"] == "env"]
    if local_p:
        providers_short += " · " + ", ".join(f"{p['provider']}" for p in local_p)
    if cloud_p:
        providers_short += " · " + ", ".join(p["provider"] for p in cloud_p)

    system_message = f"Raven ✅  {badge_short}{stack_line}{skill_line}{providers_short}"

    # 7. Output JSON for SessionStart hook
    output = {
        "systemMessage": system_message,
        "hookSpecificOutput": {
            "hookEventName":   "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
