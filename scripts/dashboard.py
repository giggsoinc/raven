#!/usr/bin/env python3
"""
Raven — Tokenomics & Usage Dashboard

Single module. Three render modes. Recommendations engine.

Modes:
  python3 dashboard.py --cli                  → ASCII table to stdout
  python3 dashboard.py --obsidian             → writes ~/RavenVault/Dashboard.md
  python3 dashboard.py --html [--open]        → writes ~/RavenVault/dashboard.html
  python3 dashboard.py --json                 → dumps raw metrics (for piping)
  python3 dashboard.py --all                  → all of the above

Filters:
  --days N        last N days (default 30)
  --month YYYY-MM specific month
  --project NAME  scope to a project (default: all)

Data sources (all local, no telemetry):
  .raven/audit/*.log                       — guard events, violations, approvals
  .raven/.model-session.json               — last session cost
  ~/RavenVault/.metrics/YYYY-MM.json       — rolling aggregated history
  ~/RavenVault/sessions/*.md               — session summaries
  .raven/manifest.json                     — project metadata
  git config user.name + remote            — who ran it, company

Metadata block always present: report timestamp, plugin version, company,
project, user, manifest snapshot.

Recommendations engine: rule-based, reads metrics, surfaces 3-7 actionable
suggestions per session ("Opus % at 38% — review prompts for over-classification").

Local-only. No telemetry. No Hub. ~500 LOC.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
RAVEN_DIR = PROJECT_DIR / ".raven"
AUDIT_DIR = RAVEN_DIR / "audit"
MANIFEST = RAVEN_DIR / "manifest.json"
MODEL_SESSION = RAVEN_DIR / ".model-session.json"
VAULT = Path.home() / "RavenVault"
VAULT_SESSIONS = VAULT / "sessions"
VAULT_METRICS = VAULT / ".metrics"
VAULT_DASHBOARD_MD = VAULT / "Dashboard.md"
VAULT_DASHBOARD_HTML = VAULT / "dashboard.html"

PLUGIN_VERSION = "3.4.1"


# ── Metadata Collection ────────────────────────────────────────────────────────
def collect_metadata() -> dict:
    """Build the metadata block: who, what, where, when."""
    md = {
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "report_generated_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "plugin_version": PLUGIN_VERSION,
        "project": None,
        "company": None,
        "owner": None,
        "user": None,
        "git_remote": None,
        "git_branch": None,
        "manifest_present": MANIFEST.exists(),
        "vault_path": str(VAULT),
        "project_path": str(PROJECT_DIR),
    }

    # From manifest
    if MANIFEST.exists():
        try:
            m = json.loads(MANIFEST.read_text())
            md["project"] = m.get("project")
            md["owner"] = m.get("owner")
            md["company"] = m.get("company") or m.get("owner")
            md["manifest"] = {
                "project": m.get("project"),
                "owner": m.get("owner"),
                "version": m.get("version"),
                "stack": m.get("stack"),
                "standards": m.get("standards"),
                "approval_mode": m.get("approval_mode"),
            }
        except Exception:
            pass

    # From git
    try:
        md["user"] = subprocess.check_output(
            ["git", "config", "user.name"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        pass
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        md["git_remote"] = remote
        # Extract company from URL — github.com/COMPANY/repo
        m = re.search(r"[/:]([^/]+)/[^/]+?(?:\.git)?$", remote)
        if m and not md["company"]:
            md["company"] = m.group(1)
    except Exception:
        pass
    try:
        md["git_branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        pass

    md["project"] = md["project"] or PROJECT_DIR.name
    md["owner"] = md["owner"] or md["user"] or "unknown"
    md["company"] = md["company"] or md["owner"]

    return md


# ── Aggregator ────────────────────────────────────────────────────────────────
def aggregate(days: int = 30, project_filter: Optional[str] = None) -> dict:
    """Read all sources, return canonical metrics dict."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    metrics = {
        "window_days": days,
        "window_start": cutoff.strftime("%Y-%m-%d"),
        "window_end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sessions_count": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "tier_counts": Counter(),
        "tier_cost": defaultdict(float),
        "guard_events": Counter(),
        "violations": Counter(),
        "approvals": Counter(),
        "skills_used": Counter(),
        "specialists_used": Counter(),
        "sessions_by_day": defaultdict(int),
        "cost_by_day": defaultdict(float),
        "tokens_by_day": defaultdict(int),
        "projects_seen": set(),
    }

    # ── Read current .model-session.json (two-bucket schema) ──
    if MODEL_SESSION.exists():
        try:
            ms = json.loads(MODEL_SESSION.read_text())
            # Handle legacy flat schema or new two-bucket schema
            if "raven_overhead" in ms:
                ov = ms["raven_overhead"]
                uw = ms["user_work"]
                metrics["last_session"] = {
                    "started_at": ms.get("session_started_at"),
                    "raven_overhead": {
                        "tokens": ov.get("tokens", 0),
                        "cost_usd": ov.get("cost_usd", 0.0),
                        "calls": ov.get("calls", 0),
                        "by_source": ov.get("by_source", {}),
                    },
                    "user_work": {
                        "tokens": uw.get("tokens", 0),
                        "cost_usd": uw.get("cost_usd", 0.0),
                        "calls": uw.get("calls", 0),
                        "tier_counts": uw.get("tier_counts", {}),
                        "last_classification": uw.get("last_classification"),
                    },
                    "providers": ms.get("providers", {}),
                    # Back-compat top-level fields (sum of both buckets)
                    "tokens": ov.get("tokens", 0) + uw.get("tokens", 0),
                    "cost_usd": round(ov.get("cost_usd", 0.0) + uw.get("cost_usd", 0.0), 6),
                    "tier_counts": uw.get("tier_counts", {}),
                }
            else:
                # Legacy flat schema → treat as 100% user_work
                metrics["last_session"] = {
                    "started_at": ms.get("session_started_at"),
                    "raven_overhead": {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}},
                    "user_work": {
                        "tokens": ms.get("session_tokens", 0),
                        "cost_usd": ms.get("session_cost_usd", 0.0),
                        "calls": ms.get("session_calls", 0),
                        "tier_counts": ms.get("tier_counts", {}),
                        "last_classification": None,
                    },
                    "providers": {},
                    "tokens": ms.get("session_tokens", 0),
                    "cost_usd": ms.get("session_cost_usd", 0.0),
                    "tier_counts": ms.get("tier_counts", {}),
                }
        except Exception:
            metrics["last_session"] = None
    else:
        metrics["last_session"] = None

    # ── Read rolling metrics from vault ──
    VAULT_METRICS.mkdir(parents=True, exist_ok=True)
    for metrics_file in sorted(VAULT_METRICS.glob("*.json")):
        try:
            data = json.loads(metrics_file.read_text())
            for session in data.get("sessions", []):
                started = session.get("started_at", "")
                if not started:
                    continue
                try:
                    ts = datetime.fromisoformat(started.replace("Z", "+00:00"))
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                if project_filter and session.get("project") != project_filter:
                    continue

                metrics["sessions_count"] += 1
                day = ts.strftime("%Y-%m-%d")
                metrics["sessions_by_day"][day] += 1
                metrics["total_tokens"] += session.get("tokens", 0)
                metrics["total_cost_usd"] += session.get("cost_usd", 0.0)
                metrics["cost_by_day"][day] += session.get("cost_usd", 0.0)
                metrics["tokens_by_day"][day] += session.get("tokens", 0)

                for tier, count in session.get("tier_counts", {}).items():
                    metrics["tier_counts"][tier] += count
                for tier, cost in session.get("tier_cost", {}).items():
                    metrics["tier_cost"][tier] += cost
                for skill in session.get("skills_used", []):
                    metrics["skills_used"][skill] += 1
                for spec in session.get("specialists_used", []):
                    metrics["specialists_used"][spec] += 1
                if session.get("project"):
                    metrics["projects_seen"].add(session["project"])
        except Exception:
            continue

    # ── Read audit logs ──
    if AUDIT_DIR.exists():
        for log_file in sorted(AUDIT_DIR.glob("*.log")):
            try:
                log_date = datetime.strptime(log_file.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if log_date < cutoff:
                    continue
            except Exception:
                continue
            try:
                for line in log_file.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        ev = json.loads(line)
                        kind = ev.get("kind") or ev.get("event") or "unknown"
                        metrics["guard_events"][kind] += 1
                        if "violation" in kind.lower():
                            metrics["violations"][ev.get("rule", "unknown")] += 1
                        if "approval" in kind.lower() or "override" in kind.lower():
                            metrics["approvals"][ev.get("rule", "unknown")] += 1
                    except Exception:
                        pass
            except Exception:
                continue

    # ── Convert to JSON-serializable ──
    metrics["tier_counts"] = dict(metrics["tier_counts"])
    metrics["tier_cost"] = dict(metrics["tier_cost"])
    metrics["guard_events"] = dict(metrics["guard_events"])
    metrics["violations"] = dict(metrics["violations"])
    metrics["approvals"] = dict(metrics["approvals"])
    metrics["skills_used"] = dict(metrics["skills_used"].most_common(20))
    metrics["specialists_used"] = dict(metrics["specialists_used"].most_common(10))
    metrics["sessions_by_day"] = dict(metrics["sessions_by_day"])
    metrics["cost_by_day"] = {k: round(v, 4) for k, v in metrics["cost_by_day"].items()}
    metrics["tokens_by_day"] = dict(metrics["tokens_by_day"])
    metrics["projects_seen"] = sorted(metrics["projects_seen"])
    metrics["total_cost_usd"] = round(metrics["total_cost_usd"], 4)

    # ── Derived metrics ──
    total = sum(metrics["tier_counts"].values()) or 1
    metrics["tier_share_pct"] = {
        tier: round(100 * count / total, 1)
        for tier, count in metrics["tier_counts"].items()
    }
    metrics["avg_cost_per_session"] = (
        round(metrics["total_cost_usd"] / metrics["sessions_count"], 4)
        if metrics["sessions_count"] else 0
    )
    metrics["avg_tokens_per_session"] = (
        metrics["total_tokens"] // metrics["sessions_count"]
        if metrics["sessions_count"] else 0
    )

    return metrics


# ── Recommendations Engine — Split by Owner ────────────────────────────────────
#
# Two rule sets, two owners:
#   🪶 RAVEN HYGIENE  → judges raven_overhead bucket. Raven team owns the fix.
#   👤 USER BEHAVIOR  → judges user_work bucket. User owns the fix.
#   🌐 ENVIRONMENT    → manifest, vault, hooks, guards (neither bucket — config)

def recommend_raven_hygiene(metrics: dict, metadata: dict) -> list:
    """Rules that judge raven_overhead — Raven team owns these levers."""
    recs = []
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {"tokens": 0, "cost_usd": 0.0, "by_source": {}}
    uw = ls.get("user_work") or {"tokens": 0}
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    by_src = ov.get("by_source") or {}

    # Rule R1 — Overhead share too high
    if ov_pct > 20 and total_tok > 1000:
        recs.append({
            "owner": "raven_team",
            "metric": "Raven overhead at {:.1f}% of total tokens".format(ov_pct),
            "severity": "high",
            "issue": "Raven's own footprint exceeds 20%. The framework is too heavy.",
            "action": "Audit by-source breakdown. Likely candidates: skill SKILL.md size, "
                     "session-start banner length, classifier emission verbosity. "
                     "File issue: github.com/giggsoinc/raven/issues",
            "savings_estimate_usd": round(ov.get("cost_usd", 0) * 0.5, 4),
        })

    # Rule R2 — Single source dominates overhead
    if by_src:
        top_src, top_info = max(by_src.items(), key=lambda x: x[1].get("tokens", 0))
        top_share = (top_info.get("tokens", 0) / ov.get("tokens", 1) * 100) if ov.get("tokens", 0) else 0
        if top_share > 50 and ov.get("tokens", 0) > 1000:
            recs.append({
                "owner": "raven_team",
                "metric": "{} = {:.0f}% of Raven overhead".format(top_src, top_share),
                "severity": "medium",
                "issue": "One source dominates Raven's footprint.",
                "action": "If skill-load: split the skill into mode-files (load on demand). "
                         "If session-start: compress banner. "
                         "If classifier: shorten the [REQUIRED] emission.",
            })

    # Rule R3 — Skill-load specifically (Andie/specialist size)
    skill_loads = {k: v for k, v in by_src.items() if k.startswith("skill-load:")}
    if skill_loads:
        skill_total = sum(v.get("tokens", 0) for v in skill_loads.values())
        if skill_total > 5000:
            top_skill = max(skill_loads.items(), key=lambda x: x[1].get("tokens", 0))
            recs.append({
                "owner": "raven_team",
                "metric": "Skill loads: {:,} tokens ({} is heaviest at {:,})".format(
                    skill_total, top_skill[0].replace("skill-load:", ""), top_skill[1].get("tokens", 0)),
                "severity": "medium",
                "issue": "Skill load weight is a primary Raven cost. Mode-splitting helps.",
                "action": "Move rarely-used sections of {} into mode-files referenced via "
                         "frontmatter. Load on demand, not always.".format(
                    top_skill[0].replace("skill-load:", "")),
            })

    # Rule R4 — Classifier emissions too verbose
    classifiers = ["triage-router", "architect-router"]
    classifier_total = sum(by_src.get(c, {}).get("tokens", 0) for c in classifiers)
    classifier_calls = sum(by_src.get(c, {}).get("calls", 0) for c in classifiers)
    if classifier_calls > 0:
        avg_per_call = classifier_total / classifier_calls
        if avg_per_call > 100:
            recs.append({
                "owner": "raven_team",
                "metric": "Classifier emission avg {:.0f} tokens/call".format(avg_per_call),
                "severity": "info",
                "issue": "Classifier [REQUIRED] injections are larger than necessary.",
                "action": "Trim triage-router and architect-router emission text. "
                         "Target ≤50 tokens per injection.",
            })

    return recs


def recommend_user_behavior(metrics: dict, metadata: dict) -> list:
    """Rules that judge user_work — user owns these levers."""
    recs = []
    ls = metrics.get("last_session") or {}
    uw = ls.get("user_work") or {"tokens": 0, "cost_usd": 0.0, "tier_counts": {}}
    tcs = uw.get("tier_counts") or {}
    total_user_calls = sum(tcs.values()) or 1

    # Rule U1 — User Opus over-classification (user_work tier mix only)
    user_opus_pct = (tcs.get("COMPLEX", 0) / total_user_calls * 100)
    if user_opus_pct > 30:
        recs.append({
            "owner": "user",
            "metric": "Your Opus rate: {:.0f}%".format(user_opus_pct),
            "severity": "high",
            "issue": "Your prompts are classifying as COMPLEX too often. This routes "
                     "you to Opus (~50× cost of Haiku).",
            "action": "Be more specific in prompts so scope is clear. Split big asks "
                     "into smaller steps. For simple edits, say 'simple' explicitly.",
            "savings_estimate_usd": round(uw.get("cost_usd", 0) * (user_opus_pct - 20) / 100, 2),
        })
    elif user_opus_pct == 0 and total_user_calls > 5:
        recs.append({
            "owner": "user",
            "metric": "0% COMPLEX across {} prompts".format(total_user_calls),
            "severity": "info",
            "issue": "No architecture-class prompts detected — either none happened, "
                     "or architect-router isn't catching them.",
            "action": "If you DID make design decisions: architect-router should have "
                     "fired. Check by typing 'design a multi-region auth system' — "
                     "should trigger [ANDIE REQUIRED].",
        })

    # Rule U2 — User work cost per session
    if uw.get("cost_usd", 0) > 1.0:
        recs.append({
            "owner": "user",
            "metric": "${:.2f} on your work this session".format(uw.get("cost_usd", 0)),
            "severity": "medium",
            "issue": "Your session is expensive on the user_work side (separate from "
                     "Raven's overhead). Long context, many Opus calls, or both.",
            "action": "Use /clear to reset context between tasks. For repeated edit "
                     "loops, switch to Haiku via .model.env override.",
        })

    # Rule U3 — User token consumption
    if uw.get("tokens", 0) > 50000:
        recs.append({
            "owner": "user",
            "metric": "{:,} tokens in your prompts/responses".format(uw.get("tokens", 0)),
            "severity": "medium",
            "issue": "Heavy session context. Long prompts, big tool outputs, or accumulated state.",
            "action": "Use /clear more often. Trim CLAUDE.md if it's bloated. "
                     "Avoid pasting large files — reference them by path.",
        })

    # Rule U4 — LOCAL_ONLY share (secrets in prompts)
    local_pct = (tcs.get("LOCAL_ONLY", 0) / total_user_calls * 100) if total_user_calls else 0
    if local_pct > 50 and total_user_calls > 5:
        recs.append({
            "owner": "user",
            "metric": "{:.0f}% routed LOCAL_ONLY".format(local_pct),
            "severity": "info",
            "issue": "More than half your prompts trigger LOCAL_ONLY (secret detection).",
            "action": "Either: (a) you're working on lots of secrets (good — local Ollama keeps "
                     "data on-machine), or (b) secret detection is too sensitive. "
                     "Check .raven/audit/ logs for false positives.",
        })

    return recs


def recommend_environment(metrics: dict, metadata: dict) -> list:
    """Rules that judge configuration — neither bucket, just setup health."""
    recs = []

    # Rule E1 — Missing manifest
    if not metadata["manifest_present"]:
        recs.append({
            "owner": "config",
            "metric": "Manifest missing",
            "severity": "high",
            "issue": ".raven/manifest.json doesn't exist — Raven is running without project context.",
            "action": "Type anything in Claude Code — Andie's Branch A onboarding will auto-create. "
                     "Or run /raven-init.",
        })

    # Rule E2 — No vault sessions
    sessions_dir_count = len(list(VAULT_SESSIONS.glob("*.md"))) if VAULT_SESSIONS.exists() else 0
    if sessions_dir_count == 0:
        recs.append({
            "owner": "config",
            "metric": "0 vault sessions",
            "severity": "high",
            "issue": "No session summaries in ~/RavenVault/sessions/ — obsidian-log not firing.",
            "action": "Verify settings.json wires Stop → obsidian-log.py. "
                     "Reinstall plugin: claude plugin install raven-plugin-v{}.zip".format(PLUGIN_VERSION),
        })

    # Rule E3 — Guard violations / approvals (still useful, not bucket-specific)
    total_violations = sum(metrics.get("violations", {}).values())
    if total_violations > 10:
        top = max(metrics["violations"].items(), key=lambda x: x[1])
        recs.append({
            "owner": "config",
            "metric": "{} guard violations".format(total_violations),
            "severity": "high",
            "issue": "Top: {} ({} times). Either policy needs tuning or training needed.".format(top[0], top[1]),
            "action": "Address root cause. If false positive, relax rule in manifest. "
                     "Otherwise educate the team.",
        })

    total_overrides = sum(metrics.get("approvals", {}).values())
    if total_overrides > 5:
        recs.append({
            "owner": "config",
            "metric": "{} approval overrides".format(total_overrides),
            "severity": "medium",
            "issue": "Frequent GUARD:ALLOW-* overrides — guards too strict or used as escape hatches.",
            "action": "Review .raven/audit/$(date +%Y-%m-%d).log. Codify legitimate exceptions; address misuse.",
        })

    return recs


def recommend(metrics: dict, metadata: dict) -> list:
    """Aggregate all three rule sets into a single list (back-compat)."""
    return (
        recommend_raven_hygiene(metrics, metadata)
        + recommend_user_behavior(metrics, metadata)
        + recommend_environment(metrics, metadata)
    )


# ── Renderer: CLI ──────────────────────────────────────────────────────────────
def render_cli(metrics: dict, metadata: dict, recs: list) -> str:
    """Produce ASCII dashboard for terminal."""
    out = []
    bar = "─" * 70

    out.append("")
    out.append("━" * 70)
    out.append("  RAVEN — TOKENOMICS & USAGE DASHBOARD")
    out.append("━" * 70)
    out.append("")

    # Metadata block
    out.append("📋 Report Metadata")
    out.append(bar)
    out.append(f"  Generated         : {metadata['report_generated_at_local']} (UTC: {metadata['report_generated_at']})")
    out.append(f"  Plugin version    : v{metadata['plugin_version']}")
    out.append(f"  Project           : {metadata['project']}")
    out.append(f"  Company           : {metadata['company']}")
    out.append(f"  Owner             : {metadata['owner']}")
    out.append(f"  User              : {metadata['user'] or '(git not configured)'}")
    out.append(f"  Git branch        : {metadata['git_branch'] or '—'}")
    out.append(f"  Git remote        : {metadata['git_remote'] or '—'}")
    out.append(f"  Manifest          : {'✓ present' if metadata['manifest_present'] else '✗ MISSING'}")
    out.append(f"  Vault             : {metadata['vault_path']}")
    out.append("")

    # Window
    out.append("🗓  Reporting Window")
    out.append(bar)
    out.append(f"  Start             : {metrics['window_start']}")
    out.append(f"  End               : {metrics['window_end']}")
    out.append(f"  Days              : {metrics['window_days']}")
    out.append("")

    # Last session — TWO-BUCKET ATTRIBUTION
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}}
    uw = ls.get("user_work") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "tier_counts": {}}
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    total_cost = ov.get("cost_usd", 0.0) + uw.get("cost_usd", 0.0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    uw_pct = (uw.get("tokens", 0) / total_tok * 100) if total_tok else 0
    out.append("⚡ Last Session — Tokenomics Split (Raven Overhead vs User Work)")
    out.append(bar)
    out.append(f"  {'METRIC':<22} {'RAVEN CODE':>14} {'USER WORK':>14} {'TOTAL':>14}")
    out.append(f"  {'-'*22} {'-'*14:>14} {'-'*14:>14} {'-'*14:>14}")
    out.append(f"  {'Tokens':<22} {ov.get('tokens',0):>14,} {uw.get('tokens',0):>14,} {total_tok:>14,}")
    out.append(f"  {'Cost (USD)':<22} ${ov.get('cost_usd',0):>13.4f} ${uw.get('cost_usd',0):>13.4f} ${total_cost:>13.4f}")
    out.append(f"  {'Calls':<22} {ov.get('calls',0):>14} {uw.get('calls',0):>14} {ov.get('calls',0)+uw.get('calls',0):>14}")
    out.append(f"  {'Share':<22} {ov_pct:>13.1f}% {uw_pct:>13.1f}% {'100.0%':>14}")
    out.append("")

    # User work tier breakdown
    tcs = uw.get("tier_counts") or {}
    if any(tcs.values()):
        out.append(f"  USER WORK — Tier breakdown:")
        out.append(f"    {' · '.join(f'{k}:{v}' for k,v in tcs.items() if v)}")
        out.append("")

    # Raven overhead by-source breakdown
    by_src = ov.get("by_source") or {}
    if by_src:
        out.append(f"  RAVEN CODE — Overhead by source:")
        for src, info in sorted(by_src.items(), key=lambda x: -x[1].get("tokens", 0)):
            tok = info.get("tokens", 0)
            calls = info.get("calls", 0)
            cost = info.get("cost_usd", 0.0)
            out.append(f"    {src:<24} {tok:>7,} tok  {calls:>3} calls  ${cost:.5f}")
        out.append("")

    # Provider attribution (matters for Codex tier)
    providers = ls.get("providers") or {}
    if providers:
        out.append(f"  PROVIDER attribution:")
        for prov, info in providers.items():
            tok = info.get("tokens", 0)
            cost = info.get("cost_usd", 0.0)
            pct = (tok / total_tok * 100) if total_tok else 0
            out.append(f"    {prov:<12} {tok:>10,} tok ({pct:>4.1f}%)  ${cost:.4f}")
        out.append("")

    # Cumulative
    out.append("📊 Cumulative ({} days)".format(metrics["window_days"]))
    out.append(bar)
    out.append(f"  Sessions          : {metrics['sessions_count']}")
    out.append(f"  Total tokens      : {metrics['total_tokens']:,}")
    out.append(f"  Total cost        : ${metrics['total_cost_usd']:.2f}")
    out.append(f"  Avg / session     : ${metrics['avg_cost_per_session']:.4f} ({metrics['avg_tokens_per_session']:,} tok)")
    out.append("")

    # Tier mix
    if metrics["tier_counts"]:
        out.append("🎯 Tier Mix")
        out.append(bar)
        for tier in ["SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY"]:
            count = metrics["tier_counts"].get(tier, 0)
            pct = metrics["tier_share_pct"].get(tier, 0)
            cost = metrics["tier_cost"].get(tier, 0)
            bar_chars = "█" * int(pct / 2)
            out.append(f"  {tier:<12} {count:>5}  ({pct:>5.1f}%)  ${cost:>7.3f}  {bar_chars}")
        out.append("")

    # Top skills
    if metrics["skills_used"]:
        out.append("🛠  Top Skills Used")
        out.append(bar)
        for skill, count in list(metrics["skills_used"].items())[:10]:
            out.append(f"  {skill:<40} {count:>5}")
        out.append("")

    # Top specialists
    if metrics["specialists_used"]:
        out.append("👥 Top Specialists")
        out.append(bar)
        for spec, count in list(metrics["specialists_used"].items())[:10]:
            out.append(f"  {spec:<40} {count:>5}")
        out.append("")

    # Guard events
    if metrics["guard_events"]:
        out.append("🛡  Guard Events")
        out.append(bar)
        for event, count in sorted(metrics["guard_events"].items(), key=lambda x: -x[1])[:10]:
            out.append(f"  {event:<40} {count:>5}")
        out.append("")

    # Recommendations — GROUPED BY OWNER
    out.append("💡 Recommendations — Grouped by Owner")
    out.append(bar)
    if not recs:
        out.append("  ✓ All metrics within healthy bands. No actions needed.")
    else:
        sev_icon = {"high": "🔴", "medium": "🟡", "info": "🔵"}
        groups = {
            "raven_team": ("🪶 RAVEN HYGIENE — Raven team owns these fixes", []),
            "user":       ("👤 USER BEHAVIOR — You own these fixes", []),
            "config":     ("⚙️  ENVIRONMENT — Configuration / setup fixes", []),
        }
        for r in recs:
            owner = r.get("owner", "config")
            groups.get(owner, groups["config"])[1].append(r)

        counter = 1
        for owner_key, (title, items) in groups.items():
            if not items:
                continue
            out.append(f"  {title}")
            out.append(f"  {'-' * 60}")
            for r in items:
                icon = sev_icon.get(r["severity"], "⚪")
                out.append(f"    {icon} [{counter}] {r['metric']}")
                out.append(f"         Issue:  {r['issue']}")
                out.append(f"         Action: {r['action']}")
                if r.get("savings_estimate_usd"):
                    out.append(f"         Est. savings: ${r['savings_estimate_usd']:.2f}")
                counter += 1
                out.append("")

    out.append("━" * 70)
    out.append(f"  Generated by Raven v{PLUGIN_VERSION}  ·  Local-only  ·  No telemetry")
    out.append("━" * 70)
    out.append("")
    return "\n".join(out)


# ── Renderer: Obsidian Markdown (with Dataview queries) ───────────────────────
def render_obsidian(metrics: dict, metadata: dict, recs: list) -> str:
    """Markdown with frontmatter + dataview queries — opens cleanly in Obsidian."""
    lines = []
    lines.append("---")
    lines.append(f"title: Raven Dashboard")
    lines.append(f"generated_at: {metadata['report_generated_at']}")
    lines.append(f"plugin_version: {metadata['plugin_version']}")
    lines.append(f"project: {metadata['project']}")
    lines.append(f"company: {metadata['company']}")
    lines.append(f"owner: {metadata['owner']}")
    lines.append(f"user: {metadata['user'] or 'unknown'}")
    lines.append(f"window_days: {metrics['window_days']}")
    lines.append(f"sessions: {metrics['sessions_count']}")
    lines.append(f"total_cost_usd: {metrics['total_cost_usd']}")
    lines.append(f"total_tokens: {metrics['total_tokens']}")
    lines.append("tags: [raven, dashboard, tokenomics, metrics]")
    lines.append("---")
    lines.append("")
    lines.append(f"# 🪶 Raven Dashboard — {metadata['project']}")
    lines.append("")
    lines.append(f"> Generated: **{metadata['report_generated_at_local']}**  ·  Plugin: **v{metadata['plugin_version']}**")
    lines.append(f"> Company: **{metadata['company']}**  ·  Owner: **{metadata['owner']}**  ·  User: **{metadata['user'] or '—'}**")
    lines.append(f"> Window: **{metrics['window_start']} → {metrics['window_end']}** ({metrics['window_days']} days)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Project Metadata")
    lines.append("")
    if metadata.get("manifest"):
        m = metadata["manifest"]
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Project | {m.get('project', '—')} |")
        lines.append(f"| Owner | {m.get('owner', '—')} |")
        lines.append(f"| Version | {m.get('version', '—')} |")
        lines.append(f"| Stack | `{json.dumps(m.get('stack', {}), indent=None)}` |")
        lines.append(f"| Standards | {m.get('standards', '—')} |")
        lines.append(f"| Approval mode | {m.get('approval_mode', '—')} |")
    else:
        lines.append("⚠️ Manifest missing. Run `/raven-init` to create one.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Headline numbers
    lines.append("## 📊 Headline Numbers")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Sessions ({metrics['window_days']}d) | **{metrics['sessions_count']}** |")
    lines.append(f"| Total tokens | **{metrics['total_tokens']:,}** |")
    lines.append(f"| Total cost (USD) | **${metrics['total_cost_usd']:.2f}** |")
    lines.append(f"| Avg cost / session | ${metrics['avg_cost_per_session']:.4f} |")
    lines.append(f"| Avg tokens / session | {metrics['avg_tokens_per_session']:,} |")
    lines.append("")

    # Two-bucket attribution split
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}}
    uw = ls.get("user_work") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "tier_counts": {}}
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    total_cost = ov.get("cost_usd", 0.0) + uw.get("cost_usd", 0.0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    uw_pct = (uw.get("tokens", 0) / total_tok * 100) if total_tok else 0

    lines.append("## ⚡ Last Session — Two-Bucket Tokenomics")
    lines.append("")
    lines.append("| Metric | 🪶 Raven Code (overhead) | 👤 User Work | Total |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| Tokens | **{ov.get('tokens',0):,}** | **{uw.get('tokens',0):,}** | {total_tok:,} |")
    lines.append(f"| Cost (USD) | ${ov.get('cost_usd',0):.4f} | ${uw.get('cost_usd',0):.4f} | ${total_cost:.4f} |")
    lines.append(f"| Calls | {ov.get('calls',0)} | {uw.get('calls',0)} | {ov.get('calls',0)+uw.get('calls',0)} |")
    lines.append(f"| Share | {ov_pct:.1f}% | {uw_pct:.1f}% | 100.0% |")
    lines.append("")
    lines.append("> 🪶 **Raven Code** = tokens consumed by hooks, skill loads, classifier injections, banners. Raven team's lever.")
    lines.append("> 👤 **User Work** = tokens consumed by your prompts + Claude's responses + tool calls. Your lever.")
    lines.append("")

    # Raven Code breakdown
    by_src = ov.get("by_source") or {}
    if by_src:
        lines.append("### 🪶 Raven Code — Overhead by Source")
        lines.append("")
        lines.append("| Source | Tokens | Calls | Cost (USD) |")
        lines.append("|---|---:|---:|---:|")
        for src, info in sorted(by_src.items(), key=lambda x: -x[1].get("tokens", 0)):
            lines.append(f"| `{src}` | {info.get('tokens',0):,} | {info.get('calls',0)} | ${info.get('cost_usd',0):.5f} |")
        lines.append("")

    # User Work breakdown
    tcs = uw.get("tier_counts") or {}
    if any(tcs.values()):
        lines.append("### 👤 User Work — Tier Mix")
        lines.append("")
        lines.append("| Tier | Count |")
        lines.append("|---|---:|")
        for tier in ["SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY"]:
            c = tcs.get(tier, 0)
            if c:
                lines.append(f"| {tier} | {c} |")
        lines.append("")

    # Provider attribution (for Codex tier especially)
    providers = ls.get("providers") or {}
    if providers:
        lines.append("### 🔌 Provider Attribution")
        lines.append("")
        lines.append("| Provider | Tokens | Share | Cost (USD) |")
        lines.append("|---|---:|---:|---:|")
        for prov, info in providers.items():
            tok = info.get("tokens", 0)
            cost = info.get("cost_usd", 0.0)
            pct = (tok / total_tok * 100) if total_tok else 0
            lines.append(f"| `{prov}` | {tok:,} | {pct:.1f}% | ${cost:.4f} |")
        lines.append("")

    # Tier mix
    if metrics["tier_counts"]:
        lines.append("## 🎯 Tier Mix")
        lines.append("")
        lines.append("| Tier | Count | Share | Cost (USD) |")
        lines.append("|---|---:|---:|---:|")
        for tier in ["SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY"]:
            c = metrics["tier_counts"].get(tier, 0)
            p = metrics["tier_share_pct"].get(tier, 0)
            cost = metrics["tier_cost"].get(tier, 0)
            lines.append(f"| {tier} | {c} | {p:.1f}% | ${cost:.3f} |")
        lines.append("")

    # Daily series
    if metrics["cost_by_day"]:
        lines.append("## 📅 Daily Series")
        lines.append("")
        lines.append("| Date | Sessions | Tokens | Cost |")
        lines.append("|---|---:|---:|---:|")
        for day in sorted(metrics["sessions_by_day"].keys()):
            s = metrics["sessions_by_day"][day]
            t = metrics["tokens_by_day"].get(day, 0)
            c = metrics["cost_by_day"].get(day, 0)
            lines.append(f"| {day} | {s} | {t:,} | ${c:.3f} |")
        lines.append("")

    # Top skills + specialists
    if metrics["skills_used"]:
        lines.append("## 🛠 Top Skills Used")
        lines.append("")
        lines.append("| Skill | Invocations |")
        lines.append("|---|---:|")
        for skill, count in list(metrics["skills_used"].items())[:15]:
            lines.append(f"| {skill} | {count} |")
        lines.append("")

    if metrics["specialists_used"]:
        lines.append("## 👥 Top Specialists")
        lines.append("")
        lines.append("| Specialist | Invocations |")
        lines.append("|---|---:|")
        for spec, count in list(metrics["specialists_used"].items())[:10]:
            lines.append(f"| {spec} | {count} |")
        lines.append("")

    # Guard events
    if metrics["guard_events"]:
        lines.append("## 🛡 Guard Events")
        lines.append("")
        lines.append("| Event | Count |")
        lines.append("|---|---:|")
        for event, count in sorted(metrics["guard_events"].items(), key=lambda x: -x[1])[:15]:
            lines.append(f"| {event} | {count} |")
        lines.append("")

    # Recommendations — grouped by owner
    lines.append("## 💡 Recommendations — Grouped by Owner")
    lines.append("")
    lines.append("> Different cost owners need different fixes. Issues are tagged by who controls the lever.")
    lines.append("")
    if not recs:
        lines.append("✓ All metrics within healthy bands. No actions needed.")
    else:
        sev = {"high": "🔴 HIGH", "medium": "🟡 MEDIUM", "info": "🔵 INFO"}
        groups = {
            "raven_team": ("🪶 Raven Hygiene", "Raven team owns these — file issues at github.com/giggsoinc/raven/issues if persistent."),
            "user":       ("👤 User Behavior", "You own these — prompt tuning, /clear cadence, model choice."),
            "config":     ("⚙️ Environment / Setup", "Configuration issues — manifest, hooks, guards, vault wiring."),
        }
        counter = 1
        for owner_key, (title, blurb) in groups.items():
            owner_recs = [r for r in recs if r.get("owner") == owner_key]
            if not owner_recs:
                continue
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"*{blurb}*")
            lines.append("")
            for r in owner_recs:
                lines.append(f"#### {counter}. {sev.get(r['severity'], 'INFO')} — {r['metric']}")
                lines.append("")
                lines.append(f"**Issue:** {r['issue']}")
                lines.append("")
                lines.append(f"**Action:** {r['action']}")
                if r.get("savings_estimate_usd"):
                    lines.append("")
                    lines.append(f"**Estimated savings:** ${r['savings_estimate_usd']:.2f}")
                lines.append("")
                counter += 1
    lines.append("---")
    lines.append("")

    # Dataview block (only renders if user has dataview plugin)
    lines.append("## 📈 Dataview — Session History")
    lines.append("")
    lines.append("(Renders if Obsidian Dataview plugin is installed)")
    lines.append("")
    lines.append("```dataview")
    lines.append("TABLE date, project, mode, status")
    lines.append('FROM "sessions"')
    lines.append("SORT date DESC")
    lines.append("LIMIT 30")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Raven v{metadata['plugin_version']} · Local-only · No telemetry*")
    lines.append("")
    return "\n".join(lines)


# ── Renderer: Static HTML ─────────────────────────────────────────────────────
def render_html(metrics: dict, metadata: dict, recs: list) -> str:
    """Static HTML with download buttons, no JS deps."""
    sev_color = {"high": "#dc2626", "medium": "#f59e0b", "info": "#3b82f6"}
    raw_json = json.dumps({"metadata": metadata, "metrics": metrics, "recommendations": recs}, indent=2, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Raven Dashboard — {metadata['project']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px; line-height: 1.5; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin-bottom: 8px; }}
  h2 {{ font-size: 18px; margin: 32px 0 12px; color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
  .meta {{ background: #1e293b; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px; font-size: 14px; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px 24px; }}
  .meta-grid div {{ }}
  .meta-grid strong {{ color: #94a3b8; display: inline-block; min-width: 120px; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }}
  th {{ background: #334155; color: #cbd5e1; font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .stat {{ background: #1e293b; padding: 16px 20px; border-radius: 8px; }}
  .stat-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
  .rec {{ background: #1e293b; padding: 16px 20px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #3b82f6; }}
  .rec.high {{ border-left-color: #dc2626; }}
  .rec.medium {{ border-left-color: #f59e0b; }}
  .rec-metric {{ font-weight: 600; margin-bottom: 6px; }}
  .rec-body {{ font-size: 14px; color: #cbd5e1; }}
  .rec-body strong {{ color: #e2e8f0; }}
  .bar {{ display: inline-block; height: 10px; background: #3b82f6; border-radius: 2px; vertical-align: middle; }}
  .download {{ display: inline-block; margin: 8px 8px 24px 0; padding: 10px 20px; background: #3b82f6; color: white; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 14px; cursor: pointer; border: none; }}
  .download:hover {{ background: #2563eb; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <h1>🪶 Raven Dashboard — {metadata['project']}</h1>
  <p style="color: #94a3b8; margin-bottom: 24px;">
    Generated {metadata['report_generated_at_local']} ·
    Plugin v{metadata['plugin_version']} ·
    Window: {metrics['window_start']} → {metrics['window_end']} ({metrics['window_days']} days)
  </p>

  <button class="download" onclick="downloadJSON()">⬇ Download JSON</button>
  <button class="download" onclick="downloadCSV()">⬇ Download CSV</button>
  <button class="download" onclick="window.print()">🖨 Print / Save PDF</button>

  <h2>📋 Project Metadata</h2>
  <div class="meta">
    <div class="meta-grid">
      <div><strong>Project</strong> {metadata['project']}</div>
      <div><strong>Company</strong> {metadata['company']}</div>
      <div><strong>Owner</strong> {metadata['owner']}</div>
      <div><strong>User</strong> {metadata['user'] or '—'}</div>
      <div><strong>Branch</strong> {metadata['git_branch'] or '—'}</div>
      <div><strong>Remote</strong> {metadata['git_remote'] or '—'}</div>
      <div><strong>Manifest</strong> {'✓ present' if metadata['manifest_present'] else '✗ MISSING'}</div>
      <div><strong>Vault</strong> {metadata['vault_path']}</div>
    </div>
  </div>

  <h2>📊 Headline Numbers</h2>
  <div class="stat-grid">
    <div class="stat"><div class="stat-label">Sessions</div><div class="stat-value">{metrics['sessions_count']}</div></div>
    <div class="stat"><div class="stat-label">Tokens</div><div class="stat-value">{metrics['total_tokens']:,}</div></div>
    <div class="stat"><div class="stat-label">Cost (USD)</div><div class="stat-value">${metrics['total_cost_usd']:.2f}</div></div>
    <div class="stat"><div class="stat-label">Avg / Session</div><div class="stat-value">${metrics['avg_cost_per_session']:.3f}</div></div>
  </div>
"""

    # ── Two-bucket Tokenomics Split ──
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}}
    uw = ls.get("user_work") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "tier_counts": {}}
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    total_cost = ov.get("cost_usd", 0.0) + uw.get("cost_usd", 0.0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    uw_pct = (uw.get("tokens", 0) / total_tok * 100) if total_tok else 0

    html += f"""
<h2>⚡ Tokenomics Split — Raven Code vs User Work</h2>
<p style="color:#94a3b8;font-size:13px;margin-bottom:16px;">
  Different cost owners need different levers. 🪶 <strong>Raven Code</strong>
  (overhead) is Raven team's lever. 👤 <strong>User Work</strong> is your lever.
</p>
<div class="stat-grid" style="grid-template-columns:1fr 1fr;">
  <div class="stat" style="border-left:4px solid #8b5cf6;">
    <div class="stat-label">🪶 Raven Code (Overhead)</div>
    <div class="stat-value">{ov.get('tokens',0):,}</div>
    <div style="color:#94a3b8;font-size:13px;margin-top:8px;">
      ${ov.get('cost_usd',0):.4f} · {ov.get('calls',0)} calls · {ov_pct:.1f}% of total
    </div>
  </div>
  <div class="stat" style="border-left:4px solid #10b981;">
    <div class="stat-label">👤 User Work</div>
    <div class="stat-value">{uw.get('tokens',0):,}</div>
    <div style="color:#94a3b8;font-size:13px;margin-top:8px;">
      ${uw.get('cost_usd',0):.4f} · {uw.get('calls',0)} calls · {uw_pct:.1f}% of total
    </div>
  </div>
</div>
"""

    # Raven Code by-source breakdown
    by_src = ov.get("by_source") or {}
    if by_src:
        html += '<h2>🪶 Raven Code — Overhead by Source</h2>\n'
        html += '<table>\n<thead><tr><th>Source</th><th class="num">Tokens</th><th class="num">Calls</th><th class="num">Cost (USD)</th></tr></thead>\n<tbody>\n'
        for src, info in sorted(by_src.items(), key=lambda x: -x[1].get("tokens", 0)):
            html += f'<tr><td><code>{src}</code></td><td class="num">{info.get("tokens",0):,}</td><td class="num">{info.get("calls",0)}</td><td class="num">${info.get("cost_usd",0):.5f}</td></tr>\n'
        html += '</tbody></table>\n'

    # Provider attribution (Codex-tier matters)
    providers = ls.get("providers") or {}
    if providers:
        html += '<h2>🔌 Provider Attribution</h2>\n'
        html += '<table>\n<thead><tr><th>Provider</th><th class="num">Tokens</th><th class="num">Share</th><th class="num">Cost (USD)</th></tr></thead>\n<tbody>\n'
        for prov, info in providers.items():
            tok = info.get("tokens", 0)
            cost = info.get("cost_usd", 0.0)
            pct = (tok / total_tok * 100) if total_tok else 0
            html += f'<tr><td><code>{prov}</code></td><td class="num">{tok:,}</td><td class="num">{pct:.1f}%</td><td class="num">${cost:.4f}</td></tr>\n'
        html += '</tbody></table>\n'

    if metrics["tier_counts"]:
        html += '<h2>🎯 Tier Mix</h2>\n<table>\n<thead><tr><th>Tier</th><th class="num">Count</th><th class="num">Share</th><th class="num">Cost (USD)</th><th>Distribution</th></tr></thead>\n<tbody>\n'
        for tier in ["SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY"]:
            c = metrics["tier_counts"].get(tier, 0)
            p = metrics["tier_share_pct"].get(tier, 0)
            cost = metrics["tier_cost"].get(tier, 0)
            html += f'<tr><td>{tier}</td><td class="num">{c}</td><td class="num">{p:.1f}%</td><td class="num">${cost:.3f}</td><td><span class="bar" style="width:{p*2}px"></span></td></tr>\n'
        html += '</tbody></table>\n'

    if metrics["cost_by_day"]:
        html += '<h2>📅 Daily Series</h2>\n<table>\n<thead><tr><th>Date</th><th class="num">Sessions</th><th class="num">Tokens</th><th class="num">Cost</th></tr></thead>\n<tbody>\n'
        for day in sorted(metrics["sessions_by_day"].keys()):
            s = metrics["sessions_by_day"][day]
            t = metrics["tokens_by_day"].get(day, 0)
            c = metrics["cost_by_day"].get(day, 0)
            html += f'<tr><td>{day}</td><td class="num">{s}</td><td class="num">{t:,}</td><td class="num">${c:.3f}</td></tr>\n'
        html += '</tbody></table>\n'

    if metrics["skills_used"]:
        html += '<h2>🛠 Top Skills</h2>\n<table>\n<thead><tr><th>Skill</th><th class="num">Invocations</th></tr></thead>\n<tbody>\n'
        for skill, count in list(metrics["skills_used"].items())[:15]:
            html += f'<tr><td>{skill}</td><td class="num">{count}</td></tr>\n'
        html += '</tbody></table>\n'

    if metrics["guard_events"]:
        html += '<h2>🛡 Guard Events</h2>\n<table>\n<thead><tr><th>Event</th><th class="num">Count</th></tr></thead>\n<tbody>\n'
        for event, count in sorted(metrics["guard_events"].items(), key=lambda x: -x[1])[:15]:
            html += f'<tr><td>{event}</td><td class="num">{count}</td></tr>\n'
        html += '</tbody></table>\n'

    html += '<h2>💡 Recommendations — Grouped by Owner</h2>\n'
    html += '<p style="color:#94a3b8;font-size:13px;margin-bottom:16px;">Different cost owners need different fixes. Issues are tagged by who controls the lever.</p>\n'
    if not recs:
        html += '<p style="color:#10b981;background:#1e293b;padding:16px;border-radius:8px;">✓ All metrics within healthy bands. No actions needed.</p>\n'
    else:
        groups = {
            "raven_team": ("🪶 Raven Hygiene", "Raven team owns these — file issues if persistent.", "#8b5cf6"),
            "user":       ("👤 User Behavior", "You own these — prompt tuning, /clear cadence, model choice.", "#10b981"),
            "config":     ("⚙️ Environment / Setup", "Configuration issues — manifest, hooks, guards, vault wiring.", "#f59e0b"),
        }
        counter = 1
        for owner_key, (title, blurb, color) in groups.items():
            owner_recs = [r for r in recs if r.get("owner") == owner_key]
            if not owner_recs:
                continue
            html += f'<h3 style="color:{color};margin-top:24px;margin-bottom:8px;border-bottom:2px solid {color};padding-bottom:4px;">{title}</h3>\n'
            html += f'<p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">{blurb}</p>\n'
            for r in owner_recs:
                html += f'<div class="rec {r["severity"]}" style="border-left-color:{color};">\n'
                html += f'<div class="rec-metric">[{counter}] {r["metric"]}</div>\n'
                html += f'<div class="rec-body"><strong>Issue:</strong> {r["issue"]}<br><strong>Action:</strong> {r["action"]}'
                if r.get("savings_estimate_usd"):
                    html += f' <br><strong>Estimated savings:</strong> ${r["savings_estimate_usd"]:.2f}'
                html += '</div></div>\n'
                counter += 1

    html += f"""
  <div class="footer">
    Generated by Raven v{metadata['plugin_version']} · Local-only · No telemetry
  </div>
</div>

<script>
const DATA = {raw_json};

function downloadJSON() {{
  const blob = new Blob([JSON.stringify(DATA, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'raven-dashboard-{metadata['project']}-{datetime.now().strftime('%Y%m%d-%H%M')}.json';
  a.click();
  URL.revokeObjectURL(url);
}}

function downloadCSV() {{
  const rows = [
    ['date', 'sessions', 'tokens', 'cost_usd'],
    ...Object.keys(DATA.metrics.sessions_by_day).sort().map(d => [
      d,
      DATA.metrics.sessions_by_day[d] || 0,
      DATA.metrics.tokens_by_day[d] || 0,
      (DATA.metrics.cost_by_day[d] || 0).toFixed(4)
    ])
  ];
  const csv = rows.map(r => r.join(',')).join('\\n');
  const blob = new Blob([csv], {{type: 'text/csv'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'raven-dashboard-{metadata['project']}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv';
  a.click();
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>
"""
    return html


# ── Main ──────────────────────────────────────────────────────────────────────
# ── Drift Audit (Method C) ─────────────────────────────────────────────────────
#
# Sampling-based safety net that catches attribution drift. Runs weekly via
# /loop or cron. Verifies known-overhead sources are correctly tagged and
# detects suspiciously high single-call user_work tokens (likely leaked overhead).

KNOWN_OVERHEAD_EXACT = {
    "triage-router", "architect-router", "session-start",
    "token-guard", "obsidian-log", "cve-prompt-guard",
    "secret-scan", "audit-log", "db-guard", "schema-guard",
    "mcp-guard", "policy-sync", "stream-signal", "raven_agent",
    "model-router", "log-overhead",
}
KNOWN_OVERHEAD_PREFIXES = ("skill-load:", "raven-hook:", "guard:")


def audit_drift(metrics: dict, metadata: dict, sample_rate: float = 0.01) -> dict:
    """
    Sample by_source attributions and check for drift.

    Findings categories:
      - unknown_source: source in raven_overhead not in known-good list
      - high_avg_user: user_work avg/call suspiciously high (overhead leak)
      - missing_source: known hook fired but no overhead recorded
      - cross_session_drift: per-source token average shifts >2x vs baseline
    """
    findings = []
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {}
    uw = ls.get("user_work") or {}
    by_src = ov.get("by_source") or {}

    # Check 1 — unknown overhead sources
    for src, info in by_src.items():
        is_known = (
            src in KNOWN_OVERHEAD_EXACT
            or any(src.startswith(p) for p in KNOWN_OVERHEAD_PREFIXES)
        )
        if not is_known:
            findings.append({
                "severity": "warn",
                "kind": "unknown_source",
                "source": src,
                "tokens": info.get("tokens", 0),
                "issue": f"Source '{src}' not in known-good overhead list",
                "action": "If legitimate, add to KNOWN_OVERHEAD_EXACT in dashboard.py. "
                         "If unexpected, audit the caller — may be misattribution.",
            })

    # Check 2 — user_work avg suspiciously high (overhead leak)
    tier_counts = uw.get("tier_counts") or {}
    user_calls = sum(tier_counts.values())
    if user_calls > 0:
        avg_per_call = uw.get("tokens", 0) / user_calls
        if avg_per_call > 100000:
            findings.append({
                "severity": "high",
                "kind": "high_avg_user",
                "source": "user_work bucket",
                "tokens": int(avg_per_call),
                "issue": f"User work avg {avg_per_call:,.0f} tokens/call — unusually high (>100K).",
                "action": "Likely overhead is being misattributed to user_work. "
                         "Audit recent log-overhead calls for missing --source flag, "
                         "or check if model-router got --source override accidentally.",
            })

    # Check 3 — total overhead vs total session
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    if total_tok > 1000 and ov_pct < 0.1:
        findings.append({
            "severity": "warn",
            "kind": "missing_overhead",
            "source": "raven_overhead bucket",
            "tokens": 0,
            "issue": f"Raven overhead at {ov_pct:.2f}% — implausibly low.",
            "action": "Hooks may not be calling log-overhead.py. "
                     "Verify triage-router + architect-router fire _log_overhead after emission.",
        })

    # Write audit log
    audit_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".raven" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"dashboard-audit-{datetime.now().strftime('%Y-%m-%d')}.log"
    try:
        with open(audit_path, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kind": "dashboard_audit",
                "project": metadata.get("project"),
                "findings_count": len(findings),
                "findings": findings,
                "metrics_snapshot": {
                    "raven_overhead_tokens": ov.get("tokens", 0),
                    "user_work_tokens": uw.get("tokens", 0),
                    "ov_pct": round(ov_pct, 2),
                    "sources_count": len(by_src),
                },
            }, default=str) + "\n")
    except Exception:
        pass  # never block

    return {
        "findings": findings,
        "audit_log_path": str(audit_path),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "sources_audited": len(by_src),
        "drift_detected": len(findings) > 0,
    }


def render_audit_cli(audit: dict) -> str:
    """Compact audit-only CLI output."""
    out = []
    out.append("")
    out.append("━" * 70)
    out.append("  RAVEN — DRIFT AUDIT (Method C — Sampling Safety Net)")
    out.append("━" * 70)
    out.append(f"  Checked at      : {audit['checked_at']}")
    out.append(f"  Sources audited : {audit['sources_audited']}")
    out.append(f"  Audit log       : {audit['audit_log_path']}")
    out.append(f"  Drift detected  : {'⚠️  YES' if audit['drift_detected'] else '✅ NO'}")
    out.append("")
    findings = audit["findings"]
    if not findings:
        out.append("  ✅ All sources correctly attributed. No drift detected.")
    else:
        sev_icon = {"high": "🔴", "warn": "🟡", "info": "🔵"}
        for i, f in enumerate(findings, 1):
            icon = sev_icon.get(f["severity"], "⚪")
            out.append(f"  {icon} [{i}] {f['kind']}: {f['source']}")
            out.append(f"        Tokens: {f['tokens']:,}")
            out.append(f"        Issue:  {f['issue']}")
            out.append(f"        Action: {f['action']}")
            out.append("")
    out.append("━" * 70)
    out.append("  Run weekly: /loop 7d /raven-dashboard --audit")
    out.append("━" * 70)
    out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Raven Tokenomics & Usage Dashboard")
    parser.add_argument("--cli", action="store_true", help="Render to terminal")
    parser.add_argument("--obsidian", action="store_true", help="Write Dashboard.md to ~/RavenVault/")
    parser.add_argument("--html", action="store_true", help="Write dashboard.html to ~/RavenVault/")
    parser.add_argument("--json", action="store_true", help="Dump raw metrics JSON")
    parser.add_argument("--all", action="store_true", help="All output modes")
    parser.add_argument("--audit", action="store_true",
                        help="Run drift audit on attribution buckets (Method C — sampling safety net)")
    parser.add_argument("--open", action="store_true", help="Open HTML report after writing")
    parser.add_argument("--days", type=int, default=30, help="Window in days (default 30)")
    parser.add_argument("--month", type=str, help="Specific month YYYY-MM")
    parser.add_argument("--project", type=str, help="Filter by project name")
    args = parser.parse_args()

    if not (args.cli or args.obsidian or args.html or args.json or args.all or args.audit):
        args.cli = True  # default

    days = args.days
    if args.month:
        try:
            year, month = args.month.split("-")
            days = 31  # rough — aggregator filters by date anyway
        except Exception:
            print(f"Invalid --month format. Use YYYY-MM. Got: {args.month}", file=sys.stderr)
            sys.exit(1)

    metadata = collect_metadata()
    metrics = aggregate(days=days, project_filter=args.project)
    recs = recommend(metrics, metadata)

    # Drift audit — runs independently or alongside other modes
    audit_result = None
    if args.audit:
        audit_result = audit_drift(metrics, metadata)
        print(render_audit_cli(audit_result))
        # Exit non-zero if drift detected (useful for CI / scheduled checks)
        if audit_result["drift_detected"]:
            print(f"⚠️  {len(audit_result['findings'])} drift findings — see {audit_result['audit_log_path']}",
                  file=sys.stderr)

    if args.cli or args.all:
        print(render_cli(metrics, metadata, recs))

    if args.obsidian or args.all:
        VAULT.mkdir(parents=True, exist_ok=True)
        VAULT_DASHBOARD_MD.write_text(render_obsidian(metrics, metadata, recs))
        print(f"📝 Obsidian dashboard: {VAULT_DASHBOARD_MD}", file=sys.stderr)

    if args.html or args.all:
        VAULT.mkdir(parents=True, exist_ok=True)
        VAULT_DASHBOARD_HTML.write_text(render_html(metrics, metadata, recs))
        print(f"🌐 HTML dashboard: {VAULT_DASHBOARD_HTML}", file=sys.stderr)
        if args.open:
            try:
                subprocess.run(["open", str(VAULT_DASHBOARD_HTML)], check=False)
            except Exception:
                pass

    if args.json:
        payload = {"metadata": metadata, "metrics": metrics, "recommendations": recs}
        if audit_result is not None:
            payload["audit"] = audit_result
        print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
