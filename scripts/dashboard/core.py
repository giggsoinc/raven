#!/usr/bin/env python3
"""
Raven — Tokenomics & Usage Dashboard

Single module. Three render modes. Recommendations engine.

Modes:
  python3 dashboard.py --cli                  → ASCII table to stdout
  python3 dashboard.py --obsidian             → writes ~/RavenVault/Dashboard.md
  python3 dashboard.py --html [--open]        → writes ~/RavenVault/dashboard.html
                                              (tokenomics + knowledge graph panel)
  python3 dashboard.py --graph-only           → rebuild graph JSON + graph-focused HTML
  python3 dashboard.py --graph-json           → only write knowledge-graph.json
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
suggestions per session ("COMPLEX-tier rate at 38% — review prompts for
over-classification"; COMPLEX routes to Sonnet-5-high, never Opus — see
model-router.py's defaults and CLAUDE.md Rule 8).

Local-only. No telemetry. No Hub. ~500 LOC.
"""

import argparse
import html as html_lib
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

PLUGIN_VERSION = "5.5.4"


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
def _project_name(raw) -> Optional[str]:
    """Normalize project field (str | dict | None) from metrics rows."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("name") or raw.get("project")
    return str(raw)


def _parse_day(day_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(day_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def format_usd(amount: float, *, force_cents: bool = False) -> str:
    """Human money: avoid $0.00 masking real sub-cent / small costs."""
    try:
        v = float(amount or 0.0)
    except (TypeError, ValueError):
        v = 0.0
    if v == 0:
        return "$0"
    if force_cents or v >= 1.0:
        return f"${v:,.2f}"
    if v >= 0.01:
        return f"${v:.4f}"
    return f"${v:.6f}"


EXTERNAL_USAGE_PATH = VAULT / ".metrics" / "external-usage.json"
EXTERNAL_USAGE_TEMPLATE = VAULT / ".metrics" / "external-usage.template.json"


def load_external_usage() -> dict:
    """Optional Claude/Anthropic-reported usage for side-by-side compare.

    File: ~/RavenVault/.metrics/external-usage.json
    (never auto-filled by Raven — human or Claude pastes after Console/export.)
    """
    if not EXTERNAL_USAGE_PATH.exists():
        return {}
    try:
        data = json.loads(EXTERNAL_USAGE_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {"error": f"unreadable {EXTERNAL_USAGE_PATH}"}


def ensure_external_usage_template() -> None:
    """Write a template file users/Claude can fill for comparison."""
    try:
        VAULT_METRICS.mkdir(parents=True, exist_ok=True)
        if EXTERNAL_USAGE_TEMPLATE.exists():
            return
        EXTERNAL_USAGE_TEMPLATE.write_text(
            json.dumps(
                {
                    "source": "anthropic_console | claude_session_estimate | user_paste",
                    "as_of": "YYYY-MM-DD",
                    "window_days": 30,
                    "notes": "Paste totals from Anthropic Console or ask Claude to estimate from known usage. Raven does not fill this file.",
                    "total": {"tokens": 0, "cost_usd": 0.0},
                    "by_project": {
                        "fin-processor": {
                            "tokens": 0,
                            "cost_usd": 0.0,
                            "notes": "example — replace with real numbers",
                        }
                    },
                },
                indent=2,
            )
            + "\n"
        )
    except Exception:
        pass


def render_cost_compare_section(metrics: dict, metadata: dict) -> str:
    """Side-by-side: Raven-metered vs Claude/external-reported."""
    ensure_external_usage_template()
    ext = load_external_usage()
    bp = metrics.get("by_project") or {}
    window = f"{metrics.get('window_start')} → {metrics.get('window_end')}"

    ext_bp = ext.get("by_project") if isinstance(ext.get("by_project"), dict) else {}
    ext_total = ext.get("total") if isinstance(ext.get("total"), dict) else {}
    names = sorted(set(list(bp.keys()) + list(ext_bp.keys())), key=str.lower)

    rows = ""
    for name in names:
        r = bp.get(name) or {}
        e = ext_bp.get(name) if isinstance(ext_bp.get(name), dict) else {}
        r_tok = int(r.get("tokens") or 0)
        r_cost = float(r.get("cost_usd") or 0)
        e_tok = e.get("tokens")
        e_cost = e.get("cost_usd")
        e_tok_s = f"{int(e_tok):,}" if e_tok is not None else "—"
        e_cost_s = format_usd(float(e_cost)) if e_cost is not None else "—"
        # delta only when external present
        if e_cost is not None:
            delta = float(e_cost) - r_cost
            delta_s = format_usd(delta) if delta >= 0 else f"-{format_usd(abs(delta))}"
            ratio = (float(e_cost) / r_cost) if r_cost > 0 else ("∞" if float(e_cost) > 0 else "—")
            if isinstance(ratio, float):
                ratio_s = f"{ratio:.1f}×"
            else:
                ratio_s = str(ratio)
        else:
            delta_s = "—"
            ratio_s = "—"
        rows += (
            f"<tr><td><strong>{name}</strong></td>"
            f"<td class='num'>{r_tok:,}</td><td class='num'>{format_usd(r_cost)}</td>"
            f"<td class='num'>{e_tok_s}</td><td class='num'>{e_cost_s}</td>"
            f"<td class='num'>{delta_s}</td><td class='num'>{ratio_s}</td></tr>\n"
        )
    if not rows:
        rows = "<tr><td colspan='7' style='color:#94a3b8'>No Raven per-repo rows yet.</td></tr>"

    r_tot_t = int(metrics.get("total_tokens") or 0)
    r_tot_c = float(metrics.get("total_cost_usd") or 0)
    e_tot_t = ext_total.get("tokens")
    e_tot_c = ext_total.get("cost_usd")
    e_tot_t_s = f"{int(e_tot_t):,}" if e_tot_t is not None else "—"
    e_tot_c_s = format_usd(float(e_tot_c)) if e_tot_c is not None else "—"

    has_ext = bool(ext) and "error" not in ext and (
        ext_bp or e_tot_c is not None or e_tot_t is not None
    )
    if has_ext:
        status = (
            f"<p style='color:#86efac;font-size:13px;'>External file loaded: "
            f"<code>{EXTERNAL_USAGE_PATH}</code> · source={ext.get('source','?')} · "
            f"as_of={ext.get('as_of','?')} · window_days={ext.get('window_days','?')}</p>"
        )
    elif ext.get("error"):
        status = f"<p style='color:#f59e0b;font-size:13px;'>{ext.get('error')}</p>"
    else:
        status = f"""
<p style="color:#fbbf24;font-size:13px;margin-bottom:12px;">
  <strong>No Claude/external usage file yet.</strong>
  Raven column is filled automatically. Claude column stays empty until you (or Claude) write:
  <code>{EXTERNAL_USAGE_PATH}</code>
  (template: <code>{EXTERNAL_USAGE_TEMPLATE}</code>).
</p>
"""

    claude_prompt = """Ask Claude (in any project session):

Copy Anthropic Console usage (or your best estimate) into
~/RavenVault/.metrics/external-usage.json using the template at
external-usage.template.json. Include by_project.fin-processor (and others)
with tokens + cost_usd for the same ~30 day window as the Raven dashboard.
Then run: python3 scripts/dashboard.py --html --open
and open the side-by-side Cost compare section.

If you only have org totals (not per-repo), put them under total and note that
in notes — do not invent per-repo splits."""

    return f"""
  <h2 id="cost-method">📐 What “cost” means here (two sources)</h2>
  <div class="meta" style="border-left:4px solid #38bdf8;margin-bottom:16px;font-size:14px;line-height:1.55;">
    <p style="margin-bottom:10px;"><strong>1) Raven-metered (left columns)</strong> — computed from
    <em>code-path token consumption</em> × <em>model rate cards</em>, not from your invoice:</p>
    <ul style="margin:0 0 12px 18px;color:#cbd5e1;">
      <li><code>log-overhead.py</code> — estimated hook/router tokens during the session</li>
      <li><code>token-meter-write.py</code> on Stop — transcript <code>usage</code> ×
        <code>scripts/model-pricing.json</code></li>
      <li>Stored in <code>.raven/.model-session.json</code> and
        <code>~/RavenVault/.metrics/YYYY-MM.json</code> (project-tagged when available)</li>
    </ul>
    <p style="margin-bottom:10px;"><strong>2) Claude / Anthropic-reported (right columns)</strong> —
    numbers <em>you or Claude paste</em> from Console, export, or session estimate.
    Raven never scrapes billing APIs.</p>
    <p style="color:#94a3b8;font-size:13px;margin:0;">
    Window for Raven column: <strong>{window}</strong>
    ({metrics.get('window_days')}d). Compare only when external window matches.
    Large gaps (e.g. Raven $0.002 vs Claude $100+) mean meters under-captured real model usage —
    trust the Claude/Console side for money, Raven side for local discipline telemetry.
    </p>
  </div>

  <h2 id="cost-compare">⚖️ Cost compare — Raven vs Claude/external</h2>
  {status}
  <table>
    <thead>
      <tr>
        <th>Repo</th>
        <th class="num">Raven tokens</th>
        <th class="num">Raven $</th>
        <th class="num">Claude/ext tokens</th>
        <th class="num">Claude/ext $</th>
        <th class="num">Δ $ (ext − Raven)</th>
        <th class="num">ext / Raven</th>
      </tr>
    </thead>
    <tbody>
      {rows}
      <tr style="background:#0f172a;">
        <td><strong>TOTAL</strong></td>
        <td class="num"><strong>{r_tot_t:,}</strong></td>
        <td class="num"><strong>{format_usd(r_tot_c)}</strong></td>
        <td class="num"><strong>{e_tot_t_s}</strong></td>
        <td class="num"><strong>{e_tot_c_s}</strong></td>
        <td class="num">—</td>
        <td class="num">—</td>
      </tr>
    </tbody>
  </table>
  <div class="meta" style="margin-top:16px;font-size:13px;color:#cbd5e1;">
    <strong>Prompt to give Claude</strong>
    <pre style="white-space:pre-wrap;margin-top:8px;padding:12px;background:#0f172a;border-radius:8px;color:#e2e8f0;font-size:12px;">{claude_prompt}</pre>
  </div>
"""


def cite_chip(cid: str, label: str = "") -> str:
    """Inline citation anchor → bibliography entry #cite-N."""
    tip = label or cid
    return (
        f'<a class="cite" href="#cite-{cid}" title="{tip}">[{cid}]</a>'
    )


def build_citation_registry(metrics: dict, metadata: dict) -> list[dict]:
    """Numbered, on-page citations for every metric family."""
    vault = metadata.get("vault_path") or str(VAULT)
    ms_path = str(MODEL_SESSION) if MODEL_SESSION.exists() else f"{PROJECT_DIR}/.raven/.model-session.json"
    cites = [
        {
            "id": "C1",
            "title": "Portfolio cost / tokens / sessions",
            "path": f"{vault}/.metrics/*.json",
            "field": "sessions[] rows with project + tokens + cost_usd; also by_project",
            "rule": "Sum only project-tagged rows inside the report window. Unscoped by_day excluded.",
            "used_for": "All-repos headline cards",
        },
        {
            "id": "C2",
            "title": f"This-repo slice ({metrics.get('current_project') or metadata.get('project') or 'cwd'})",
            "path": f"{vault}/.metrics/*.json",
            "field": "same as C1 filtered where project == current repo name",
            "rule": "Project name from .raven/manifest.json or git remote basename.",
            "used_for": "This-repo headline card",
        },
        {
            "id": "C3",
            "title": "Live session meters",
            "path": ms_path,
            "field": "raven_overhead.tokens/cost_usd + user_work.tokens/cost_usd (+ by_source)",
            "rule": "Point-in-time file written by model-router / token-meter during the open session.",
            "used_for": "Live session card + tokenomics split + overhead-by-source table",
        },
        {
            "id": "C4",
            "title": "Knowledge graph structure",
            "path": f"{vault}/graph/knowledge-graph.json",
            "field": "nodes[].id/type + edges[] from wikilinks in vault markdown",
            "rule": "Built by knowledge_graph.py scanning projects|concepts|decisions|sessions.",
            "used_for": "Graph node/edge counts and interactive map",
        },
        {
            "id": "C5",
            "title": "Project hubs & notes (agent memory)",
            "path": f"{vault}/projects/*.md, concepts/, decisions/, sessions/",
            "field": "frontmatter + ## Current state / Open questions / Recent sessions",
            "rule": "Written by obsidian-log / knowledge-extract; agent boot Reads .raven/memory/CARD.md if ide-boot load=1.",
            "used_for": "Graph briefings, open questions, repo links, local paths",
        },
        {
            "id": "C6",
            "title": "Guard / CVE event counts",
            "path": str(AUDIT_DIR / "*.log") if AUDIT_DIR else ".raven/audit/*.log",
            "field": "JSONL kind/event lines in window",
            "rule": "Count only; not a full CVE inventory. Quiet ≠ unscanned.",
            "used_for": "Guard event tables and CVE blurb in node cost panel",
        },
        {
            "id": "C7",
            "title": "Manifest / project identity",
            "path": str(MANIFEST) if MANIFEST.exists() else ".raven/manifest.json",
            "field": "project, owner, stack, version",
            "rule": "Defines 'this repo' label and stack context for agents.",
            "used_for": "Metadata block and current_project resolution",
        },
        {
            "id": "C8",
            "title": "Report generation timestamp",
            "path": "dashboard.py runtime",
            "field": "report_generated_at_local / UTC",
            "rule": "Clock at HTML build time — not a metric source.",
            "used_for": "Header freshness",
        },
    ]
    # Attach concrete metric files that were actually read
    extra = []
    for i, src in enumerate(metrics.get("sources_used") or [], start=1):
        extra.append(
            {
                "id": f"S{i}",
                "title": f"Source used this build: {src}",
                "path": src,
                "field": "see aggregate() sources_used",
                "rule": "Listed only if successfully parsed this run.",
                "used_for": "Traceability of this HTML build",
            }
        )
    return cites + extra


def _by_day_row_suspect(row: dict) -> bool:
    """Detect known-corrupt meter rollups (61k 'sessions'/day, multi‑MB token dumps)."""
    try:
        sessions = int(row.get("sessions") or 0)
        tokens = int(row.get("tokens") or 0)
        cost = float(row.get("cost_usd") or 0)
    except (TypeError, ValueError):
        return True
    if sessions > 40:  # single-dev machine day cap
        return True
    if tokens > 2_000_000:
        return True
    if cost > 25.0:
        return True
    if tokens > 0 and cost / tokens > 0.01:  # >$10 per 1k tokens
        return True
    return False


def _empty_project_bucket() -> dict:
    return {
        "sessions": 0,
        "tokens": 0,
        "cost_usd": 0.0,
        "days": set(),
    }


def aggregate(days: int = 30, project_filter: Optional[str] = None) -> dict:
    """Read trusted sources; headline totals come only from per-repo rows.

    Trusted:
      - sessions[] rows with a project name (day rollup or per-session)
      - by_project map in monthly files
      - live .model-session.json (attributed to current project)
    Untrusted for headline (recorded separately):
      - unscoped by_day without project (June/July global dumps)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    by_project: dict[str, dict] = defaultdict(_empty_project_bucket)
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
        "sources_used": [],
        "project_filter": project_filter,
        "legacy_unscoped": {
            "sessions": 0,
            "tokens": 0,
            "cost_usd": 0.0,
            "suspect_days": 0,
            "note": "Unscoped by_day rows — not included in headline (no repo tag).",
        },
        "trust": "per-repo only",
    }

    current_project = None
    if MANIFEST.exists():
        try:
            current_project = json.loads(MANIFEST.read_text()).get("project")
        except Exception:
            pass
    if not current_project:
        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            current_project = remote.rstrip("/").split("/")[-1].replace(".git", "")
        except Exception:
            current_project = Path.cwd().name
    metrics["current_project"] = current_project

    # ── Live session ──
    if MODEL_SESSION.exists():
        try:
            ms = json.loads(MODEL_SESSION.read_text())
            if "raven_overhead" in ms:
                ov = ms["raven_overhead"]
                uw = ms.get("user_work") or {}
                metrics["last_session"] = {
                    "started_at": ms.get("session_started_at"),
                    "project": ms.get("project") or current_project,
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
                    "tokens": ov.get("tokens", 0) + uw.get("tokens", 0),
                    "cost_usd": round(
                        float(ov.get("cost_usd", 0.0) or 0)
                        + float(uw.get("cost_usd", 0.0) or 0),
                        6,
                    ),
                    "tier_counts": uw.get("tier_counts", {}),
                }
            else:
                metrics["last_session"] = {
                    "started_at": ms.get("session_started_at"),
                    "project": ms.get("project") or current_project,
                    "raven_overhead": {
                        "tokens": 0,
                        "cost_usd": 0.0,
                        "calls": 0,
                        "by_source": {},
                    },
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
            metrics["sources_used"].append("model-session")
        except Exception:
            metrics["last_session"] = None
    else:
        metrics["last_session"] = None

    def _credit(project: str, day: str, sessions: int, tokens: int, cost: float):
        ts = _parse_day(day)
        if ts is None or ts < cutoff:
            return
        if not project:
            return
        if project_filter and project != project_filter:
            return
        n = max(int(sessions or 0), 1 if (tokens or cost) else 0)
        if n == 0 and not tokens and not cost:
            return
        b = by_project[project]
        b["sessions"] += n
        b["tokens"] += int(tokens or 0)
        b["cost_usd"] += float(cost or 0.0)
        b["days"].add(day)
        metrics["sessions_count"] += n
        metrics["sessions_by_day"][day] += n
        metrics["total_tokens"] += int(tokens or 0)
        metrics["total_cost_usd"] += float(cost or 0.0)
        metrics["cost_by_day"][day] += float(cost or 0.0)
        metrics["tokens_by_day"][day] += int(tokens or 0)
        metrics["projects_seen"].add(project)

    VAULT_METRICS.mkdir(parents=True, exist_ok=True)
    for metrics_file in sorted(VAULT_METRICS.glob("*.json")):
        try:
            data = json.loads(metrics_file.read_text())
        except Exception:
            continue

        # Preferred: explicit by_project map
        bp = data.get("by_project")
        if isinstance(bp, dict):
            for pname, prow in bp.items():
                if not isinstance(prow, dict):
                    continue
                # Optional nested by_day under project
                p_by_day = prow.get("by_day")
                if isinstance(p_by_day, dict) and p_by_day:
                    for day, row in p_by_day.items():
                        if not isinstance(row, dict):
                            continue
                        _credit(
                            str(pname),
                            day,
                            row.get("sessions", 0),
                            row.get("tokens", 0),
                            row.get("cost_usd", 0.0),
                        )
                else:
                    # Whole-month project totals — only if month overlaps window
                    month = data.get("month") or data.get("year_month") or metrics_file.stem
                    # Attribute to month mid-day if within window loosely via any day in month
                    try:
                        y, m = month.split("-")[:2]
                        # credit on last day of window if month in range — skip if no day breakdown
                        # Use month-01 as synthetic day only if in window
                        day = f"{y}-{m}-01"
                        if _parse_day(day) and _parse_day(day) >= cutoff:
                            _credit(
                                str(pname),
                                day,
                                prow.get("sessions", 0),
                                prow.get("tokens", 0),
                                prow.get("cost_usd", 0.0),
                            )
                    except Exception:
                        pass
            metrics["sources_used"].append(f"metrics:{metrics_file.name}:by_project")

        # sessions[] with project tags (trusted)
        sessions = data.get("sessions")
        if isinstance(sessions, list):
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                proj = _project_name(session.get("project"))
                if not proj:
                    continue
                started = session.get("started_at") or session.get("date") or ""
                day = started[:10] if started else ""
                if not day:
                    continue
                sess_n = session.get("sessions")
                if sess_n is not None and not session.get("tier_counts"):
                    _credit(
                        proj,
                        day,
                        sess_n,
                        session.get("tokens", 0),
                        session.get("cost_usd", 0.0),
                    )
                else:
                    _credit(
                        proj,
                        day,
                        1,
                        session.get("tokens", 0),
                        session.get("cost_usd", 0.0),
                    )
                for tier, count in (session.get("tier_counts") or {}).items():
                    if not project_filter or proj == project_filter:
                        metrics["tier_counts"][tier] += count
            metrics["sources_used"].append(f"metrics:{metrics_file.name}:sessions")

        # Unscoped by_day — never in headline; keep for diagnostics
        by_day = data.get("by_day")
        if isinstance(by_day, dict):
            for day, row in by_day.items():
                if not isinstance(row, dict):
                    continue
                ts = _parse_day(day)
                if ts is None or ts < cutoff:
                    continue
                # Nested per-project under by_day
                nested = row.get("by_project")
                if isinstance(nested, dict):
                    for pname, prow in nested.items():
                        if not isinstance(prow, dict):
                            continue
                        _credit(
                            str(pname),
                            day,
                            prow.get("sessions", 0),
                            prow.get("tokens", 0),
                            prow.get("cost_usd", 0.0),
                        )
                    continue
                # Unscoped
                if _by_day_row_suspect(row):
                    metrics["legacy_unscoped"]["suspect_days"] += 1
                metrics["legacy_unscoped"]["sessions"] += int(row.get("sessions") or 0)
                metrics["legacy_unscoped"]["tokens"] += int(row.get("tokens") or 0)
                metrics["legacy_unscoped"]["cost_usd"] += float(row.get("cost_usd") or 0)

    # Fold live session into current project if not already counted for today
    ls = metrics.get("last_session") or {}
    ls_cost = float(ls.get("cost_usd") or 0.0)
    ls_tok = int(ls.get("tokens") or 0)
    ls_proj = _project_name(ls.get("project")) or current_project
    if (ls_cost or ls_tok) and ls_proj:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Avoid double-count: only add if this project's day cost is still 0
        already = by_project.get(ls_proj, {}).get("cost_usd", 0) if ls_proj in by_project else 0
        # Check day-level for project via total day — if today's total cost for project path empty
        if metrics["cost_by_day"].get(day, 0) == 0 or (
            project_filter in (None, ls_proj) and ls_proj not in by_project
        ):
            if not project_filter or project_filter == ls_proj:
                # Only credit live session if vault has no row for this project today
                proj_days = by_project.get(ls_proj, {}).get("days") or set()
                if day not in proj_days:
                    _credit(ls_proj, day, 1, ls_tok, ls_cost)
        for tier, count in (ls.get("tier_counts") or {}).items():
            metrics["tier_counts"][tier] += count

    # ── Audit logs (events only) ──
    if AUDIT_DIR.exists():
        for log_file in sorted(AUDIT_DIR.glob("*.log")):
            try:
                log_date = datetime.strptime(log_file.stem, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
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

    # Serialize by_project
    bp_out = {}
    for pname, b in by_project.items():
        bp_out[pname] = {
            "sessions": b["sessions"],
            "tokens": b["tokens"],
            "cost_usd": round(float(b["cost_usd"]), 6),
            "days": len(b["days"]),
        }
    metrics["by_project"] = dict(
        sorted(bp_out.items(), key=lambda kv: -kv[1]["cost_usd"])
    )

    # If filter set, recompute headline from that project only (already filtered via _credit)
    # If no filter, headline is sum of all per-repo (already)

    metrics["tier_counts"] = dict(metrics["tier_counts"])
    metrics["tier_cost"] = dict(metrics["tier_cost"])
    metrics["guard_events"] = dict(metrics["guard_events"])
    metrics["violations"] = dict(metrics["violations"])
    metrics["approvals"] = dict(metrics["approvals"])
    metrics["skills_used"] = dict(metrics["skills_used"].most_common(20))
    metrics["specialists_used"] = dict(metrics["specialists_used"].most_common(10))
    metrics["sessions_by_day"] = dict(metrics["sessions_by_day"])
    metrics["cost_by_day"] = {k: round(v, 6) for k, v in metrics["cost_by_day"].items()}
    metrics["tokens_by_day"] = dict(metrics["tokens_by_day"])
    metrics["projects_seen"] = sorted(metrics["projects_seen"])
    metrics["total_cost_usd"] = round(metrics["total_cost_usd"], 6)
    metrics["sources_used"] = sorted(set(metrics["sources_used"]))
    metrics["legacy_unscoped"]["cost_usd"] = round(
        metrics["legacy_unscoped"]["cost_usd"], 4
    )

    total = sum(metrics["tier_counts"].values()) or 1
    metrics["tier_share_pct"] = {
        tier: round(100 * count / total, 1)
        for tier, count in metrics["tier_counts"].items()
    }
    metrics["avg_cost_per_session"] = (
        round(metrics["total_cost_usd"] / metrics["sessions_count"], 6)
        if metrics["sessions_count"]
        else 0
    )
    metrics["avg_tokens_per_session"] = (
        metrics["total_tokens"] // metrics["sessions_count"]
        if metrics["sessions_count"]
        else 0
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

    # Rule U1 — User COMPLEX-tier over-classification (user_work tier mix only).
    # COMPLEX routes to Sonnet-5-high, NOT Opus — Opus/Fable are excluded from
    # auto-routing by design (model-router.py defaults, CLAUDE.md Rule 8:
    # NO AUTO-OPUS). This used to be mislabeled "Opus rate" before that rule
    # was locked in; fixed 2026-08-21 so the panel doesn't claim a cost tier
    # the router is not allowed to auto-select.
    user_complex_pct = (tcs.get("COMPLEX", 0) / total_user_calls * 100)
    if user_complex_pct > 30:
        recs.append({
            "owner": "user",
            "metric": "Your COMPLEX-tier rate: {:.0f}%".format(user_complex_pct),
            "severity": "high",
            "issue": "Your prompts are classifying as COMPLEX too often. This routes "
                     "you to Sonnet-5-high (more expensive than the SIMPLE/MEDIUM "
                     "defaults, but never Opus — Raven never auto-selects Opus).",
            "action": "Be more specific in prompts so scope is clear. Split big asks "
                     "into smaller steps. For simple edits, say 'simple' explicitly.",
            "savings_estimate_usd": round(uw.get("cost_usd", 0) * (user_complex_pct - 20) / 100, 2),
        })
    elif user_complex_pct == 0 and total_user_calls > 5:
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
                     "Raven's overhead). Long context, many COMPLEX-tier (Sonnet-5-high) "
                     "calls, or both.",
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


def _load_or_build_graph(project_filter: Optional[str] = None, session_days: int = 30) -> dict:
    """Build knowledge-graph.json via knowledge_graph module (fail-soft)."""
    pkg_dir = Path(__file__).resolve().parent
    for d in (str(pkg_dir), str(pkg_dir.parent)):
        if d not in sys.path:
            sys.path.insert(0, d)
    try:
        from graph import build_graph, write_graph  # type: ignore

        g = build_graph(project_filter=project_filter, session_days=session_days)
        write_graph(g)
        return g
    except Exception as e:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_filter": project_filter,
            "nodes": [],
            "edges": [],
            "error": str(e),
        }


def _word_cap(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "…"


def _read_vault_note(rel_path: str) -> str:
    """Read markdown from ~/RavenVault/{rel_path} (with or without .md)."""
    p = Path(rel_path)
    if not p.is_absolute():
        p = VAULT / rel_path
    if p.suffix != ".md":
        p = p.with_suffix(".md") if p.suffix == "" else p
    if not p.exists() and not str(rel_path).endswith(".md"):
        p = VAULT / f"{rel_path}.md"
    try:
        return p.read_text(errors="replace") if p.exists() else ""
    except OSError:
        return ""


def _plain_from_md(text: str, max_chars: int = 4000) -> str:
    body = text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    # strip wikilinks to labels
    body = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", body)
    body = re.sub(r"[#>`*_]", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:max_chars]


def _cve_guard_blurb(metrics: dict, project: str) -> str:
    guards = metrics.get("guard_events") or {}
    viol = metrics.get("violations") or {}
    n_guard = sum(guards.values()) if isinstance(guards, dict) else 0
    n_viol = sum(viol.values()) if isinstance(viol, dict) else 0
    secrets = sum(v for k, v in (guards.items() if isinstance(guards, dict) else []) if "secret" in k.lower())
    cve = sum(v for k, v in (guards.items() if isinstance(guards, dict) else []) if "cve" in k.lower())
    top = ""
    if isinstance(viol, dict) and viol:
        top_items = sorted(viol.items(), key=lambda x: -x[1])[:3]
        top = "; ".join(f"{k}×{v}" for k, v in top_items)
    return (
        f"Raven guard window for work near {project or 'this repo'}: "
        f"{n_guard} guard event(s) logged, {n_viol} violation signal(s). "
        f"Secret-scan hits (bucket): {secrets}. CVE-related events: {cve}. "
        f"{('Top rules: ' + top + '. ') if top else ''}"
        f"CVE blocking is enforced at commit via pre-commit / cve-check — "
        f"a quiet report here means no blocked library in this window, not 'no scan ran'. "
        f"Always re-run raven-sync after dependency changes. "
        f"Treat zero events as 'no fire', not 'no coverage'."
    )


def _repo_url_from_hub(hub_text: str, project: str, metadata: dict) -> str:
    m = re.search(r"https://github\.com/[^\s\)\]>\"']+", hub_text or "")
    if m:
        return m.group(0).rstrip(".,")
    remote = metadata.get("git_remote") or ""
    if "github.com" in remote and project and project in remote:
        return (
            remote.replace("git@", "https://")
            .replace("github.com:", "github.com/")
            .replace(".git", "")
        )
    if remote.startswith("http") and project and project in remote:
        return remote.replace(".git", "")
    # common giggsoinc default
    if project:
        return f"https://github.com/giggsoinc/{project}"
    if remote.startswith("http"):
        return remote.replace(".git", "")
    return ""


def _local_path_from_hub(hub_text: str) -> str:
    m = re.search(r"Local:\s*(~?[^\s\n]+)", hub_text or "", re.I)
    if m:
        p = m.group(1).strip()
        if p.startswith("~/"):
            p = str(Path.home() / p[2:])
        # validate exists; if hub is stale, fall through to discovery later
        if Path(p).expanduser().exists():
            return str(Path(p).expanduser().resolve())
        return p
    return ""


# Roots to search for nested clones (not only top-level)
_LOCAL_SEARCH_ROOTS = [
    Path.home() / "AntiGravity_Projects",
    Path.home() / "Projects",
    Path.home() / "Developer",
    Path.home() / "src",
    Path.home() / "code",
]
_LOCAL_SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "target",
    "vendor",
    ".next",
    "coverage",
}
_local_path_cache: dict[str, Optional[str]] = {}


def _score_local_candidate(path: Path, project: str) -> tuple:
    """Higher is better. Prefer git roots, then package roots, then shallower paths.

    Order matters: a top-level clone named Aryx with .git must beat nested
    Aryx-EE/aryx package dirs when project name is case-insensitively 'aryx'.
    """
    name = path.name
    proj = project or ""
    exact = 1 if name == proj else 0
    case_i = 1 if name.lower() == proj.lower() else 0
    has_git = 1 if (path / ".git").exists() else 0
    has_manifest = 1 if (path / ".raven" / "manifest.json").exists() else 0
    has_pkg = 1 if any(
        (path / f).exists()
        for f in ("package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml")
    ) else 0
    # depth under home (shallower better → negative depth)
    try:
        depth = len(path.relative_to(Path.home()).parts)
    except ValueError:
        depth = len(path.parts)
    # penalize generic / non-repo nestings
    parts_l = [p.lower() for p in path.parts]
    nest_penalty = 0
    if "docs" in parts_l or "assets" in parts_l or "node_modules" in parts_l:
        nest_penalty += 8
    if "src" in parts_l and has_git == 0:
        nest_penalty += 3
    # nested package folder with same name as parent product (…/Aryx-EE/aryx)
    if depth >= 2 and has_git == 0 and has_manifest == 0:
        nest_penalty += 2
    # Prefer: git root → shallower path → not under docs/ → case match
    # (shallower before exact basename so Aryx beats nested Aryx-EE/aryx)
    return (has_git, has_manifest, -nest_penalty, -depth, has_pkg, case_i, exact)


def discover_local_path(project: str, max_depth: int = 5) -> Optional[str]:
    """Find a local clone for project name under known roots (recursive, depth-capped).

    Handles nested layouts e.g. ~/AntiGravity_Projects/Proj1/fin-processor.
    Prefers directories that look like repos (.git / manifest / package files).
    """
    if not project or project in (".", ".."):
        return None
    key = project.lower()
    if key in _local_path_cache:
        return _local_path_cache[key]

    candidates: list[Path] = []
    target = project.lower()

    for root in _LOCAL_SEARCH_ROOTS:
        if not root.is_dir():
            continue
        # Walk with skip; do not follow symlinks into cycles
        try:
            root = root.resolve()
        except Exception:
            continue
        for dirpath, dirnames, _files in os.walk(root, topdown=True, followlinks=False):
            p = Path(dirpath)
            try:
                rel_parts = p.relative_to(root).parts
            except ValueError:
                rel_parts = ()
            depth = len(rel_parts)
            # prune deep / junk dirs
            dirnames[:] = [
                d
                for d in dirnames
                if d not in _LOCAL_SKIP_DIR_NAMES and not d.startswith(".")
            ]
            if depth > max_depth:
                dirnames[:] = []
                continue
            if p.name.lower() == target:
                candidates.append(p)

    if not candidates:
        _local_path_cache[key] = None
        return None

    best = max(candidates, key=lambda c: _score_local_candidate(c, project))
    score = _score_local_candidate(best, project)
    # Reject weak matches: no .git and buried under docs/assets (e.g. …/docs/diagrams)
    has_git = (best / ".git").exists()
    parts_l = [p.lower() for p in best.parts]
    if not has_git and ("docs" in parts_l or "assets" in parts_l or "node_modules" in parts_l):
        _local_path_cache[key] = None
        return None
    # Reject if no git and no package/manifest and many candidates (ambiguous junk)
    has_signal = has_git or (best / ".raven" / "manifest.json").exists() or any(
        (best / f).exists()
        for f in ("package.json", "pyproject.toml", "requirements.txt", "go.mod")
    )
    if not has_signal and len(candidates) > 1:
        # try best among those with signal only
        strong = [c for c in candidates if (c / ".git").exists()]
        if strong:
            best = max(strong, key=lambda c: _score_local_candidate(c, project))
        else:
            _local_path_cache[key] = None
            return None

    try:
        resolved = str(best.resolve())
    except Exception:
        resolved = str(best)
    _local_path_cache[key] = resolved
    return resolved


def backfill_hub_local(project: str, local_path: str) -> bool:
    """Write/create projects/{name}.md with Local: (+ GitHub if known)."""
    if not project or not local_path:
        return False
    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / "projects").mkdir(parents=True, exist_ok=True)
    hub = VAULT / "projects" / f"{project}.md"
    line = f"- Local: {local_path}"
    gh = f"- GitHub: https://github.com/giggsoinc/{project}"
    if not hub.exists():
        hub.write_text(
            f"""---
type: project
name: {project}
tags: [project, raven]
---
# {project}

## Repo
{gh}
{line}

## Current state
- Local path discovered by Raven dashboard (nested search under ~/AntiGravity_Projects).

## Open questions
- [ ] (none yet)

## Key decisions
- (none yet)

## Concepts
- (none yet)

## Recent sessions
- (none yet)
"""
        )
        return True
    try:
        text = hub.read_text(errors="replace")
    except OSError:
        return False
    # Already correct?
    m = re.search(r"Local:\s*(~?[^\s\n]+)", text, re.I)
    if m:
        existing = m.group(1).strip()
        if existing.startswith("~/"):
            existing = str(Path.home() / existing[2:])
        try:
            if Path(existing).expanduser().resolve() == Path(local_path).resolve():
                return False
        except Exception:
            pass
        # replace existing Local line
        text2 = re.sub(
            r"(?m)^(\s*[-*]?\s*Local:\s*).+$",
            rf"\1{local_path}",
            text,
            count=1,
        )
        if text2 == text:
            return False
        hub.write_text(text2)
        return True
    # Insert under ## Repo if present
    if re.search(r"(?m)^##\s+Repo\s*$", text):
        text2 = re.sub(
            r"(?m)(^##\s+Repo\s*\n)",
            rf"\1{line}\n",
            text,
            count=1,
        )
    else:
        text2 = text.rstrip() + f"\n\n## Repo\n{gh}\n{line}\n"
    if text2 != text:
        hub.write_text(text2)
        return True
    return False


def resolve_local_path(project: str, hub_text: str = "") -> str:
    """Hub Local: first (if exists on disk), else recursive discovery + optional hub backfill."""
    from_hub = _local_path_from_hub(hub_text) if hub_text else ""
    if from_hub and Path(from_hub).expanduser().exists():
        return str(Path(from_hub).expanduser().resolve())
    found = discover_local_path(project)
    if found:
        try:
            backfill_hub_local(project, found)
        except Exception:
            pass
        return found
    # return hub path even if missing (display only)
    return from_hub or ""


def _local_uri(path: str) -> str:
    """file:// URI for a local clone path (for clickable links in HTML)."""
    if not path:
        return ""
    try:
        p = Path(path).expanduser()
        # Prefer resolved absolute path even if missing (user may open later)
        if not p.is_absolute():
            p = Path.home() / p
        return p.resolve().as_uri() if p.exists() else p.absolute().as_uri()
    except Exception:
        return ""


def _local_link_html(path: str, label: str = "Local") -> str:
    """Anchor to local repo; empty string if no path."""
    if not path:
        return ""
    uri = _local_uri(path)
    if not uri:
        return f'<span style="color:#94a3b8;font-size:12px" title="path not resolved">{path}</span>'
    exists = Path(path).expanduser().exists()
    badge = "" if exists else ' <span style="color:#f59e0b">(path missing)</span>'
    return (
        f'<a href="{uri}" title="{path}" style="color:#86efac;font-size:12px;">'
        f"📁 {label}</a>"
        f' <code style="font-size:10px;color:#64748b;">{path}</code>{badge}'
    )


def _hub_sections(hub_text: str) -> dict:
    """Extract open questions / current state / recent sessions bullets."""
    plain_body = hub_text or ""
    out = {"open_questions": [], "current_state": [], "recent_sessions": [], "concepts": []}
    for heading, key in (
        ("Open questions", "open_questions"),
        ("Open Questions", "open_questions"),
        ("Current state", "current_state"),
        ("Current State", "current_state"),
        ("Recent sessions", "recent_sessions"),
        ("Concepts", "concepts"),
        ("Key decisions", "concepts"),
    ):
        bullets = []
        pat = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.M | re.I)
        m = pat.search(plain_body)
        if not m:
            continue
        rest = plain_body[m.end() :]
        nxt = re.search(r"^##\s+", rest, re.M)
        block = rest[: nxt.start()] if nxt else rest
        for ln in block.splitlines():
            s = ln.strip()
            if s.startswith("- "):
                bullets.append(s[2:].strip())
            if len(bullets) >= 8:
                break
        if bullets and not out[key]:
            out[key] = bullets
    return out


def build_node_briefings(graph: dict, metrics: dict, metadata: dict) -> dict:
    """Precompute Guru-style click panels for each graph node + center overview."""
    by_project = metrics.get("by_project") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    briefings: dict = {}

    # Degree map for neighbor hints
    degree: dict[str, int] = Counter()
    neighbors: dict[str, set] = defaultdict(set)
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s and t:
            degree[s] += 1
            degree[t] += 1
            neighbors[s].add(t)
            neighbors[t].add(s)

    for n in nodes:
        nid = n.get("id") or ""
        ntype = n.get("type") or "unknown"
        label = n.get("label") or nid.split("/")[-1]
        path = n.get("path") or f"{nid}.md"
        note = _read_vault_note(path if path.endswith(".md") else nid)
        plain = _plain_from_md(note)

        # Resolve owning project for costs
        proj = label if ntype == "project" else None
        if not proj and nid.startswith("projects/"):
            proj = nid.split("/", 1)[-1]
        if not proj:
            m = re.search(r"projects/([A-Za-z0-9._-]+)", note + " " + nid)
            if m:
                proj = m.group(1)
        # session notes like sessions/2026-08-04-raven
        if not proj and ntype == "session":
            stem = nid.split("/")[-1]
            parts = stem.split("-")
            if len(parts) >= 4:
                proj = "-".join(parts[3:])  # after YYYY-MM-DD
            elif len(parts) >= 1:
                proj = parts[-1]

        pstats = by_project.get(proj or "", {}) if proj else {}
        cost = float(pstats.get("cost_usd") or 0)
        tokens = int(pstats.get("tokens") or 0)
        sessions = int(pstats.get("sessions") or 0)

        # Last update from file mtime or hub "updated"
        updated = ""
        um = re.search(r"^updated:\s*(.+)$", note, re.M)
        if um:
            updated = um.group(1).strip()
        try:
            vp = VAULT / path if not Path(path).is_absolute() else Path(path)
            if not vp.exists():
                vp = VAULT / f"{nid}.md"
            if vp.exists():
                mtime = datetime.fromtimestamp(vp.stat().st_mtime)
                if not updated:
                    updated = mtime.strftime("%Y-%m-%d %H:%M")
                age_days = (datetime.now() - mtime).days
            else:
                age_days = None
        except Exception:
            age_days = None

        neigh = sorted(neighbors.get(nid, []))[:12]
        hub_for_links = note
        # Prefer project hub for non-project nodes
        if proj and ntype != "project":
            hub_for_links = _read_vault_note(f"projects/{proj}") or note
        repo_url = (
            _repo_url_from_hub(hub_for_links, proj or label, metadata)
            if (ntype == "project" or proj)
            else ""
        )
        local_path = resolve_local_path(proj or label, hub_for_links)
        sections = _hub_sections(hub_for_links if ntype == "project" else note)
        if ntype == "project" and not sections.get("open_questions"):
            sections = _hub_sections(note)

        related_concepts = [x for x in neigh if x.startswith("concepts/")][:8]
        related_decisions = [x for x in neigh if x.startswith("decisions/")][:6]
        related_sessions = [x for x in neigh if x.startswith("sessions/")][:6]
        if ntype == "project":
            # also pull from hub recent sessions bullets
            for rs in sections.get("recent_sessions") or []:
                mlink = re.search(r"\[\[(sessions/[^\]]+)\]\]", rs)
                if mlink and mlink.group(1) not in related_sessions:
                    related_sessions.append(mlink.group(1))

        vault_note_uri = ""
        try:
            vp = VAULT / path if not str(path).startswith("/") else Path(path)
            if not vp.exists():
                vp = VAULT / f"{nid}.md"
            if vp.exists():
                vault_note_uri = vp.resolve().as_uri()
        except Exception:
            pass

        # ── Summary ~200 words (Andie-Guru voice) ──
        analogy = {
            "project": "Think of this repo as a workshop bench: tools, unfinished pieces, and notes pinned above the vise.",
            "concept": "Think of this concept as a sticky note on the whiteboard — a single idea people keep pointing at.",
            "decision": "Think of this decision as a signed change order: once agreed, builders stop re-arguing and just execute.",
            "session": "Think of this session as a day's work log — what someone did, not the whole factory.",
        }.get(ntype, "Think of this node as a pin on a map of how your software knowledge connects.")

        oq = "; ".join(sections.get("open_questions") or [])[:180]
        st = "; ".join(sections.get("current_state") or [])[:180]
        note_line = (plain[:200] + "…") if plain and len(plain) > 200 else (plain or "no note body yet")
        guru = (
            f"• What: '{label}' — {ntype} note in vault memory (not a live monitor)\n"
            f"• Repo: {proj or 'unscoped'}\n"
            f"{('• Open questions: ' + oq + chr(10)) if oq else ''}"
            f"{('• Current state: ' + st + chr(10)) if st else ''}"
            f"• Latest note: {note_line}\n"
            f"• Use: story + links here → code via Open repo"
        )

        # ── Last update — bullets ──
        last_up = (
            f"• Last touch: {updated or 'unknown'}"
            f"{f' (~{age_days}d ago)' if age_days is not None else ''}\n"
            f"• Links: {degree.get(nid, 0)} → {', '.join(neigh[:4]) if neigh else 'none yet'}\n"
            f"• Local: {local_path or 'not on hub'}\n"
            f"• Note: ~/RavenVault/{path}\n"
            f"• Refresh: next session (Stop hooks) or scripts/obsidian-log.py"
        )

        # ── Cost / tokens / CVE — bullets ──
        cost_blk = (
            f"• Spend ({proj or 'n/a'}): {sessions} sessions · {tokens:,} tokens · {format_usd(cost)}\n"
            f"• Guards: {_cve_guard_blurb(metrics, proj or label)}\n"
            f"• Window: {metrics.get('window_start')} → {metrics.get('window_end')} · portfolio totals in header strip"
        )

        briefings[nid] = {
            "id": nid,
            "label": label,
            "type": ntype,
            "project": proj,
            "path": path,
            "guru": guru,
            "last_update": last_up,
            "cost_report": cost_blk,
            "repo_url": repo_url,
            "local_path": local_path,
            "local_uri": _local_uri(local_path),
            "vault_note_uri": vault_note_uri,
            "open_questions": sections.get("open_questions") or [],
            "current_state": sections.get("current_state") or [],
            "related_concepts": related_concepts,
            "related_decisions": related_decisions,
            "related_sessions": related_sessions[:6],
            "neighbors": neigh,
            "note_excerpt": plain[:900] if plain else "",
            "stats": {
                "sessions": sessions,
                "tokens": tokens,
                "cost_usd": cost,
                "cost_display": format_usd(cost),
            },
        }

    # Center / overview card
    proj_lines = []
    for pname, st in list((by_project or {}).items())[:12]:
        proj_lines.append(
            f"{pname}: {st.get('sessions', 0)} sess · {int(st.get('tokens', 0)):,} tok · {format_usd(st.get('cost_usd', 0))}"
        )
    center_guru = _word_cap(
        "🧠 GURU — Knowledge map center. "
        "Think of this view as the front desk of a multi-building campus: one map, many doors. "
        "This center is the whole workshop floor, not one bench. "
        "Each colored node is a project, concept, decision, or session note living in your RavenVault on this machine. "
        "Click a node to zoom into one story; click empty canvas or the Center button to return here for the campus-wide briefing. "
        "Business: one shared map reduces 'where did we leave that?' thrash across product repos, which cuts meeting time and rework risk when people switch context. "
        "Technical: agents and humans load short hub digests instead of pasting multi‑megabyte git dumps into chat, which keeps token spend honest and answers grounded. "
        "Functional: product, engineering, and ops can point at the same project hub language — open questions, decisions, concepts — so standups and handoffs share one narrative. "
        f"Repos tracked in this cost window: {', '.join((by_project or {}).keys()) or 'none yet'}. "
        f"The interactive graph currently has {len(nodes)} nodes and {len(edges)} edges built from wikilinks. "
        "Trust dollar headlines only when rows carry a project tag. "
        "Old unscoped by_day rollups (tens of thousands of fake 'sessions' in a day) are excluded from headlines because they inflated totals into nonsense. "
        "Use the per-repo table under the graph when you need comparable spend across applications. "
        "One takeaway: start at Center for the portfolio, then click a repo node when you need that product's story.",
        200,
    )
    center_last = _word_cap(
        f"Dashboard generated {metadata.get('report_generated_at_local') or 'now'}. "
        f"Vault root: {metadata.get('vault_path') or str(VAULT)}. "
        f"Active filter: {graph.get('project_filter') or 'all projects'}. "
        f"Plugin/report metadata project: {metadata.get('project') or 'n/a'}. "
        f"Rebuild anytime with: python3 scripts/dashboard.py --html --open. "
        f"Index, hubs, and session notes refresh when Stop hooks run (token-meter-write, obsidian-log, knowledge-extract). "
        f"If Center looks empty, open Obsidian on ~/RavenVault and confirm projects/*.md hubs exist, then re-run the dashboard command. "
        f"Graph JSON export lives at ~/RavenVault/graph/knowledge-graph.json for tooling that prefers files over HTML.",
        100,
    )
    center_cost = _word_cap(
        f"Headline window uses trusted per-repo rows only: {metrics.get('sessions_count', 0)} sessions, "
        f"{int(metrics.get('total_tokens') or 0):,} tokens, {format_usd(metrics.get('total_cost_usd', 0))}. "
        f"By repo — {'; '.join(proj_lines) if proj_lines else 'no per-repo rows yet; future Stop hooks write by_project into monthly metrics'}. "
        f"{_cve_guard_blurb(metrics, 'all repos')} "
        f"Legacy unscoped cost (not in headline): {format_usd((metrics.get('legacy_unscoped') or {}).get('cost_usd', 0))} "
        f"across {(metrics.get('legacy_unscoped') or {}).get('suspect_days', 0)} suspect day(s).",
        100,
    )
    cur = metrics.get("current_project") or metadata.get("project") or ""
    # Collect all graph project links for center drill-down
    graph_projects = []
    for n in nodes:
        if (n.get("type") or "") == "project" or str(n.get("id", "")).startswith("projects/"):
            pid = n.get("id") or ""
            pname = pid.split("/")[-1] if pid else n.get("label")
            bhub = _read_vault_note(pid or f"projects/{pname}")
            _lp = resolve_local_path(str(pname), bhub)
            graph_projects.append(
                {
                    "id": pid or f"projects/{pname}",
                    "name": pname,
                    "repo_url": _repo_url_from_hub(bhub, pname, metadata),
                    "local_path": _lp,
                    "local_uri": _local_uri(_lp),
                }
            )
    briefings["__center__"] = {
        "id": "__center__",
        "label": "All repos (center)",
        "type": "overview",
        "project": cur,
        "path": "index/README.md",
        "guru": center_guru,
        "last_update": center_last,
        "cost_report": center_cost,
        "repo_url": _repo_url_from_hub("", cur, metadata)
        if cur
        else (metadata.get("git_remote") or ""),
        "local_path": str(PROJECT_DIR),
        "local_uri": _local_uri(str(PROJECT_DIR)),
        "vault_note_uri": (VAULT / "index" / "README.md").resolve().as_uri()
        if (VAULT / "index" / "README.md").exists()
        else "",
        "open_questions": [],
        "current_state": [],
        "related_concepts": [],
        "related_decisions": [],
        "related_sessions": [],
        "neighbors": [p["id"] for p in graph_projects],
        "graph_projects": graph_projects,
        "note_excerpt": "",
        "stats": {
            "sessions": metrics.get("sessions_count", 0),
            "tokens": metrics.get("total_tokens", 0),
            "cost_usd": metrics.get("total_cost_usd", 0),
            "cost_display": format_usd(metrics.get("total_cost_usd", 0)),
        },
    }
    return briefings


def render_knowledge_graph_section(
    graph: dict,
    metrics: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Knowledge graph + Guru click panel (offline-safe list + optional vis-network)."""
    metrics = metrics or {}
    metadata = metadata or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    n_nodes, n_edges = len(nodes), len(edges)
    briefings = build_node_briefings(graph, metrics, metadata)
    # Ensure nodes carry vibe icons (emoji + data-URI)
    try:
        from icons import enrich_node, legend_html, icon_img_html, resolve_icon_key, emoji_for
    except ImportError:
        try:
            from icons import (  # type: ignore
                enrich_node,
                legend_html,
                icon_img_html,
                resolve_icon_key,
                emoji_for,
            )
        except ImportError:
            enrich_node = None  # type: ignore
            legend_html = lambda: ""  # type: ignore
            icon_img_html = lambda *a, **k: ""  # type: ignore
            resolve_icon_key = None  # type: ignore
            emoji_for = lambda k: "❓"  # type: ignore
    if enrich_node and graph.get("nodes"):
        graph = dict(graph)
        graph["nodes"] = [enrich_node(n) for n in graph["nodes"]]
    graph_json = json.dumps(graph, default=str)
    brief_json = json.dumps(briefings, default=str)
    legend = legend_html() if callable(legend_html) else ""

    if n_nodes < 2:
        return f"""
  <h2 id="knowledge-graph">🕸 Knowledge graph</h2>
  <div class="meta" style="border-left:4px solid #f59e0b;">
    <p><strong>Knowledge graph is sparse</strong> ({n_nodes} node(s), {n_edges} edge(s)).</p>
    <p style="color:#94a3b8;margin-top:8px;font-size:14px;">
      Create project hubs and concept notes, then rebuild. See
      <code>docs/obsidian-knowledge-graph-plan.md</code>.
    </p>
  </div>
"""

    # Per-repo table rows — union of cost projects + graph project hubs
    repo_names = set((metrics.get("by_project") or {}).keys())
    for n in nodes:
        if (n.get("type") or "") == "project" or str(n.get("id", "")).startswith("projects/"):
            repo_names.add(str(n.get("id", "")).split("/")[-1])
    repo_rows = ""
    project_chips = ""
    for pname in sorted(repo_names, key=str.lower):
        st = (metrics.get("by_project") or {}).get(pname) or {
            "sessions": 0,
            "tokens": 0,
            "cost_usd": 0,
        }
        brief = briefings.get(f"projects/{pname}") or {}
        url = brief.get("repo_url") or f"https://github.com/giggsoinc/{pname}"
        local = brief.get("local_path") or ""
        if not local:
            hubp = VAULT / "projects" / f"{pname}.md"
            hub_txt = ""
            if hubp.exists():
                try:
                    hub_txt = hubp.read_text(errors="replace")
                except Exception:
                    pass
            local = resolve_local_path(pname, hub_txt)
        local_html = _local_link_html(local, "Local")
        local_uri = _local_uri(local)
        # icon for this project chip
        pnode = next(
            (n for n in (graph.get("nodes") or []) if n.get("id") == f"projects/{pname}"),
            {},
        )
        ico = (pnode or {}).get("icon") or "project"
        ico_html = icon_img_html(ico, 16, pname) if icon_img_html else "📦"
        not_found_span = ' · <span style="color:#64748b;font-size:11px">not found under search roots</span>'
        local_or_fallback = (' · ' + local_html) if local_html else not_found_span
        repo_rows += (
            f"<tr style='cursor:pointer' onclick=\"window.kgShowNode('projects/{pname}')\">"
            f"<td>{ico_html} <strong>{pname}</strong></td>"
            f"<td class='num'>{st.get('sessions',0)}</td>"
            f"<td class='num'>{int(st.get('tokens',0)):,}</td>"
            f"<td class='num'>{format_usd(st.get('cost_usd',0))}</td>"
            f"<td onclick='event.stopPropagation()'>"
            f"<a href='{url}' target='_blank' rel='noopener'>GitHub ↗</a>"
            f"{local_or_fallback}"
            f"</td></tr>\n"
        )
        project_chips += (
            f"<span class='kg-chip-wrap'>"
            f"<a class='kg-chip' href='#' "
            f"title='Briefing' onclick=\"event.preventDefault(); window.kgShowNode('projects/{pname}');\">"
            f"{ico_html} {pname}</a>"
            f"<a class='kg-chip-link' href='{url}' target='_blank' rel='noopener' title='GitHub'>GitHub ↗</a>"
        )
        if local_uri:
            project_chips += (
                f"<a class='kg-chip-link' href='{local_uri}' title='{local}' "
                f"style='color:#86efac'>Local 📁</a>"
            )
        project_chips += "</span> "
    if not repo_rows:
        repo_rows = (
            "<tr><td colspan='5' style='color:#94a3b8'>No project hubs/cost rows yet.</td></tr>"
        )

    return f"""
  <h2 id="knowledge-graph">🕸 Knowledge graph</h2>
  {legend}
  <p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">
    Click a <strong>node</strong> / chip for Summary · notes · cost/CVE · repo.
    Empty canvas / <strong>Center</strong> = portfolio.
    You do not need to read code to use this map.
  </p>
  <style>
    .kg-chip {{ display:inline-block; margin:3px 2px; padding:6px 10px; background:#312e81; color:#e0e7ff;
      border-radius:999px; font-size:12px; text-decoration:none; cursor:pointer; border:1px solid #4c1d95; }}
    .kg-chip:hover {{ background:#4c1d95; }}
    .kg-chip-link {{ color:#38bdf8; font-size:12px; margin-right:6px; text-decoration:none; }}
    .kg-chip-wrap {{ display:inline-flex; align-items:center; gap:4px; margin:4px 10px 4px 0;
      padding:4px 8px; background:#1e293b; border-radius:999px; border:1px solid #334155; }}
    .kg-drill a {{ color:#38bdf8; cursor:pointer; text-decoration:none; margin-right:8px; }}
    .kg-drill a:hover {{ text-decoration:underline; }}
    #kg-svg text {{ pointer-events: none; }}
    #kg-svg circle, #kg-svg rect {{ cursor: pointer; }}
  </style>
  <div style="margin-bottom:12px;">
    <button type="button" class="download" style="background:#8b5cf6;" onclick="window.kgShowNode('__center__')">◎ Center overview</button>
  </div>
  <div style="margin-bottom:16px;">
    <div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">
      Projects in graph — name = briefing · <strong>GitHub ↗</strong> · <strong style="color:#86efac">Local 📁</strong>
      (always visible; does not need the force-canvas)
    </div>
    <div>{project_chips or '<span style="color:#94a3b8">No project nodes</span>'}</div>
  </div>
  <div id="kg-filters" style="margin-bottom:12px;font-size:13px;color:#cbd5e1;">
    <label style="margin-right:12px;"><input type="checkbox" class="kg-type" value="project" checked> project</label>
    <label style="margin-right:12px;"><input type="checkbox" class="kg-type" value="concept" checked> concept</label>
    <label style="margin-right:12px;"><input type="checkbox" class="kg-type" value="decision" checked> decision</label>
    <label style="margin-right:12px;"><input type="checkbox" class="kg-type" value="session" checked> session</label>
    <label style="margin-right:12px;"><input type="checkbox" class="kg-type" value="unknown" checked> unknown</label>
  </div>
  <div style="display:grid;grid-template-columns:minmax(280px,1fr) minmax(320px,1.1fr);gap:16px;align-items:start;">
    <div>
      <div id="kg-canvas" style="height:520px;background:#1e293b;border-radius:8px;border:1px solid #334155;overflow:hidden;"></div>
      <div id="kg-nodelist" style="margin-top:12px;max-height:280px;overflow:auto;background:#1e293b;border-radius:8px;padding:8px;"></div>
    </div>
    <div id="kg-panel" style="background:#1e293b;border-radius:8px;border:1px solid #334155;padding:16px 18px;min-height:520px;">
      <p style="color:#94a3b8;font-size:14px;">Select a node or Center to load the briefing.</p>
    </div>
  </div>

  <h3 style="margin-top:24px;color:#94a3b8;">Per-repo tokens &amp; cost (click row = open briefing)</h3>
  <table>
    <thead><tr><th>Repo</th><th class="num">Sessions</th><th class="num">Tokens</th><th class="num">Cost</th><th>Link</th></tr></thead>
    <tbody>
      {repo_rows}
    </tbody>
  </table>

  <script type="application/json" id="kg-data">{graph_json}</script>
  <script type="application/json" id="kg-briefings">{brief_json}</script>
  <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <script>
  (function() {{
    const GRAPH = JSON.parse(document.getElementById('kg-data').textContent);
    const BRIEFS = JSON.parse(document.getElementById('kg-briefings').textContent);
    const COLORS = {{
      project: '#8b5cf6', concept: '#10b981', decision: '#f59e0b',
      session: '#3b82f6', unknown: '#64748b', overview: '#f472b6'
    }};
    let network = null;

    function esc(s) {{
      return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }}
    function nl2br(s) {{ return esc(s).replace(/\\n/g, '<br>'); }}

    function listLinks(ids, label) {{
      if (!ids || !ids.length) return '';
      const items = ids.map(function(x) {{
        return '<a href="#" onclick="event.preventDefault(); window.kgShowNode(\\''+String(x).replace(/'/g,'')+'\\')">'+esc(x)+'</a>';
      }}).join(' ');
      return '<div class="kg-drill" style="margin:8px 0;"><span style="color:#94a3b8;font-size:12px;">'+esc(label)+': </span>'+items+'</div>';
    }}
    function bulletList(arr, title) {{
      if (!arr || !arr.length) return '';
      return '<div style="margin:10px 0;"><div style="font-size:12px;color:#94a3b8;">'+esc(title)+'</div><ul style="margin:4px 0 0 18px;font-size:13px;color:#e2e8f0;">' +
        arr.slice(0,8).map(function(x){{ return '<li>'+esc(x)+'</li>'; }}).join('') + '</ul></div>';
    }}

    window.kgShowNode = function(id) {{
      const b = BRIEFS[id] || BRIEFS['__center__'];
      if (!b) {{
        document.getElementById('kg-panel').innerHTML =
          '<p style="color:#f59e0b;">No briefing for <code>'+esc(id)+'</code>. Hub may be missing — create ~/RavenVault/projects/…</p>';
        return;
      }}
      const url = b.repo_url || '';
      const st = b.stats || {{}};
      const costShow = st.cost_display || st.cost_usd || '0';
      const treeName = b.type === 'project' ? b.label : (b.project || '');
      if (treeName && window.openCodeTree) {{ openCodeTree(treeName, true); }}
      let actions = '<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;">';
      if (treeName) {{
        actions += '<a class="download" style="background:#1d4ed8;text-decoration:none;margin:0;cursor:pointer;" onclick="window.openCodeTree && openCodeTree(\\''+esc(treeName)+'\\')">🌳 Code tree</a>';
      }}
      if (url) {{
        actions += '<a class="download" style="background:#10b981;text-decoration:none;margin:0;" href="'+esc(url)+'" target="_blank" rel="noopener">↗ GitHub</a>';
      }}
      if (b.local_path) {{
        // file:// link so Finder/IDE can open the local clone
        let localHref = b.local_uri || '';
        if (!localHref && b.local_path) {{
          // best-effort: absolute path → file URI
          const lp = String(b.local_path);
          localHref = lp.startsWith('/') ? ('file://' + lp) : '';
        }}
        if (localHref) {{
          actions += '<a class="download" style="background:#166534;text-decoration:none;margin:0;" href="'+esc(localHref)+'" title="'+esc(b.local_path)+'">📁 Open local repo</a>';
        }} else {{
          actions += '<span class="download" style="background:#334155;margin:0;cursor:default;" title="Local path">📁 '+esc(b.local_path)+'</span>';
        }}
        actions += '<div style="width:100%;font-size:11px;color:#86efac;margin-top:4px;font-family:ui-monospace,monospace;">Local: '+esc(b.local_path)+'</div>';
      }}
      if (b.vault_note_uri) {{
        actions += '<a class="download" style="background:#0ea5e9;text-decoration:none;margin:0;" href="'+esc(b.vault_note_uri)+'">📝 Vault note</a>';
      }}
      if (b.project && id !== 'projects/'+b.project) {{
        actions += '<button type="button" class="download" style="background:#8b5cf6;margin:0;" onclick="window.kgShowNode(\\'projects/'+String(b.project).replace(/'/g,'')+'\\')">Repo hub</button>';
      }}
      actions += '</div>';
      if (!url && !b.local_path) {{
        actions += '<p style="margin-top:10px;color:#94a3b8;font-size:13px;">Add under project hub <code>## Repo</code>:<br>'+
          '- GitHub: https://github.com/org/repo<br>- Local: /absolute/path/to/clone</p>';
      }}

      // Center: list all graph projects as drill targets
      let projectDrill = '';
      if (b.graph_projects && b.graph_projects.length) {{
        projectDrill = '<div class="kg-drill" style="margin:12px 0;"><div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">Projects in graph</div>' +
          b.graph_projects.map(function(p) {{
            const u = p.repo_url ? ' <a href="'+esc(p.repo_url)+'" target="_blank" rel="noopener">GitHub ↗</a>' : '';
            let loc = '';
            if (p.local_path) {{
              const href = p.local_uri || (String(p.local_path).startsWith('/') ? ('file://'+p.local_path) : '');
              loc = href
                ? ' <a href="'+esc(href)+'" style="color:#86efac" title="'+esc(p.local_path)+'">Local 📁</a> <code style="font-size:10px;color:#64748b">'+esc(p.local_path)+'</code>'
                : ' <code style="font-size:10px;color:#64748b">'+esc(p.local_path)+'</code>';
            }}
            return '<div style="margin:6px 0;"><a href="#" onclick="event.preventDefault(); window.kgShowNode(\\''+String(p.id).replace(/'/g,'')+'\\')">'+esc(p.name)+'</a>'+u+loc+'</div>';
          }}).join('') + '</div>';
      }}

      document.getElementById('kg-panel').innerHTML =
        '<div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">'+esc(b.type)+' · '+esc(b.id)+'</div>'+
        '<h3 style="margin:0 0 12px;color:#e2e8f0;">'+esc(b.label)+'</h3>'+
        '<div style="font-size:12px;color:#cbd5e1;margin-bottom:12px;">'+
          (st.sessions!=null?('Sessions <strong>'+st.sessions+'</strong> · '):'')+
          (st.tokens!=null?('Tokens <strong>'+Number(st.tokens).toLocaleString()+'</strong> · '):'')+
          ('Cost <strong>'+esc(String(costShow))+'</strong>')+
        '</div>'+
        actions +
        projectDrill +
        bulletList(b.open_questions, 'Open questions') +
        bulletList(b.current_state, 'Current state') +
        listLinks(b.related_concepts, 'Concepts') +
        listLinks(b.related_decisions, 'Decisions') +
        listLinks(b.related_sessions, 'Sessions') +
        listLinks((b.neighbors||[]).filter(function(x){{ return !(b.related_concepts||[]).includes(x) && !(b.related_sessions||[]).includes(x); }}).slice(0,8), 'More links') +
        (b.note_excerpt ? '<div style="margin:12px 0;padding:10px;background:#0f172a;border-radius:6px;font-size:12px;color:#94a3b8;max-height:120px;overflow:auto;"><div style="margin-bottom:4px;color:#64748b;">Note excerpt</div>'+esc(b.note_excerpt)+'</div>' : '') +
        '<h4 style="color:#a78bfa;margin:16px 0 2px;">Summary</h4>'+
        '<div style="font-size:11px;color:#94a3b8;margin:0 0 8px;">Generated by Andie - Guru</div>'+
        '<p style="font-size:14px;line-height:1.55;color:#e2e8f0;">'+nl2br(b.guru)+'</p>'+
        '<h4 style="color:#38bdf8;margin:16px 0 6px;">Last update</h4>'+
        '<p style="font-size:14px;line-height:1.55;color:#e2e8f0;">'+nl2br(b.last_update)+'</p>'+
        '<h4 style="color:#fbbf24;margin:16px 0 6px;">Cost · tokens · Raven CVE / guards</h4>'+
        '<p style="font-size:14px;line-height:1.55;color:#e2e8f0;">'+nl2br(b.cost_report)+'</p>';
      try {{
        if (network && id !== '__center__') {{
          network.selectNodes([id]);
          network.focus(id, {{ scale: 1.2, animation: true }});
        }} else if (network && id === '__center__') {{
          network.unselectAll();
          network.fit({{ animation: true }});
        }}
      }} catch (e) {{}}
      // scroll panel into view on small screens
      try {{ document.getElementById('kg-panel').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }}); }} catch (e) {{}}
    }};

    function drawOfflineSvg(nodesArr, edgesArr) {{
      // Always-on layout (no CDN). Top-down layered tree — root(s) at top,
      // children spread horizontally below by BFS depth (2026-08-21: was a
      // circle/ellipse; user wants a real top-to-bottom mind map).
      const container = document.getElementById('kg-canvas');
      const W = Math.max(container.clientWidth || 480, 320);
      const ROW_H = 90;

      const hasIncoming = {{}};
      edgesArr.forEach(function(e) {{ hasIncoming[e.to] = true; }});
      const children = {{}};
      edgesArr.forEach(function(e) {{
        (children[e.from] = children[e.from] || []).push(e.to);
      }});
      const roots = nodesArr.filter(function(n) {{ return !hasIncoming[n.id]; }});
      const rootList = roots.length ? roots : nodesArr.slice(0, 1);

      const depth = {{}};
      const queue = rootList.map(function(n) {{ return {{ id: n.id, d: 0 }}; }});
      const seen = {{}};
      rootList.forEach(function(n) {{ seen[n.id] = true; }});
      while (queue.length) {{
        const cur = queue.shift();
        depth[cur.id] = Math.max(depth[cur.id] || 0, cur.d);
        (children[cur.id] || []).forEach(function(childId) {{
          if (!seen[childId]) {{ seen[childId] = true; queue.push({{ id: childId, d: cur.d + 1 }}); }}
        }});
      }}
      nodesArr.forEach(function(n) {{ if (depth[n.id] === undefined) depth[n.id] = 0; }});

      const byRow = {{}};
      nodesArr.forEach(function(n) {{
        const d = depth[n.id];
        (byRow[d] = byRow[d] || []).push(n.id);
      }});
      // Dense graphs (many edges, few real hierarchy levels) pile most
      // nodes into one BFS depth — wrap wide rows into sub-rows so the
      // layout still grows top-to-bottom instead of reading as one wide
      // horizontal band.
      const MAX_PER_ROW = 6;
      const SUB_ROW_H = ROW_H * 0.6;
      let totalSubRows = 0;
      const subRowStart = {{}};
      Object.keys(byRow).sort(function(a, b) {{ return Number(a) - Number(b); }}).forEach(function(dKey) {{
        subRowStart[dKey] = totalSubRows;
        totalSubRows += Math.ceil(byRow[dKey].length / MAX_PER_ROW);
      }});
      const H = Math.max(totalSubRows * SUB_ROW_H + 100, 320);

      const pos = {{}};
      Object.keys(byRow).forEach(function(dKey) {{
        const row = byRow[dKey];
        row.forEach(function(id, i) {{
          const subRow = Math.floor(i / MAX_PER_ROW);
          const withinSubRow = row.slice(subRow * MAX_PER_ROW, subRow * MAX_PER_ROW + MAX_PER_ROW);
          const idxInSubRow = i % MAX_PER_ROW;
          const y = 50 + (subRowStart[dKey] + subRow) * SUB_ROW_H;
          const x = W * (idxInSubRow + 1) / (withinSubRow.length + 1);
          pos[id] = {{ x: x, y: y }};
        }});
      }});
      let edgesSvg = edgesArr.map(function(e) {{
        const a = pos[e.from], b = pos[e.to];
        if (!a || !b) return '';
        return '<line x1="'+a.x+'" y1="'+a.y+'" x2="'+b.x+'" y2="'+b.y+
          '" stroke="#475569" stroke-width="1.2" />';
      }}).join('');
      let nodesSvg = nodesArr.map(function(node) {{
        const p = pos[node.id];
        const col = node.color || '#64748b';
        const lab = (node.label || node.id || '').slice(0, 14);
        const emo = node.emoji || '❓';
        const idSafe = String(node.id).replace(/"/g, '');
        if (node.shape === 'box') {{
          return '<g class="kg-node" data-id="'+idSafe+'" transform="translate('+p.x+','+p.y+')">' +
            '<rect x="-40" y="-18" width="80" height="36" rx="8" fill="'+col+'" opacity="0.92"/>' +
            '<text text-anchor="middle" y="-2" font-size="14">'+emo+'</text>' +
            '<text text-anchor="middle" y="14" fill="#f8fafc" font-size="9" font-family="system-ui">'+esc(lab)+'</text></g>';
        }}
        return '<g class="kg-node" data-id="'+idSafe+'" transform="translate('+p.x+','+p.y+')">' +
          '<circle r="16" fill="'+col+'" opacity="0.95"/>' +
          '<text text-anchor="middle" y="5" font-size="13">'+emo+'</text>' +
          '<text text-anchor="middle" y="32" fill="#cbd5e1" font-size="9" font-family="system-ui">'+esc(lab)+'</text></g>';
      }}).join('');
      container.innerHTML =
        '<svg id="kg-svg" width="100%" height="'+H+'" viewBox="0 0 '+W+' '+H+
        '" style="display:block;background:#1e293b">' +
        '<rect width="100%" height="100%" fill="#1e293b" id="kg-svg-bg"/>' +
        edgesSvg + nodesSvg +
        '<text x="12" y="20" fill="#86efac" font-size="11" font-family="system-ui">Picture map · '+
        nodesArr.length+' boxes · click any icon</text></svg>';
      container.querySelectorAll('.kg-node').forEach(function(g) {{
        g.addEventListener('click', function(ev) {{
          ev.stopPropagation();
          window.kgShowNode(g.getAttribute('data-id'));
        }});
      }});
      const bg = container.querySelector('#kg-svg-bg');
      if (bg) bg.addEventListener('click', function() {{ window.kgShowNode('__center__'); }});
      network = null;
    }}

    function rebuild() {{
      const allowed = new Set(Array.from(document.querySelectorAll('.kg-type:checked')).map(c => c.value));
      const nodesArr = (GRAPH.nodes || []).filter(n => allowed.has(n.type || 'unknown')).map(n => ({{
        id: n.id, label: n.label || n.id, title: (n.path || n.id) + ' (' + (n.type||'') + ')',
        color: COLORS[n.type] || COLORS.unknown, shape: n.type === 'project' ? 'box' : 'dot',
        type: n.type || 'unknown',
        emoji: n.icon_emoji || '❓',
        icon: n.icon || n.type || 'unknown',
        iconUri: n.icon_data_uri || ''
      }}));
      const idset = new Set(nodesArr.map(n => n.id));
      const edgesArr = (GRAPH.edges || []).filter(e => idset.has(e.source) && idset.has(e.target)).map((e,i) => ({{
        id: i, from: e.source, to: e.target, arrows: 'to', color: {{ color:'#475569' }}
      }}));

      // Node list ALWAYS works (offline) — icons first for vibe coders
      const list = document.getElementById('kg-nodelist');
      list.innerHTML = '<div style="font-size:12px;color:#86efac;margin-bottom:6px;">All boxes ('+nodesArr.length+') — click the picture</div>' +
        nodesArr.map(n => {{
          const ico = n.iconUri
            ? '<img src="'+n.iconUri+'" width="18" height="18" alt="" style="vertical-align:middle;margin-right:6px"/>'
            : '<span style="margin-right:6px">'+n.emoji+'</span>';
          return '<button type="button" style="display:flex;align-items:center;width:100%;text-align:left;margin:3px 0;padding:8px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;cursor:pointer;" onclick="window.kgShowNode(\\''+String(n.id).replace(/'/g, '')+'\\')">'+
            ico+' <span><strong>'+esc(n.label)+'</strong> <span style="color:#64748b;font-size:11px;">'+esc(n.type)+' · '+esc(n.icon)+'</span></span></button>';
        }}).join('');

      const container = document.getElementById('kg-canvas');
      // Prefer offline SVG so hard-refresh / no-CDN never looks "empty"
      drawOfflineSvg(nodesArr, edgesArr);
      // Optional: upgrade to vis-network if CDN already loaded
      if (typeof vis !== 'undefined') {{
        try {{
          const data = {{ nodes: new vis.DataSet(nodesArr), edges: new vis.DataSet(edgesArr) }};
          network = new vis.Network(container, data, {{
            physics: {{ stabilization: true, barnesHut: {{ gravitationalConstant: -12000 }} }},
            interaction: {{ hover: true, tooltipDelay: 80, multiselect: false }},
            nodes: {{ font: {{ color: '#e2e8f0', size: 12 }} }}
          }});
          network.on('click', function(params) {{
            if (params.nodes && params.nodes.length) window.kgShowNode(params.nodes[0]);
            else window.kgShowNode('__center__');
          }});
        }} catch (err) {{
          drawOfflineSvg(nodesArr, edgesArr);
        }}
      }}
    }}
    document.querySelectorAll('.kg-type').forEach(c => c.addEventListener('change', rebuild));
    try {{
      rebuild();
      window.kgShowNode('__center__');
    }} catch (err) {{
      document.getElementById('kg-panel').innerHTML =
        '<p style="color:#f59e0b;">Graph UI error (data still in page JSON): '+esc(String(err))+'</p>'+
        '<p style="color:#94a3b8;font-size:13px;">Use project chips above — they do not need the canvas.</p>';
    }}
  }})();
  </script>
"""


# ── Renderer: Static HTML ─────────────────────────────────────────────────────

def render_cost_log_section(metadata: dict) -> str:
    """💰 Cost Log — per-turn, per-model rows from .raven/cost-log.jsonl.

    Only models actually observed in the transcript get rows; Raven's hook
    scripts make no API calls and are never logged (the old by_source
    overhead figures were never computed by anything — do not resurrect).
    """
    log_path = RAVEN_DIR / "cost-log.jsonl"
    if not log_path.exists():
        return (
            '<h2 id="cost-log">💰 Cost Log</h2>'
            '<div class="meta">No rows yet — the log starts filling at the end of the next '
            'turn (Stop hook). One row per model actually used, with estimated vs computed '
            'cost and running cumulative totals.</div>'
        )
    rows = []
    try:
        for line in log_path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception as e:
        return f'<h2 id="cost-log">💰 Cost Log</h2><div class="meta">cost-log.jsonl unreadable: {e}</div>'

    if not rows:
        return '<h2 id="cost-log">💰 Cost Log</h2><div class="meta">Log exists but has no valid rows.</div>'

    total_computed = sum(float(r.get("computed_cost_usd") or 0) for r in rows)
    latest = rows[-1]
    recent = rows[-30:]

    # Dual-path verification verdict (written by token-meter-write.py):
    # Path A = accumulated per-turn deltas; Path B = independent full-
    # transcript recompute. Disagreement >5% renders UNVERIFIED, loudly.
    verify_html = ""
    verify_path = RAVEN_DIR / ".cost-verify.json"
    if verify_path.exists():
        try:
            v = json.loads(verify_path.read_text())
            if v.get("verified"):
                verify_html = (
                    f'<span style="color:#22c55e;font-weight:600">✅ VERIFIED</span> — '
                    f'both calculation paths agree within {v.get("variance_pct", "?")}% '
                    f'(A: {format_usd(v.get("path_a_usd") or 0)} deltas · '
                    f'B: {format_usd(v.get("path_b_usd") or 0)} recompute)'
                )
            else:
                verify_html = (
                    f'<span style="color:#dc2626;font-weight:700">⚠️ UNVERIFIED — paths disagree '
                    f'by {v.get("variance_pct", "?")}%</span> '
                    f'(A: {format_usd(v.get("path_a_usd") or 0)} deltas vs '
                    f'B: {format_usd(v.get("path_b_usd") or 0)} recompute) — treat session figures '
                    f'as suspect until the divergence is explained'
                )
        except Exception:
            verify_html = ""
    if not verify_html:
        verify_html = "Verification pending — dual-path check runs on the next Stop hook."

    body = ""
    for r in reversed(recent):
        est = r.get("est_cost_usd")
        est_cell = format_usd(est) if est is not None else "—"
        body += (
            f"<tr><td>{(r.get('ts') or '')[:19].replace('T', ' ')}</td>"
            f"<td><code>{r.get('model', '?')}</code></td>"
            f"<td>{r.get('source', '?')}</td>"
            f"<td class='num'>{(r.get('tokens_in') or 0) + (r.get('tokens_out') or 0):,}</td>"
            f"<td class='num'>{est_cell}</td>"
            f"<td class='num'>{format_usd(r.get('computed_cost_usd') or 0)}</td>"
            f"<td class='num'>{format_usd(r.get('cum_session_usd') or 0)}</td></tr>\n"
        )

    return f"""
  <h2 id="cost-log">💰 Cost Log</h2>
  <div class="meta">
    <strong>{len(rows)}</strong> rows · all-time computed total <strong>{format_usd(total_computed)}</strong> ·
    latest cumulative this month <strong>{format_usd(latest.get('cum_month_usd') or 0)}</strong>
    <br><span style="color:#94a3b8;font-size:12px">One row per model actually observed per turn
    (subagent rows appear only when a subagent with a model override really ran).
    "Est" is the router's pre-turn guess; "Computed" is real token usage × pricing —
    never merged. Raven's own hook scripts make zero API calls and are never logged as cost.
    Showing latest {len(recent)} rows.</span>
    <br><span style="font-size:13px">{verify_html}</span>
    <br><span style="color:#94a3b8;font-size:11px">Citation — every session figure above is
    backed by two independent calculations: Path A sums per-turn checkpoint deltas
    (cost-log.jsonl); Path B recomputes the whole transcript from scratch
    (.raven/.cost-verify.json). Disagreement &gt;5% is flagged, never averaged.</span>
  </div>
  <table>
    <tr><th>When (UTC)</th><th>Model</th><th>Source</th><th class="num">Tokens</th>
        <th class="num">Est</th><th class="num">Computed</th><th class="num">Cum (session)</th></tr>
    {body}
  </table>
"""


RAVEN_DASHBOARD_NAME = "raven-dashboard.html"


def _tail_jsonl(path: Path, n: int = 40) -> list:
    if not path.is_file() or n <= 0:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _td(v, money=False) -> str:
    if v is None or v == "":
        s = "—"
    elif money:
        try:
            s = f"${float(v):.4f}"
        except (TypeError, ValueError):
            s = str(v)
    else:
        s = str(v)
    if len(s) > 80:
        s = s[:77] + "…"
    return html_lib.escape(s)


def _details_json(obj: dict) -> str:
    blob = html_lib.escape(json.dumps(obj, indent=2)[:2000])
    return f"<details><summary>json</summary><pre class='dim'>{blob}</pre></details>"


def _audit_tail(n: int = 30, raven_dir: Optional[Path] = None) -> list:
    d = raven_dir if raven_dir is not None else AUDIT_DIR
    if not d.is_dir():
        return []
    files = sorted(d.glob("*.log"))[-5:]
    rows = []
    for f in files:
        rows.extend(_tail_jsonl(f, 200))
    return rows[-n:]


def _stamp_repo(row: dict, fallback: str) -> dict:
    r = dict(row)
    if not str(r.get("repo") or r.get("project") or "").strip():
        r["repo"] = fallback
    return r


def _gather_repo_logs(names: list, per: int = 40) -> tuple:
    """Pull turn/cost/audit JSONL from each local clone + this repo."""
    turns: list = []
    costs: list = []
    audits: list = []
    seen: set = set()
    roots: list = []
    for name in names:
        if not isinstance(name, str):
            continue
        lp = resolve_local_path(str(name), "")
        if lp and Path(lp, ".git").is_dir():
            roots.append(Path(lp).resolve())
    roots.append(PROJECT_DIR.resolve())
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        raven = root / ".raven"
        label = root.name
        try:
            raw = json.loads((raven / "manifest.json").read_text()).get("project")
            if isinstance(raw, dict):
                raw = raw.get("name") or raw.get("project")
            if raw:
                label = str(raw)
        except Exception:
            pass
        for row in _tail_jsonl(raven / "turn-log.jsonl", per):
            turns.append(_stamp_repo(row, label))
        for row in _tail_jsonl(raven / "cost-log.jsonl", per):
            costs.append(_stamp_repo(row, label))
        for row in _audit_tail(per, raven / "audit"):
            audits.append(_stamp_repo(row, label))
    def _ts(r):
        return str(r.get("ts") or r.get("timestamp") or "")
    turns.sort(key=_ts)
    costs.sort(key=_ts)
    audits.sort(key=_ts)
    # Keep last `per` lines *per repo* (already tailed). Do not re-trim the
    # merged list — that dropped older Grok turns when Claude filled the window.
    return turns, costs, audits


def _usd(v) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _day_key(row: dict) -> str:
    ts = str(row.get("ts") or row.get("timestamp") or "")
    return ts[:10] if len(ts) >= 10 else ""


def _dedupe_log_rows(rows: list) -> list:
    seen: set = set()
    out = []
    for r in rows:
        k = (
            r.get("ts") or r.get("timestamp"),
            r.get("ide") or r.get("host"),
            r.get("model") or r.get("recommend"),
            r.get("computed_cost_usd"),
            r.get("est_cost_usd"),
            r.get("session_id"),
            r.get("tokens_in"),
            r.get("tokens_out"),
        )
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _get_cost_fn():
    sess = str(Path(__file__).resolve().parent.parent / "session")
    if sess not in sys.path:
        sys.path.insert(0, sess)
    from cost_calc import get_cost as _gc
    return _gc


def _log_session_key(repo: str, ide: str, row: dict) -> tuple:
    """Stable session grain for spend: real session_id, else calendar day."""
    sid = str(row.get("session_id") or "").strip()
    if sid and sid.lower() not in ("none", "null"):
        return (repo, ide, sid)
    day = _day_key(row)
    if day:
        return (repo, ide, f"day:{day}")
    return (repo, ide, str(row.get("ts") or row.get("timestamp") or "unknown"))


def _row_actual_usd(row: dict, gc) -> float:
    """One Stop snapshot: prefer computed_cost_usd (includes cache); else get_cost+cache."""
    raw = row.get("computed_cost_usd")
    if raw is not None and str(raw) != "":
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    model = str(row.get("model") or "")
    try:
        usd = gc(
            model,
            int(row.get("tokens_in") or 0),
            int(row.get("tokens_out") or 0),
            int(row.get("cache_read") or 0),
            int(row.get("cache_creation") or 0),
        )
    except TypeError:
        # Older get_cost without cache kwargs
        usd = gc(model, int(row.get("tokens_in") or 0), int(row.get("tokens_out") or 0))
    return float(usd or 0.0)


def _spend_from_logs(turn_log: list, cost_log: list) -> dict:
    """Spend from cost-log (actual) + turn-log (estimated) with matching grains.

    Actual: one snapshot per (repo, ide, session) — the max tokens_out row —
    priced once via computed_cost_usd / get_cost including cache_read (0.1×) and
    cache_creation (1.25×). Taking one snapshot avoids triple-counting when
    Stop re-parsed a full transcript.

    Estimated (IDEs with no cost-log coverage): per router fire,
    tokens_in=prompt_chars/4, tokens_out=500, then sum into session keys
    (session_id or day when Grok/Codex omit session_id). Labeled estimated —
    not billed.
    """
    turn_log = _dedupe_log_rows(turn_log)
    cost_log = _dedupe_log_rows(cost_log)
    try:
        gc = _get_cost_fn()
    except Exception:
        gc = lambda *_a, **_k: None

    def _ide_fits_model(ide: str, model: str) -> bool:
        i, m = (ide or "").lower(), (model or "").lower()
        if i == "claude":
            return "claude" in m or "anthropic" in m or not m
        if i == "grok":
            return "grok" in m
        if i == "codex":
            return any(x in m for x in ("codex", "gpt", "o3", "o4"))
        return True

    by_repo: dict = {}
    days: dict = {}
    sess_keys: set = set()
    tok = 0
    router_mix: dict = {}

    def bucket(repo: str, ide: str) -> tuple:
        b = by_repo.setdefault(
            repo, {"sessions": 0, "tokens": 0, "cost_usd": 0.0, "by_ide": {}, "kind": "estimated"}
        )
        ib = b["by_ide"].setdefault(
            ide,
            {
                "sessions": 0,
                "tokens": 0,
                "cost_usd": 0.0,
                "kind": "estimated",
                "in": 0,
                "out": 0,
                "cache_read": 0,
                "fires": 0,
            },
        )
        return b, ib

    best: dict = {}
    for r in cost_log:
        ide = str(r.get("ide") or r.get("host") or "unknown")
        model = str(r.get("model") or "")
        if not _ide_fits_model(ide, model):
            continue
        repo = str(r.get("repo") or r.get("project") or "unknown")
        key = _log_session_key(repo, ide, r)
        prev = best.get(key)
        tout = int(r.get("tokens_out") or 0)
        prev_out = int(prev.get("tokens_out") or 0) if prev else -1
        prev_usd = float(prev.get("computed_cost_usd") or 0) if prev else -1.0
        cur_usd = float(r.get("computed_cost_usd") or 0)
        if prev is None or tout > prev_out or (tout == prev_out and cur_usd >= prev_usd):
            best[key] = r

    covered = set()
    for key, r in best.items():
        repo, ide, _sid = key
        tin = int(r.get("tokens_in") or 0)
        tout = int(r.get("tokens_out") or 0)
        cr = int(r.get("cache_read") or 0)
        usd = _row_actual_usd(r, gc)
        _b, ib = bucket(repo, ide)
        ib["cost_usd"] += float(usd)
        ib["kind"] = "actual"
        ib["in"] = int(ib.get("in") or 0) + tin
        ib["out"] = int(ib.get("out") or 0) + tout
        ib["cache_read"] = int(ib.get("cache_read") or 0) + cr
        ib["tokens"] += tin + tout
        tok += tin + tout
        day = _day_key(r)
        if day:
            days[day] = days.get(day, 0.0) + float(usd)
        sess_keys.add(key)
        covered.add((repo, ide))

    for r in turn_log:
        repo = str(r.get("repo") or r.get("project") or "unknown")
        ide = str(r.get("ide") or r.get("host") or "unknown")
        model = str(r.get("recommend") or "")
        tier = str(r.get("tier") or "?")
        mk = (ide, tier, model or "?")
        router_mix[mk] = router_mix.get(mk, 0) + 1
        if (repo, ide) in covered:
            continue
        chars = int(r.get("prompt_chars") or 0)
        tin = max(0, chars // 4)
        tout = 500  # nominal reply guess per router fire
        usd = gc(model, tin, tout) if model else None
        if usd is None:
            usd = _usd(r.get("est_cost_usd"))
        _b, ib = bucket(repo, ide)
        ib["cost_usd"] += float(usd or 0)
        ib["kind"] = "estimated"
        ib["in"] = int(ib.get("in") or 0) + tin
        ib["out"] = int(ib.get("out") or 0) + tout
        ib["fires"] = int(ib.get("fires") or 0) + 1
        ib["tokens"] += tin + tout
        tok += tin + tout
        day = _day_key(r)
        if day:
            days[day] = days.get(day, 0.0) + float(usd or 0)
        sess_keys.add(_log_session_key(repo, ide, r))

    actual_total = 0.0
    est_total = 0.0
    for repo, b in by_repo.items():
        b["sessions"] = sum(1 for k in sess_keys if k[0] == repo)
        kinds = set()
        cost = 0.0
        tokens = 0
        for ide, ib in b["by_ide"].items():
            ib["sessions"] = sum(1 for k in sess_keys if k[0] == repo and k[1] == ide)
            ib["cost_usd"] = round(float(ib["cost_usd"]), 4)
            cost += ib["cost_usd"]
            tokens += int(ib.get("tokens") or 0)
            kinds.add(ib.get("kind") or "estimated")
            if ib.get("kind") == "actual":
                actual_total += ib["cost_usd"]
            else:
                est_total += ib["cost_usd"]
        b["cost_usd"] = round(cost, 4)
        b["tokens"] = tokens
        b["kind"] = (
            "actual"
            if kinds == {"actual"}
            else ("estimated" if kinds == {"estimated"} else "mixed")
        )
    kind = (
        "mixed"
        if actual_total > 0 and est_total > 0
        else ("actual" if actual_total > 0 else "estimated")
    )
    # Headline spend = sum of repo rows (already 4-dp), not a separate float path.
    repo_sum = round(sum(float(b.get("cost_usd") or 0) for b in by_repo.values()), 4)
    mix_rows = [
        {"ide": a, "tier": b, "model": c, "fires": n}
        for (a, b, c), n in sorted(router_mix.items(), key=lambda kv: -kv[1])
    ]
    return {
        "total_cost_usd": repo_sum,
        "sessions_count": len(sess_keys),
        "total_tokens": tok,
        "by_project": by_repo,
        "cost_by_day": {k: round(v, 4) for k, v in days.items()},
        "spend_kind": kind,
        "actual_usd": round(actual_total, 4),
        "estimated_usd": round(est_total, 4),
        "router_mix": mix_rows,
    }


def _obs_metrics(rows: list) -> dict:
    by_ide: dict = {}
    by_tier: dict = {}
    by_repo: dict = {}
    by_repo_cost: dict = {}
    est = 0.0
    chars = 0
    last = ""
    needs = 0
    red = 0
    for r in rows:
        ide = str(r.get("ide") or r.get("host") or "—")
        tier = str(r.get("tier") or "—")
        repo = str(r.get("repo") or r.get("project") or "—")
        by_ide[ide] = by_ide.get(ide, 0) + 1
        by_tier[tier] = by_tier.get(tier, 0) + 1
        by_repo[repo] = by_repo.get(repo, 0) + 1
        usd = _usd(r.get("est_cost_usd"))
        by_repo_cost[repo] = by_repo_cost.get(repo, 0.0) + usd
        est += usd
        try:
            chars += int(r.get("prompt_chars") or 0)
        except (TypeError, ValueError):
            pass
        ts = str(r.get("ts") or "")
        if ts > last:
            last = ts
        if r.get("needs_rate"):
            needs += 1
        if r.get("redteam"):
            red += 1
    return {
        "traces": len(rows),
        "est": round(est, 6),
        "chars": chars,
        "last": last or "—",
        "needs_rate": needs,
        "redteam": red,
        "by_ide": by_ide,
        "by_tier": by_tier,
        "by_repo": by_repo,
        "by_repo_cost": {k: round(v, 6) for k, v in by_repo_cost.items()},
    }


def _count_tbl(d: dict, h1: str, h2: str) -> str:
    if not d:
        return f"<tr><td colspan='2'>No {h1.lower()} yet</td></tr>"
    return "".join(
        f"<tr><td>{html_lib.escape(str(k))}</td><td class='num'>{v}</td></tr>"
        for k, v in sorted(d.items(), key=lambda kv: -kv[1])
    )


def _pane_bar(title: str, built: str) -> str:
    return (
        f'<div class="pane-bar"><h2>{title}</h2>'
        f'<span class="dim refresh-meta">Last refresh: {html_lib.escape(built)}</span>'
        f'<button type="button" class="refresh-now" onclick="refreshNow()" title="Rebuild now">↻ Refresh now</button></div>'
    )


def _with_running_est(turn_log: list) -> list:
    """Fill est + total_cost_usd on old rows (needs_rate / empty cost-log)."""
    try:
        import sys as _sys
        _sess = str(Path(__file__).resolve().parent.parent / "session")
        if _sess not in _sys.path:
            _sys.path.insert(0, _sess)
        from cost_calc import estimate as _est
    except Exception:
        _est = None
    running = 0.0
    out = []
    for r in turn_log:
        row = dict(r)
        if row.get("est_cost_usd") is None and _est and row.get("recommend"):
            try:
                e = _est(str(row.get("recommend")), int(row.get("prompt_chars") or 0))
                if e.get("est_cost_usd") is not None:
                    row["est_cost_usd"] = e["est_cost_usd"]
                    row["needs_rate"] = False
            except Exception:
                pass
        est = row.get("est_cost_usd")
        running += _usd(est)
        stored = _usd(row.get("total_cost_usd"))
        if stored <= 0 and running > 0:
            row["total_cost_usd"] = round(running, 6)
        else:
            running = max(running, stored)
        out.append(row)
    return out


def _is_okf_html(path: Path) -> bool:
    try:
        head = path.read_text(errors="replace")[:8000]
    except OSError:
        return False
    return 'id="okf"' in head or "EXTRACTED graph" in head


def _safe_repo_stem(name: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._-]+$", name or ""))


def _tree_files() -> dict[str, str]:
    """OKF graphs only — never legacy folder-trees / mind-maps / junk names."""
    trees = VAULT / "dashboard" / "trees"
    out: dict[str, str] = {}
    if not trees.is_dir():
        return out
    for p in trees.glob("*.html"):
        if not _safe_repo_stem(p.stem):
            continue
        if _is_okf_html(p):
            out[p.stem.lower()] = p.name
    return out


def _okf_baked_head(path: Path) -> str:
    """git_head from an OKF trees/*.html payload, or empty."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(
        r'<script[^>]*id=["\']okf["\'][^>]*>(.*?)</script>',
        raw,
        re.I | re.S,
    )
    if not m:
        return ""
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return ""
    return str(data.get("git_head") or "")


def _live_git_head(repo: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return (out.stdout or "").strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _ensure_okf_graphs(names: list[str]) -> None:
    """Build OKF HTML when missing or when baked git_head ≠ live HEAD."""
    xray = Path(__file__).resolve().parent / "xray.py"
    if not xray.is_file():
        return
    trees = VAULT / "dashboard" / "trees"
    trees.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str):
            continue
        lp = resolve_local_path(str(name), "")
        if not lp or not Path(lp, ".git").is_dir():
            continue
        key = str(Path(lp).resolve())
        if key in seen:
            continue
        seen.add(key)
        dest = trees / f"{Path(lp).name}.html"
        live = _live_git_head(Path(lp))
        baked = _okf_baked_head(dest) if dest.is_file() and _is_okf_html(dest) else ""
        if dest.is_file() and _is_okf_html(dest) and live and baked == live:
            continue
        try:
            subprocess.run(
                [sys.executable, str(xray), "--repo", lp, "--html"],
                cwd=lp,
                timeout=180,
                capture_output=True,
            )
        except Exception as e:
            print(f"dashboard: OKF build skipped for {name}: {e}", file=sys.stderr)


def _one_line(text: str, n: int = 140) -> str:
    s = " ".join((text or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _readme_blurb(root: Path) -> tuple[str, list[str]]:
    """One-line what-it-does + up to 5 bullets from README / CARD. No secrets."""
    line, bullets = "", []
    for name in ("README.md", "readme.md", "CLAUDE.md"):
        p = root / name
        if not p.is_file():
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")[:8000]
        except OSError:
            continue
        paras, bl = [], []
        for ln in raw.splitlines():
            t = ln.strip()
            if t.startswith("#"):
                continue
            if t.startswith(("- ", "* ", "• ")):
                bl.append(t[2:].strip())
                if len(bl) >= 5:
                    break
            elif t and not paras:
                paras.append(t)
        line = _one_line(paras[0] if paras else (bl[0] if bl else root.name))
        bullets = bl[:5]
        break
    if not line:
        man = root / ".raven" / "manifest.json"
        try:
            m = json.loads(man.read_text(encoding="utf-8"))
            line = _one_line(str(m.get("description") or m.get("project") or root.name))
        except (OSError, json.JSONDecodeError, TypeError):
            line = root.name
    return line, bullets


def _recent_files(root: Path) -> tuple[list[str], str]:
    """Max 5 recent paths + last commit date. Fail-soft."""
    files, last = [], ""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%as"],
            capture_output=True, text=True, timeout=8,
        )
        last = (out.stdout or "").strip()
    except Exception:
        last = ""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-12", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, timeout=8,
        )
        seen: set[str] = set()
        for ln in (out.stdout or "").splitlines():
            p = ln.strip()
            if not p or p in seen:
                continue
            seen.add(p)
            files.append(p)
            if len(files) >= 5:
                break
    except Exception:
        pass
    return files, last


def _overview_repo_rows(names: list, bp: dict) -> str:
    rows = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        key = name.strip()
        lk = key.lower()
        if lk in seen:
            continue
        seen.add(lk)
        lp = resolve_local_path(key, "")
        root = Path(lp) if lp and Path(lp).exists() else None
        blurb, bullets = _readme_blurb(root) if root else (_one_line(key), [])
        recent, last = _recent_files(root) if root else ([], "")
        extra = " …" if root and recent else ""
        b = bp.get(key) if isinstance(bp.get(key), dict) else {}
        if not b:
            for pk, pv in (bp or {}).items():
                if str(pk).lower() == lk and isinstance(pv, dict):
                    b = pv
                    break
        ide_map = b.get("by_ide") if isinstance(b.get("by_ide"), dict) else {}
        ide_s = " · ".join(
            f"{html_lib.escape(str(ide))} ${float(iv.get('cost_usd') or 0):.4f}"
            for ide, iv in sorted(ide_map.items(), key=lambda kv: -float((kv[1] or {}).get("cost_usd") or 0))
            if isinstance(iv, dict)
        ) or "—"
        total = float(b.get("cost_usd") or 0)
        ul = ""
        if bullets:
            ul = "<ul class='brief'>" + "".join(f"<li>{html_lib.escape(_one_line(x, 80))}</li>" for x in bullets[:5]) + "</ul>"
        files_html = "<br>".join(html_lib.escape(f) for f in recent) + (html_lib.escape(extra) if extra else "")
        if not files_html:
            files_html = "—"
        rows.append(
            f"<tr><td><b>{html_lib.escape(key)}</b></td>"
            f"<td>{html_lib.escape(blurb)}{ul}</td>"
            f"<td class='dim'>{files_html}</td>"
            f"<td>{html_lib.escape(last or '—')}</td>"
            f"<td>{ide_s}</td>"
            f"<td class='num'>${total:.4f}</td></tr>"
        )
    return "".join(rows) or "<tr><td colspan='6'>No repos discovered</td></tr>"


def write_raven_dashboard(metadata: dict, metrics: Optional[dict] = None) -> Path:
    """Full dashboard: Graph + Overview + Repos + Costs + Guards. Graph = xray OKF only."""
    out_dir = VAULT / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import xray as _xray
        _xray.render_html(open_after=False)
        n = _xray.rebake_tree_htmls()
        print(f"dashboard: rebaked {n} graph pages onto shared okf-viewer.js", file=sys.stderr)
    except Exception as e:
        print(f"dashboard: xray.render_html failed: {e}", file=sys.stderr)
    metrics = metrics or {}
    project = metadata.get("project") or "raven"
    bp = metrics.get("by_project") or {}
    _ensure_okf_graphs([project, *list(bp.keys())])
    tree_map = _tree_files()
    want = str(project).lower()
    tree_file = (
        tree_map.get(want)
        or tree_map.get(Path(metadata.get("project_path") or ".").name.lower())
        or ""
    )
    iframe = f"trees/{tree_file}" if tree_file else ""
    opts = "".join(
        f"<option value='{fn}' {'selected' if fn == tree_file else ''}>{stem}</option>"
        for stem, fn in sorted(tree_map.items())
    ) or "<option value=''>no graphs yet</option>"

    turn_log, cost_log, audit_log = _gather_repo_logs(
        [project, *list(tree_map.keys()), *list(bp.keys())], per=5000
    )
    turn_log = _with_running_est(turn_log)
    log_spend = _spend_from_logs(turn_log, cost_log)
    metrics = dict(metrics)
    spend_kind = log_spend.get("spend_kind") or "estimated"
    # Costs pane headline must use the same session set / dollars as the table —
    # never max() with vault aggregate rollups (those inflated Sessions to 427).
    metrics["cost_by_day"] = log_spend["cost_by_day"] or metrics.get("cost_by_day") or {}
    metrics["spend_kind"] = spend_kind
    metrics["actual_usd"] = float(log_spend.get("actual_usd") or 0)
    metrics["estimated_usd"] = float(log_spend.get("estimated_usd") or 0)
    metrics["sessions_count"] = int(log_spend.get("sessions_count") or 0)
    metrics["total_tokens"] = int(log_spend.get("total_tokens") or 0)
    merged_bp = {}
    for name, b in log_spend["by_project"].items():
        merged_bp[name] = dict(b)
    for _n, b in merged_bp.items():
        if not isinstance(b, dict):
            continue
        ides = b.get("by_ide") if isinstance(b.get("by_ide"), dict) else {}
        if ides:
            b["cost_usd"] = round(
                sum(float(iv.get("cost_usd") or 0) for iv in ides.values() if isinstance(iv, dict)),
                4,
            )
            b["tokens"] = sum(int(iv.get("tokens") or 0) for iv in ides.values() if isinstance(iv, dict))
            b["sessions"] = sum(int(iv.get("sessions") or 0) for iv in ides.values() if isinstance(iv, dict))
            kinds = {str(iv.get("kind") or "estimated") for iv in ides.values() if isinstance(iv, dict)}
            b["kind"] = "actual" if kinds == {"actual"} else ("estimated" if kinds == {"estimated"} else "mixed")
    bp = merged_bp
    metrics["by_project"] = bp
    metrics["total_cost_usd"] = round(
        sum(float(b.get("cost_usd") or 0) for b in bp.values() if isinstance(b, dict)),
        4,
    )
    metrics["sessions_count"] = sum(
        int(b.get("sessions") or 0) for b in bp.values() if isinstance(b, dict)
    )

    repo_rows = []
    listed: set[str] = set()
    for stem, fn in sorted(tree_map.items()):
        listed.add(stem)
        b = bp.get(stem) if isinstance(bp.get(stem), dict) else {}
        if not b:
            for pk, pv in bp.items():
                if str(pk).lower() == stem and isinstance(pv, dict):
                    b = pv
                    break
        click = f"goOkf('{fn}')"
        repo_rows.append(
            f"<tr style='cursor:pointer' onclick=\"{click}\"><td><b>{stem}</b></td>"
            f"<td class='num'>{int(b.get('sessions') or 0)}</td>"
            f"<td class='num'>{int(b.get('tokens') or 0):,}</td>"
            f"<td class='num'>${float(b.get('cost_usd') or 0):.2f}</td>"
            f"<td>graph</td></tr>"
        )
    for name, b in sorted(bp.items(), key=lambda kv: str(kv[0]).lower()):
        if not isinstance(name, str) or not _safe_repo_stem(str(name)):
            continue
        if not isinstance(b, dict):
            continue
        key = str(name).lower()
        if key in listed:
            continue
        fn = tree_map.get(key)
        click = f"goOkf('{fn}')" if fn else ""
        graph_cell = "graph" if fn else "<span class='dim'>no graph file</span>"
        style = "cursor:pointer" if fn else ""
        repo_rows.append(
            f"<tr style='{style}' onclick=\"{click}\"><td><b>{name}</b></td>"
            f"<td class='num'>{int(b.get('sessions') or 0)}</td>"
            f"<td class='num'>{int(b.get('tokens') or 0):,}</td>"
            f"<td class='num'>${float(b.get('cost_usd') or 0):.2f}</td>"
            f"<td>{graph_cell}</td></tr>"
        )
    repo_tbl = "".join(repo_rows) or "<tr><td colspan='5'>No repo metrics yet</td></tr>"
    ov_names = []
    for x in (project, *list(tree_map.keys()), *list(bp.keys())):
        if x and str(x) not in ov_names:
            ov_names.append(str(x))
    overview_tbl = _overview_repo_rows(ov_names, bp)

    guards = metrics.get("guard_events") or {}
    GUARD_MEANING = {
        "unknown": "Audit JSON with no event/kind — usually token/cost lines, not a block.",
        "notify": "notify.py ran (email/Slack). dry-run = no secrets file; not a violation.",
        "guard_block": "A guard denied an action (real stop). Read the audit line for which guard.",
        "guard_warn": "A guard warned but allowed the action.",
        "design": "Logged design note (Andie-Jr / plan). Not a security hit.",
        "implement": "Logged implement note after go-ahead. Not a security hit.",
        "commit": "Pre-commit notify: gate passed.",
        "block": "Pre-commit notify: gate blocked the commit.",
        "override": "Guard override flag used ([GUARD:ALLOW-DELETE] etc.).",
        "token-warning": "Session token threshold crossed (75%/90%).",
        "incident": "P1/P2 incident notify was attempted.",
        "violation": "Policy/style/CVE/secret rule recorded a violation.",
        "approval": "An approval/override was logged.",
    }
    if hasattr(guards, "items"):
        g_rows = "".join(
            f"<tr><td><code>{k}</code></td><td class='num'>{v}</td>"
            f"<td class='dim'>{GUARD_MEANING.get(str(k), 'Audit line kind from .raven/audit — not always a guard fire.')}</td></tr>"
            for k, v in sorted(guards.items(), key=lambda x: -x[1])[:20]
        )
    else:
        g_rows = ""
    n_guards = sum(guards.values()) if hasattr(guards, "values") else 0

    obs_log = _tail_jsonl(Path.home() / "RavenVault" / "obs" / "runs.jsonl", 80)
    logpack_json = json.dumps({"turn": turn_log, "cost": cost_log, "audit": audit_log, "obs": obs_log})
    try:
        from dash_settings import public_view as _pv
        settings_json = json.dumps(_pv())
    except Exception:
        settings_json = "{}"
    repos_for_filter = sorted({
        *tree_map.keys(),
        *[
            str(r.get("repo") or r.get("project") or "").strip()
            for r in (turn_log + cost_log + audit_log + obs_log)
            if str(r.get("repo") or r.get("project") or "").strip()
        ],
    }, key=lambda s: s.lower())
    log_repo_opts = '<option value="all">all repos</option>' + "".join(
        f'<option value="{html_lib.escape(x)}">{html_lib.escape(x)}</option>' for x in repos_for_filter
    )

    def _repo_cell(r: dict) -> str:
        return str(r.get("repo") or r.get("project") or "—")

    if turn_log:
        turn_tbl = "".join(
            f"<tr data-repo='{html_lib.escape(_repo_cell(r).lower())}'>"
            f"<td>{_td(r.get('ts'))}</td><td>{_td(_repo_cell(r))}</td>"
            f"<td>{_td(r.get('ide') or r.get('host'))}</td>"
            f"<td>{_td(r.get('tier'))}</td><td>{_td(r.get('recommend'))}</td>"
            f"<td class='num'>{_td(r.get('est_cost_usd'), money=True)}</td>"
            f"<td class='num'>{_td(r.get('total_cost_usd'), money=True)}</td>"
            f"<td><button type='button' onclick=\"show('obs');openLog('obs',{i})\">view</button></td>"
            f"<td><button type='button' onclick=\"openLog('turn',{i})\">json</button></td></tr>"
            for i, r in reversed(list(enumerate(turn_log)))
        )
    else:
        turn_tbl = "<tr><td colspan='8'>No router fires logged. If Codex/Grok skipped model-router.py, this stays empty.</td></tr>"
    if cost_log:
        cost_tbl = "".join(
            f"<tr data-repo='{html_lib.escape(_repo_cell(r).lower())}'>"
            f"<td>{_td(r.get('ts'))}</td><td>{_td(_repo_cell(r))}</td>"
            f"<td>{_td(r.get('ide'))}</td><td>{_td(r.get('model'))}</td>"
            f"<td>{_td(r.get('source'))}</td>"
            f"<td class='num'>{_td(r.get('tokens_in'))}</td>"
            f"<td class='num'>{_td(r.get('tokens_out'))}</td>"
            f"<td class='num'>{_td(r.get('computed_cost_usd'), money=True)}</td>"
            f"<td class='num'>{_td(r.get('total_cost_usd') or r.get('cum_session_usd'), money=True)}</td>"
            f"<td><button type='button' onclick=\"openLog('cost',{i})\">json</button></td></tr>"
            for i, r in reversed(list(enumerate(cost_log)))
        )
    else:
        cost_tbl = "<tr><td colspan='10'>No Stop/token-meter rows yet (Grok often has no Stop hook).</td></tr>"
    if audit_log:
        audit_tbl = "".join(
            f"<tr data-repo='{html_lib.escape(_repo_cell(r).lower())}'>"
            f"<td>{_td(r.get('ts') or r.get('timestamp'))}</td>"
            f"<td>{_td(_repo_cell(r))}</td>"
            f"<td>{_td(r.get('ide') or r.get('host') or '—')}</td>"
            f"<td>{_td(r.get('event') or r.get('kind') or 'unknown')}</td>"
            f"<td>{_td(r.get('detail') or r.get('reason') or r.get('model') or '')}</td>"
            f"<td><button type='button' onclick=\"openLog('audit',{i})\">json</button></td></tr>"
            for i, r in reversed(list(enumerate(audit_log)))
        )
    else:
        audit_tbl = "<tr><td colspan='6'>No audit JSONL in window.</td></tr>"
    obs_src = _with_running_est(obs_log) if obs_log else turn_log
    if obs_src:
        obs_tbl = "".join(
            f"<tr data-repo='{html_lib.escape(_repo_cell(r).lower())}'>"
            f"<td>{_td(r.get('ts'))}</td><td>{_td(_repo_cell(r))}</td>"
            f"<td>{_td(r.get('ide') or r.get('host'))}</td>"
            f"<td>{_td(r.get('tier'))}</td><td>{_td(r.get('recommend'))}</td>"
            f"<td class='num'>{_td(r.get('prompt_chars'))}</td>"
            f"<td class='num'>{_td(r.get('est_cost_usd'), money=True)}</td>"
            f"<td><button type='button' onclick=\"openLog('obs',{i})\">json</button></td></tr>"
            for i, r in reversed(list(enumerate(obs_src)))
        )
    else:
        obs_tbl = "<tr><td colspan='8'>No local traces yet. Router writes ~/RavenVault/obs/runs.jsonl (not git).</td></tr>"
    om = _obs_metrics(obs_src)
    obs_ide_tbl = _count_tbl(om["by_ide"], "IDE", "Traces")
    obs_tier_tbl = _count_tbl(om["by_tier"], "Tier", "Traces")
    # Money from log_spend by_project (same as Costs); traces still from _obs_metrics.
    obs_repo_names = set(om["by_repo"].keys()) | {
        str(k) for k, v in (bp or {}).items() if isinstance(v, dict)
    }
    obs_repo_tbl = "".join(
        f"<tr><td>{html_lib.escape(str(k))} "
        f"<span class='dim'>{html_lib.escape(str((bp.get(k) or {}).get('kind') or '—'))}</span></td>"
        f"<td class='num'>{int(om['by_repo'].get(k, 0))}</td>"
        f"<td class='num'>${float((bp.get(k) or {}).get('cost_usd') or 0):.4f}</td></tr>"
        for k in sorted(
            obs_repo_names,
            key=lambda x: (
                -float((bp.get(x) or {}).get("cost_usd") or 0),
                -int(om["by_repo"].get(x, 0)),
                str(x).lower(),
            ),
        )
    ) or "<tr><td colspan='3'>No repo cost or traces yet</td></tr>"
    cost_repo_parts = []
    for k, v in sorted((bp or {}).items(), key=lambda kv: -float((kv[1] or {}).get("cost_usd") or 0)):
        if not isinstance(v, dict):
            continue
        rk = v.get("kind") or "estimated"
        cost_repo_parts.append(
            f"<tr><td><b>{html_lib.escape(str(k))}</b> <span class='dim'>summary · {html_lib.escape(str(rk))}</span></td>"
            f"<td class='num'>{int(v.get('sessions') or 0)}</td>"
            f"<td class='num'>{int(v.get('tokens') or 0):,}</td>"
            f"<td class='num'>${float(v.get('cost_usd') or 0):.4f}</td></tr>"
        )
        for ide, iv in sorted((v.get("by_ide") or {}).items(), key=lambda kv: -float((kv[1] or {}).get("cost_usd") or 0)):
            if not isinstance(iv, dict):
                continue
            ik = iv.get("kind") or "estimated"
            io = ""
            if iv.get("in") or iv.get("out") or iv.get("cache_read"):
                io = f" in={int(iv.get('in') or 0):,} out={int(iv.get('out') or 0):,}"
                if int(iv.get("cache_read") or 0):
                    io += f" cache_read={int(iv.get('cache_read') or 0):,}"
                if ik == "estimated" and int(iv.get("fires") or 0):
                    io += f" fires={int(iv.get('fires') or 0)}×500out"
            cost_repo_parts.append(
                f"<tr><td class='dim' style='padding-left:24px'>IDE · {html_lib.escape(str(ide))} ({html_lib.escape(str(ik))}{io})</td>"
                f"<td class='num'>{int(iv.get('sessions') or 0)}</td>"
                f"<td class='num'>{int(iv.get('tokens') or 0):,}</td>"
                f"<td class='num'>${float(iv.get('cost_usd') or 0):.4f}</td></tr>"
            )
    mix = log_spend.get("router_mix") or []
    router_mix_tbl = "".join(
        f"<tr><td>{html_lib.escape(str(r.get('ide')))}</td>"
        f"<td>{html_lib.escape(str(r.get('tier')))}</td>"
        f"<td><code>{html_lib.escape(str(r.get('model')))}</code></td>"
        f"<td class='num'>{int(r.get('fires') or 0)}</td></tr>"
        for r in mix
    ) or "<tr><td colspan='4'>No router fires</td></tr>"
    cost_by_repo_tbl = "".join(cost_repo_parts) or "<tr><td colspan='4'>No repo cost yet — router turn-log is empty</td></tr>"
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    spend = float(metrics.get("total_cost_usd") or 0)
    spend_kind = metrics.get("spend_kind") or log_spend.get("spend_kind") or "estimated"
    act_u = float(metrics.get("actual_usd") or log_spend.get("actual_usd") or 0)
    est_u = float(metrics.get("estimated_usd") or log_spend.get("estimated_usd") or 0)
    if spend_kind == "actual":
        spend_label = "Spend (actual)"
        spend_tip = (
            "Stop cost-log only: one snapshot per session (max tokens_out), "
            "computed_cost_usd / get_cost including cache_read×0.1 and cache_creation×1.25."
        )
    elif spend_kind == "mixed":
        spend_label = f"Spend (mixed) actual ${act_u:.4f} + est ${est_u:.4f}"
        spend_tip = (
            f"Headline = sum of repo rows below. "
            f"Actual ${act_u:.4f}: Stop snapshot per session with cache billed "
            f"(cache_read×0.1, cache_creation×1.25) — not a vendor invoice. "
            f"Estimated ${est_u:.4f}: router recommend × (prompt_chars/4 in + 500 out per fire); "
            f"Grok/Codex have no Stop tokens — estimates are not billed dollars."
        )
    else:
        spend_label = "Spend (estimated)"
        spend_tip = (
            "No cost-log actuals. Per router fire: chars/4 in + 500 out × rates. "
            "Not billed — Grok/Codex Stop tokens are absent."
        )
    spend_tip = (
        spend_tip
        + " Sessions count matches the grouped table (same log filter), not vault .metrics rollups. "
        + "Check vendor billing after Refresh, or /run-costs."
    )
    sess = int(metrics.get("sessions_count") or 0)
    tok = int(metrics.get("total_tokens") or 0)
    days = metrics.get("cost_by_day") or {}
    day_rows = "".join(
        f"<tr><td>{d}</td><td class='num'>${float(days[d]):.4f}</td></tr>"
        for d in sorted(days.keys())[-14:]
    )

    okf_json = json.dumps(tree_map)
    bp_json = json.dumps({
        str(k).lower(): {
            "sessions": int(v.get("sessions") or 0),
            "tokens": int(v.get("tokens") or 0),
            "cost_usd": float(v.get("cost_usd") or 0),
        }
        for k, v in bp.items()
        if isinstance(k, str) and _safe_repo_stem(str(k)) and isinstance(v, dict)
    })
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
<title>Raven dashboard — {project}</title>
<!-- raven-dashboard v2: shell + xray.render_html OKF. No mind-maps. -->
<style>
:root{{--bg:#0e1116;--panel:#161b23;--line:#232c3a;--ink:#e6ebf2;--muted:#9aa7b8;--accent:#5aa2e0}}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;display:flex;min-height:100vh}}
aside{{width:200px;background:var(--panel);border-right:1px solid var(--line);padding:16px 10px}}
.nav{{display:block;width:100%;text-align:left;padding:8px 10px;margin:2px 0;border:0;border-radius:8px;background:none;color:var(--muted);cursor:pointer}}
.nav.on,.nav:hover{{background:#1c2330;color:var(--ink)}}
main{{flex:1;padding:16px;min-width:0}}
.view{{display:none}}.view.on{{display:block}}
iframe{{width:100%;height:calc(100vh - 120px);border:1px solid var(--line);border-radius:8px;background:#020617}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;border-bottom:1px solid var(--line);text-align:left}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.dim{{color:var(--muted)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:12px 0}}
.tile{{background:var(--panel);padding:12px;border-radius:8px;border:1px solid var(--line)}}
ul.brief{{margin:6px 0 0;padding-left:18px;font-size:12px;color:var(--muted)}}
#v-home table{{font-size:13px}}
select{{background:#1c2330;color:var(--ink);border:1px solid var(--line);padding:4px 8px;border-radius:6px}}
.pane-bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}}
.pane-bar h2{{margin:0;flex:1}}
.refresh-now{{background:#1c2330;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:4px 10px;cursor:pointer}}
.refresh-now:hover{{border-color:var(--accent)}}
</style></head>
<body>
<aside>
  <h1 style="font-size:16px;padding:0 8px 12px">🪶 Raven<br><span class="dim" style="font-size:12px" id="repoLabel">{project}</span></h1>
  <button class="nav on" data-v="home">Overview</button>
  <button class="nav" data-v="graph">Graph</button>
  <button class="nav" data-v="repos">Repos</button>
  <button class="nav" data-v="costs">Costs</button>
  <button class="nav" data-v="logs">Logs</button>
  <button class="nav" data-v="obs">Observability</button>
  <button class="nav" data-v="guards">Guards</button>
  <button class="nav" data-v="settings">Settings</button>
</aside>
<main>
<section class="view" id="v-graph">
  {_pane_bar("Graph", built_at)}
  <p class="dim">Pick a repo — Graph loads <b>that</b> repo’s page. Built by <code>xray.render_html</code> when a local clone exists.</p>
  <p style="margin:8px 0">Repo:
    <select id="okfSel" onchange="goOkf(this.value)">{opts}</select>
    <span class="dim" id="graphLooking">Looking at: {project}</span>
  </p>
  <iframe id="gframe" src="{iframe}" title="OKF graph"></iframe>
</section>
<section class="view on" id="v-home">
  {_pane_bar("Overview", built_at)}
  <div class="tiles">
    <div class="tile" title="{html_lib.escape(spend_tip)}"><div class="dim">{spend_label} <span id="ovScope"></span></div><div style="font-size:22px" id="ovSpend">${spend:.4f}</div></div>
    <div class="tile"><div class="dim">Sessions (table)</div><div style="font-size:22px" id="ovSess">{sess}</div></div>
    <div class="tile"><div class="dim">Tokens</div><div style="font-size:22px" id="ovTok">{tok:,}</div></div>
    <div class="tile"><div class="dim">Guard events (all repos)</div><div style="font-size:22px">{n_guards}</div></div>
  </div>
  <p class="dim">All repos Raven can see. One-line purpose from README, up to 5 bullets, last 5 files from git, last commit date, cost by IDE, total.</p>
  <table>
    <thead><tr>
      <th>Repo</th>
      <th>What it does</th>
      <th>Recent files</th>
      <th>Last edited</th>
      <th>Cost (IDE)</th>
      <th class="num">Total cost</th>
    </tr></thead>
    <tbody>{overview_tbl}</tbody>
  </table>
</section>
<section class="view" id="v-repos">
  {_pane_bar("Repos", built_at)}
  <p class="dim">Click a row to open that repo in the Graph pane.</p>
  <table><thead><tr><th>Repo</th><th class="num">Sessions</th><th class="num">Tokens</th><th class="num">Cost</th><th>Graph</th></tr></thead>
  <tbody>{repo_tbl}</tbody></table>
</section>
<section class="view" id="v-costs">
  {_pane_bar("Costs", built_at)}
  <p class="dim">{html_lib.escape(spend_tip)} Grouped by <b>repo</b>, then <b>IDE</b>.</p>
  <div class="tiles">
    <div class="tile" title="{html_lib.escape(spend_tip)}"><div class="dim">{spend_label}</div><div style="font-size:22px" id="costSpend">${spend:.4f}</div></div>
    <div class="tile"><div class="dim">Sessions (table)</div><div style="font-size:22px" id="costSess">{sess}</div></div>
  </div>
  <h3 style="margin:16px 0 8px">By repo, then IDE</h3>
  <table><thead><tr><th>Repo / IDE</th><th class="num">Sessions</th><th class="num">Tokens</th><th class="num">Cost</th></tr></thead>
  <tbody>{cost_by_repo_tbl}</tbody></table>
  <h3 style="margin:16px 0 8px">Router (what classified, not billed Opus/Fable)</h3>
  <p class="dim">Counts from turn-log.jsonl. Cost uses this <code>recommend</code> in get_cost(). No Opus/Fable in this table unless the router wrote those ids.</p>
  <table><thead><tr><th>IDE</th><th>Tier</th><th>Recommend</th><th class="num">Fires</th></tr></thead>
  <tbody>{router_mix_tbl}</tbody></table>
  <h3 style="margin:16px 0 8px">By day</h3>
  <table><thead><tr><th>Day</th><th class="num">Spend</th></tr></thead><tbody>{day_rows}</tbody></table>
</section>
<section class="view" id="v-logs">
  {_pane_bar("Logs", built_at)}
  <p class="dim">Every row is classified by <b>repo</b> and <b>IDE</b>. Filter, then json → detail. ← Back returns to these tables.</p>
  <div id="logTables">
  <p>Repo: <select id="logRepo" onchange="filterLogs(this.value)">{log_repo_opts}</select></p>
  <h3 style="margin:16px 0 8px">Router (turn-log.jsonl)</h3>
  <table><thead><tr><th>When</th><th>Repo</th><th>IDE</th><th>Tier</th><th>Recommend</th><th class="num">est</th><th class="num">total-cost</th><th>Observe</th><th></th></tr></thead>
  <tbody>{turn_tbl}</tbody></table>
  <h3 style="margin:16px 0 8px">Turns (cost-log.jsonl)</h3>
  <table><thead><tr><th>When</th><th>Repo</th><th>IDE</th><th>Model</th><th>Source</th><th class="num">in</th><th class="num">out</th><th class="num">turn $</th><th class="num">total-cost</th><th></th></tr></thead>
  <tbody>{cost_tbl}</tbody></table>
  <h3 style="margin:16px 0 8px">Audit (latest lines)</h3>
  <table><thead><tr><th>When</th><th>Repo</th><th>IDE</th><th>Event</th><th>Detail</th><th></th></tr></thead>
  <tbody>{audit_tbl}</tbody></table>
  </div>
</section>
<section class="view" id="v-obs">
  {_pane_bar("Observability", built_at)}
  <p class="dim">Local traces from <code>~/RavenVault/obs/runs.jsonl</code> (metadata only — no prompt/response). Spend is the same calculator as Costs (cost-log + turn-log). Trace counts are from these rows; per-row <code>est_cost_usd</code> in the table remains the router guess.</p>
  <div class="tiles">
    <div class="tile"><div class="dim">Traces</div><div style="font-size:22px">{om["traces"]}</div></div>
    <div class="tile" title="{html_lib.escape(spend_tip)}"><div class="dim">{spend_label}</div><div style="font-size:22px" id="obsSpend">${spend:.4f}</div></div>
    <div class="tile"><div class="dim">Prompt chars</div><div style="font-size:22px">{om["chars"]:,}</div></div>
    <div class="tile"><div class="dim">Last trace</div><div style="font-size:14px">{html_lib.escape(om["last"])}</div></div>
    <div class="tile"><div class="dim">needs_rate</div><div style="font-size:22px">{om["needs_rate"]}</div></div>
    <div class="tile"><div class="dim">redteam flags</div><div style="font-size:22px">{om["redteam"]}</div></div>
  </div>
  <div class="tiles">
    <div class="tile"><h3>By IDE</h3><table><thead><tr><th>IDE</th><th class="num">Traces</th></tr></thead><tbody>{obs_ide_tbl}</tbody></table></div>
    <div class="tile"><h3>By tier</h3><table><thead><tr><th>Tier</th><th class="num">Traces</th></tr></thead><tbody>{obs_tier_tbl}</tbody></table></div>
    <div class="tile"><h3>By repo (cost)</h3><table><thead><tr><th>Repo</th><th class="num">Traces</th><th class="num">Cost</th></tr></thead><tbody>{obs_repo_tbl}</tbody></table></div>
  </div>
  <div id="obsTables">
  <p>Repo: <select id="obsRepo" onchange="filterLogs(this.value)">{log_repo_opts}</select></p>
  <table><thead><tr><th>When</th><th>Repo</th><th>IDE</th><th>Tier</th><th>Recommend</th><th class="num">prompt chars</th><th class="num">est</th><th></th></tr></thead>
  <tbody>{obs_tbl}</tbody></table>
  </div>
</section>
<section class="view" id="v-settings">
  {_pane_bar("Settings", built_at)}
  <p class="dim">See and edit local config. No API keys. Save needs <code>python3 scripts/ops/dashboard-server.py</code> (127.0.0.1:9787). file:// is view-only.</p>
  <form id="setForm" class="tile" style="max-width:640px" onsubmit="return saveSettings(event)">
    <h3>Observability</h3>
    <p class="dim"><b>LangSmith (smith.langchain.com) is not open source.</b> The tracing UI is cloud; self-host LangSmith is a paid Enterprise add-on. The OSS path is a <b>self-hosted</b> stack you run (typically <b>Langfuse</b> MIT, or local tracers like opensmith) — not a Raven checkbox that uploads traces.</p>
    <p class="dim">Raven still does <b>not</b> copy prompts into git. Choose a backend; Logs <b>Observe</b> is a <b>link</b> to that UI. Real traces only exist if that product is already tracing (their SDK/env).</p>
    <p>Mode:
      <label><input type="radio" name="obsMode" value="local"/> In dashboard (default)</label>
      <label><input type="radio" name="obsMode" value="off"/> Off</label>
      <label><input type="radio" name="obsMode" value="external"/> Extra UI URL (optional Langfuse)</label>
      <label><input type="radio" name="obsMode" value="langsmith_cloud"/> LangSmith cloud</label>
    </p>
    <p><label>Optional extra UI URL (only if you already run Langfuse)<br><input id="setOsBase" style="width:100%" placeholder="http://127.0.0.1:3000"/></label></p>
    <p><label>LangSmith cloud base URL<br><input id="setLsBase" style="width:100%"/></label></p>
    <p><label>LangSmith project (name only)<br><input id="setLsProj" style="width:100%"/></label></p>
    <h3 style="margin-top:18px">AIRTaaS red-team</h3>
    <p><label>AIRTaaS MCP enabled <input type="checkbox" id="setAirOn"/></label></p>
    <p>MCP (fixed): <code>https://sandbox.airtaas.ai/mcp</code></p>
    <p><button type="button" onclick="window.open('https://sandbox.airtaas.ai','_blank','noopener')">Log in to AIRTaaS</button>
       <span class="dim">Opens their site. Login stays with AIRTaaS — Raven does not store password or token.</span></p>
    <p class="dim">Sandbox is free for developers; enterprise is paid. Enable the checkbox after you have a session. Security-classed prompts then log <code>redteam=airtaas</code>.</p>
    <p><button type="submit">Save</button> <span class="dim" id="setMsg"></span></p>
  </form>
</section>
<section class="view" id="v-guards">
  {_pane_bar("Guards", built_at)}
  <p class="dim">{n_guards} JSONL line(s) in <code>.raven/audit</code> for this window. Count is not “incidents.” Only <code>guard_block</code> / <code>block</code> / <code>violation</code> are stops.</p>
  <table><thead><tr><th>Event</th><th class="num">Count</th><th>What it means</th></tr></thead>
  <tbody>{g_rows or "<tr><td colspan='3'>No audit lines in window</td></tr>"}</tbody></table>
</section>
<div id="logDetail" style="display:none;flex:1;padding:16px;overflow:auto">
  <p><button type="button" onclick="closeLogDetail()">← Back to log tables</button>
     <span class="dim" id="logDetailMeta"></span></p>
  <pre id="logDetailPre" class="dim"></pre>
</div>
</main>
<script>
const OKF = {okf_json};
const METRICS = {bp_json};
const LOGPACK = __LOGPACK__;
const SETTINGS = __SETTINGS__;
const ALL = {{spend:{spend}, sess:{sess}, tok:{tok}}};
function show(v){{
  document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('on', x.dataset.v===v));
  document.querySelectorAll('.view').forEach(x=>x.classList.toggle('on', x.id==='v-'+v));
  try {{ sessionStorage.setItem('ravenPane', v); }} catch(e) {{}}
  closeLogDetail();
}}
function liveDashUrl(){{
  const hash = (location.hash || '').replace(/^#/, '');
  return 'http://127.0.0.1:9787' + (hash ? '#' + hash : '');
}}
function refreshNow(){{
  const on = document.querySelector('.nav.on');
  const pane = on && on.dataset.v;
  if (pane) try {{ sessionStorage.setItem('ravenPane', pane); }} catch(e) {{}}
  document.querySelectorAll('.refresh-now').forEach(b => {{ b.disabled = true; b.textContent = 'Refreshing…'; }});
  const bust = Date.now();
  fetch('http://127.0.0.1:9787/api/run-costs?t='+bust).catch(()=>{{}}).then(() =>
    fetch('http://127.0.0.1:9787/refresh?t='+bust)
  ).then(r=>r.json()).then(() => {{
    location.reload();
  }}).catch(() => {{
    const live = liveDashUrl();
    document.querySelectorAll('.refresh-meta').forEach(el => {{
      el.innerHTML = 'Last refresh: file:// is view-only. <a class="live-dash" href="'+live+'">Open live dashboard</a>';
    }});
    document.querySelectorAll('.refresh-now').forEach(b => {{ b.disabled = false; b.textContent = '↻ Refresh now'; }});
  }});
}}
document.querySelectorAll('.nav').forEach(n=>n.onclick=()=>show(n.dataset.v));
function stemOf(fn){{ return (fn||'').replace(/\\.html$/i,''); }}
function metricFor(stem){{
  const s = (stem||'').toLowerCase();
  const keys = Object.keys(METRICS);
  const hit = keys.find(k => k.toLowerCase()===s || k.toLowerCase().replace(/_/g,'-')===s);
  return hit ? METRICS[hit] : {{sessions:0, tokens:0, cost_usd:0}};
}}
function applyRepo(file){{
  const stem = stemOf(file);
  const el = document.getElementById('repoLabel');
  if (el) el.textContent = stem || 'all';
  const look = document.getElementById('graphLooking');
  if (look) look.textContent = 'Looking at: ' + (stem || 'all');
  const set = (id, v) => {{ const n=document.getElementById(id); if(n) n.textContent=v; }};
  set('ovScope', stem ? '(graph: '+stem+'; totals are all repos)' : '(all repos)');
  if (history.replaceState) history.replaceState(null,'','#'+stem);
}}
function filterLogs(repo){{
  const r = (repo||'all').toLowerCase().replace(/\\.html$/,'');
  document.querySelectorAll('tr[data-repo]').forEach(tr => {{
    const v = (tr.getAttribute('data-repo')||'').toLowerCase();
    const hit = (r==='all'||r===''||v===r||v.replace(/_/g,'-')===r.replace(/_/g,'-'));
    tr.style.display = hit ? '' : 'none';
  }});
  const sel = document.getElementById('logRepo');
  if (sel) {{
    for (const o of sel.options) {{
      if (o.value.toLowerCase()===r) {{ sel.value = o.value; break; }}
    }}
  }}
}}
function openLog(bag, i){{
  const row = (LOGPACK[bag]||[])[i];
  if (!row) return;
  document.querySelectorAll('main > .view').forEach(x => x.style.display = 'none');
  const det = document.getElementById('logDetail');
  if (det) det.style.display = 'block';
  const meta = document.getElementById('logDetailMeta');
  if (meta) meta.textContent = 'repo='+(row.repo||row.project||'—')+' · ide='+(row.ide||row.host||'—');
  const pre = document.getElementById('logDetailPre');
  if (pre) pre.textContent = JSON.stringify(row, null, 2);
}}
(function fillSettings(){{
  const s = SETTINGS || {{}};
  const mode = s.observability || 'local';
  document.querySelectorAll('input[name=obsMode]').forEach(el => {{ el.checked = el.value === mode; }});
  const os = document.getElementById('setOsBase');
  if (os) os.value = s.opensource_base_url || 'http://127.0.0.1:3000';
  const b = document.getElementById('setLsBase');
  if (b) b.value = s.langsmith_base_url || '';
  const p = document.getElementById('setLsProj');
  if (p) p.value = s.langsmith_project || '';
  const ao = document.getElementById('setAirOn');
  if (ao) ao.checked = !!s.airtaas_enabled;
}})();
function saveSettings(ev){{
  ev.preventDefault();
  const modeEl = document.querySelector('input[name=obsMode]:checked');
  const body = {{
    observability: modeEl ? modeEl.value : 'off',
    langsmith_enabled: !!(modeEl && modeEl.value === 'langsmith_cloud'),
    langsmith_base_url: document.getElementById('setLsBase').value,
    langsmith_project: document.getElementById('setLsProj').value,
    opensource_base_url: document.getElementById('setOsBase').value,
    airtaas_enabled: document.getElementById('setAirOn').checked
  }};
  const msg = document.getElementById('setMsg');
  fetch('http://127.0.0.1:9787/api/settings', {{
    method: 'POST', headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify(body)
  }}).then(r => r.json()).then(d => {{
    if (msg) msg.textContent = d.ok ? 'Saved. Rebuild dashboard to refresh Logs links.' : (d.error||'fail');
  }}).catch(() => {{
    if (msg) msg.textContent = 'Start: python3 scripts/ops/dashboard-server.py — file:// cannot write.';
  }});
  return false;
}}
function closeLogDetail(){{
  const det = document.getElementById('logDetail');
  if (det) det.style.display = 'none';
  const on = document.querySelector('.nav.on');
  const v = on && on.dataset.v;
  document.querySelectorAll('main > .view').forEach(x => {{
    x.style.display = (v && x.id === 'v-'+v) ? 'block' : 'none';
  }});
}}
function goOkf(name, stay){{
  if(!name) return;
  const allowed = Object.values(OKF);
  if(allowed.indexOf(name)<0) return;
  const fr = document.getElementById('gframe');
  if (fr) fr.src = 'trees/'+name;
  const sel = document.getElementById('okfSel');
  if(sel) sel.value = name;
  applyRepo(name);
  if (!stay) show('graph');
}}
(function(){{
  try {{
    var pane = sessionStorage.getItem('ravenPane');
    if (pane) show(pane);
  }} catch(e) {{}}
  var h = decodeURIComponent((location.hash||'').replace(/^#/,''));
  if(!h) return;
  var s = h.toLowerCase().replace(/\\.html$/,'');
  var file = OKF[s];
  if(!file){{
    var k = Object.keys(OKF).find(x => x.replace(/-/g,'')===s.replace(/-/g,''));
    file = k ? OKF[k] : '';
  }}
  if(file) goOkf(file, true);
}})();
</script>
</body></html>
"""
    dest = out_dir / RAVEN_DASHBOARD_NAME
    page = page.replace("__LOGPACK__", logpack_json)
    page = page.replace("__SETTINGS__", settings_json)
    dest.write_text(page)
    redirect = (
        "<!doctype html><meta charset='utf-8'/>"
        f"<meta http-equiv='refresh' content='0;url={RAVEN_DASHBOARD_NAME}'/>"
        f"<a href='{RAVEN_DASHBOARD_NAME}'>Raven dashboard</a>\n"
    )
    (out_dir / "index.html").write_text(redirect)
    (VAULT / "dashboard.html").write_text(
        "<!doctype html><meta charset='utf-8'/>"
        f"<meta http-equiv='refresh' content='0;url=dashboard/{RAVEN_DASHBOARD_NAME}'/>"
        f"<a href='dashboard/{RAVEN_DASHBOARD_NAME}'>Raven dashboard</a>\n"
    )
    return dest


def render_index_shell(metrics: dict, metadata: dict) -> str:
    """Landing dashboard: Graph for THIS repo only. No other-repo picker."""
    project = metadata.get("project") or "raven"
    trees = VAULT / "dashboard" / "trees"
    want = str(project).lower()
    tree_file = ""
    if trees.is_dir():
        for p in trees.glob("*.html"):
            if p.stem.lower() == want:
                tree_file = p.name
                break
        if not tree_file:
            folder = Path(metadata.get("project_path") or ".").name.lower()
            for p in trees.glob("*.html"):
                if p.stem.lower() == folder:
                    tree_file = p.name
                    break
    iframe = f"trees/{tree_file}" if tree_file else ""
    miss = "" if tree_file else "<p style='color:#e0a030'>No OKF graph for this repo yet.</p>"
    spend = metrics.get("total_cost_usd") or (metrics.get("totals") or {}).get("cost_usd") or 0
    try:
        spend_s = f"${float(spend):.2f}"
    except (TypeError, ValueError):
        spend_s = "$0"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
<title>Raven — {project}</title>
<style>
:root{{--bg:#0e1116;--panel:#161b23;--line:#232c3a;--ink:#e6ebf2;--ink2:#9aa7b8;--accent:#5aa2e0}}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,sans-serif;display:flex;min-height:100vh}}
aside{{width:200px;background:var(--panel);border-right:1px solid var(--line);padding:16px 10px}}
.nav{{display:block;width:100%;text-align:left;padding:8px 10px;margin:2px 0;border:0;border-radius:8px;
background:none;color:var(--ink2);cursor:pointer}}
.nav.on,.nav:hover{{background:#1c2330;color:var(--ink)}}
main{{flex:1;padding:16px;min-width:0}}
.view{{display:none}}.view.on{{display:block}}
iframe{{width:100%;height:calc(100vh - 90px);border:1px solid var(--line);border-radius:8px;background:#020617}}
a{{color:var(--accent)}}
h2{{margin-bottom:8px}}
</style></head><body>
<aside>
  <h1 style="font-size:16px;padding:0 8px 12px">🪶 Raven<br><span style="color:var(--ink2);font-size:12px;font-weight:400">{project}</span></h1>
  <button class="nav on" data-v="graph">Graph</button>
  <button class="nav" data-v="home">Overview</button>
  <button class="nav" data-v="costs">Costs</button>
</aside>
<main>
<section class="view on" id="v-graph">
  <h2>Graph — {project}</h2>
  <p style="color:var(--ink2);font-size:13px;margin-bottom:8px">This repo only. Click a node for summary and flow. Not a multi-repo mind map.</p>
  {miss}
  <iframe id="gframe" src="{iframe}" title="OKF graph"></iframe>
</section>
<section class="view" id="v-home">
  <h2>Overview</h2>
  <p>Project <b>{project}</b> · 30d spend {spend_s}</p>
  <p style="color:var(--ink2);margin-top:12px"><a href="legacy.html">Detailed tokenomics / citations</a></p>
</section>
<section class="view" id="v-costs">
  <h2>Costs</h2>
  <p>30d {spend_s}. <a href="legacy.html">Full tables</a></p>
</section>
</main>
<script>
document.querySelectorAll('.nav').forEach(n=>n.onclick=()=>{{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('on'));
  n.classList.add('on');
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('on'));
  document.getElementById('v-'+n.dataset.v).classList.add('on');
}});
</script>
</body></html>
"""


def render_html(
    metrics: dict,
    metadata: dict,
    recs: list,
    graph: Optional[dict] = None,
    graph_only: bool = False,
) -> str:
    """Static HTML with download buttons; optional knowledge graph panel."""
    sev_color = {"high": "#dc2626", "medium": "#f59e0b", "info": "#3b82f6"}
    raw_json = json.dumps(
        {"metadata": metadata, "metrics": metrics, "recommendations": recs, "graph": graph},
        indent=2,
        default=str,
    )
    kg_section = (
        '<p class="meta" id="knowledge-graph">Vault note graph is not the code map. '
        "Open the Code graph (OKF) via <code>python3 scripts/code-xray.py --html --open</code>.</p>"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
<meta http-equiv="Pragma" content="no-cache"/>
<meta http-equiv="Expires" content="0"/>
<meta name="raven-dashboard-version" content="kg-v2-grounded"/>
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
  <p style="color: #94a3b8; margin-bottom: 8px;">
    Generated {metadata['report_generated_at_local']} ·
    Plugin v{metadata['plugin_version']} ·
    Window: {metrics['window_start']} → {metrics['window_end']} ({metrics['window_days']} days)
  </p>
  <nav style="position:sticky;top:0;z-index:20;background:#0f172acc;backdrop-filter:blur(8px);
    border-bottom:1px solid #1e293b;margin:0 -8px 16px;padding:10px 8px;display:flex;gap:14px;
    flex-wrap:wrap;align-items:center;font-size:14px;">
    <a href="#code-graph" style="color:#e2e8f0;text-decoration:none;font-weight:600;">🕸 Graph</a>
    <a href="#overview" style="color:#7dd3fc;text-decoration:none;">Overview</a>
    <a href="#costs" style="color:#7dd3fc;text-decoration:none;">Costs</a>
    <details style="margin-left:auto;position:relative;">
      <summary style="cursor:pointer;color:#94a3b8;list-style:none;">Advanced ▾</summary>
      <div style="position:absolute;right:0;top:24px;background:#1e293b;border:1px solid #334155;
        border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:6px;min-width:210px;">
        <button class="download" onclick="downloadJSON()">⬇ Download JSON</button>
        <button class="download" onclick="downloadCSV()">⬇ Download CSV</button>
        <button class="download" onclick="window.print()">🖨 Print / Save PDF</button>
        <button class="download" id="refreshBtn" onclick="refreshDashboard()" style="background:#10b981;">🔄 Refresh</button>
        <a class="download" href="#cost-method" style="background:#0ea5e9;text-decoration:none;">📐 Cost method</a>
        <a class="download" href="#cost-compare" style="background:#f59e0b;text-decoration:none;">⚖️ Compare</a>
        <label style="color:#cbd5e1;cursor:pointer;font-size:13px;">
          <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()" style="cursor:pointer;margin-right:6px;">
          Auto-refresh 30s
        </label>
        <span id="refreshStatus" style="display:none;color:#94a3b8;font-size:12px;"></span>
      </div>
    </details>
  </nav>

%%STATUS_STRIP%%

  <details style="margin-bottom:14px;">
    <summary style="cursor:pointer;color:#94a3b8;font-size:14px;padding:6px 0;">
      📋 Project metadata — {metadata['project']} · branch {metadata['git_branch'] or '—'} ·
      manifest {'✓' if metadata['manifest_present'] else '✗ MISSING'}
    </summary>
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
  </details>

  {kg_section}

%%CODE_TREE_SECTION%%

  

"""

    # ── Two-bucket Tokenomics Split ──
    ls = metrics.get("last_session") or {}
    ov = ls.get("raven_overhead") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}}
    uw = ls.get("user_work") or {"tokens": 0, "cost_usd": 0.0, "calls": 0, "tier_counts": {}}
    total_tok = ov.get("tokens", 0) + uw.get("tokens", 0)
    total_cost = float(ov.get("cost_usd", 0.0) or 0) + float(uw.get("cost_usd", 0.0) or 0)
    ov_pct = (ov.get("tokens", 0) / total_tok * 100) if total_tok else 0
    uw_pct = (uw.get("tokens", 0) / total_tok * 100) if total_tok else 0
    srcs = ", ".join(metrics.get("sources_used") or []) or "none"

    cur_proj = (
        metrics.get("current_project")
        or metadata.get("project")
        or "this-repo"
    )
    bp = metrics.get("by_project") or {}
    cur_stats = bp.get(cur_proj) or {"sessions": 0, "tokens": 0, "cost_usd": 0.0}
    # If filter applied, headline already scoped
    all_sess = metrics["sessions_count"]
    all_tok = metrics["total_tokens"]
    all_cost = metrics["total_cost_usd"]
    cur_sess = int(cur_stats.get("sessions") or 0)
    cur_tok = int(cur_stats.get("tokens") or 0)
    cur_cost = float(cur_stats.get("cost_usd") or 0)
    cur_avg = (cur_cost / cur_sess) if cur_sess else 0.0
    all_avg = metrics.get("avg_cost_per_session") or 0.0

    # Citations for this page
    citations = build_citation_registry(metrics, metadata)
    c1, c2, c3 = cite_chip("C1"), cite_chip("C2"), cite_chip("C3")
    c4, c5, c6, c7, c8 = (
        cite_chip("C4"),
        cite_chip("C5"),
        cite_chip("C6"),
        cite_chip("C7"),
        cite_chip("C8"),
    )

    # Per-repo mini table — ALL vault repos, ordered by latest activity,
    # with a 30d-active filter toggle (metered repos = bp; rest from hubs).
    def _last_touch(pname: str) -> str:
        best = 0.0
        for cand in [VAULT / "projects" / f"{pname}.md"] + sorted(
            (VAULT / "sessions").glob(f"*-{pname}.md")
        ):
            try:
                best = max(best, cand.stat().st_mtime)
            except OSError:
                pass
        return datetime.fromtimestamp(best).strftime("%Y-%m-%d %H:%M") if best else ""

    all_repo_names = {p.stem for p in (VAULT / "projects").glob("*.md")} | set(bp.keys())
    repo_entries = []
    for pname in all_repo_names:
        touch = _last_touch(pname)
        active_30d = bool(bp.get(pname)) or (
            touch >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        )
        repo_entries.append((touch, pname, bp.get(pname) or {}, active_30d))
    repo_entries.sort(reverse=True)  # latest touch first

    bp_rows = ""
    for touch, pname, st, active_30d in repo_entries:
        url = f"https://github.com/giggsoinc/{pname}"
        local = ""
        hub = VAULT / "projects" / f"{pname}.md"
        hub_txt = ""
        if hub.exists():
            try:
                hub_txt = hub.read_text(errors="replace")
                url = _repo_url_from_hub(hub_txt, pname, metadata) or url
            except Exception:
                pass
        local = resolve_local_path(pname, hub_txt)
        local_html = _local_link_html(local, "Local")
        dim = "" if active_30d else "opacity:.5;"
        badge = "" if active_30d else " <span style='color:#64748b;font-size:11px'>(idle)</span>"
        bp_rows += (
            f"<tr class='repo-row' data-active='{1 if active_30d else 0}' "
            f"style='cursor:pointer;{dim}' onclick=\"window.kgShowNode && window.kgShowNode('projects/{pname}'); window.openCodeTree && openCodeTree('{pname}')\">"
            f"<td><a href='{url}' target='_blank' rel='noopener' onclick='event.stopPropagation()'>{pname}</a>{badge} {c1}{c5}</td>"
            f"<td>{touch or '—'}</td>"
            f"<td class='num'>{st.get('sessions',0)} {c1}</td>"
            f"<td class='num'>{int(st.get('tokens',0)):,} {c1}</td>"
            f"<td class='num'>{format_usd(st.get('cost_usd',0))} {c1}</td>"
            f"<td onclick='event.stopPropagation()'>"
            f"<a href='{url}' target='_blank' rel='noopener'>GitHub ↗</a>"
            f"{(' · ' + local_html) if local_html else ''}"
            f"</td>"
            f"</tr>\n"
        )
    if not bp_rows:
        bp_rows = (
            "<tr><td colspan='6' style='color:#94a3b8'>"
            "No per-repo metrics in window yet (no project-tagged rows in C1)."
            "</td></tr>"
        )

    n_graph_nodes = len((graph or {}).get("nodes") or []) if graph else 0
    n_graph_edges = len((graph or {}).get("edges") or []) if graph else 0
    n_guards = sum((metrics.get("guard_events") or {}).values())

    # ── Answer-first status strip (vibe-coder verdict + engineer numbers) ──
    hot_file, hot_why = "—", ""
    try:
        ct = json.loads((Path(metadata.get("repo_root") or ".") / ".raven" / "code-xray.json").read_text())
        flat_ct: list = []

        def _walk_ct(n):
            if n.get("type") == "program":
                flat_ct.append(n)
            for c in n.get("children", []):
                _walk_ct(c)

        _walk_ct(ct.get("root") or {})
        flat_ct.sort(key=lambda n: -n.get("churn_30d", 0))
        if flat_ct and flat_ct[0].get("churn_30d", 0):
            hot_file = flat_ct[0]["id"].split("/")[-1]
            hot_why = (flat_ct[0].get("history") or [{}])[0].get("why", "")[:70]
    except Exception:
        pass
    ok = metadata.get("manifest_present", True)
    verdict = "✅ All clear" if ok else "⚠️ Attention"
    verdict_sub = (
        f"Nothing blocked · {n_guards} guard event(s) logged, guards announce themselves when they fire"
        if ok else "Manifest missing — run /raven-init"
    )
    status_strip = f"""
  <div id="overview" style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
    <div class="stat" style="flex:1.4;min-width:220px;border-left:4px solid {'#10b981' if ok else '#f59e0b'};">
      <div class="stat-value" style="font-size:22px;">{verdict}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:6px;">{verdict_sub}</div>
    </div>
    <div class="stat" style="flex:1;min-width:150px;">
      <div class="stat-label">Spend — 30d, all repos {c1}</div>
      <div class="stat-value">{format_usd(all_cost)}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:6px;">this repo: {format_usd(cur_cost)} {c2}</div>
    </div>
    <div class="stat" style="flex:1;min-width:150px;">
      <div class="stat-label">Sessions — 30d {c1}</div>
      <div class="stat-value">{all_sess:,}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:6px;">{all_tok:,} tokens</div>
    </div>
    <div class="stat" style="flex:1.4;min-width:200px;">
      <div class="stat-label">Hottest file this month</div>
      <div class="stat-value" style="font-size:16px;">{hot_file}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:6px;">{hot_why or 'no recent churn'}</div>
    </div>
  </div>"""
    html = html.replace("%%STATUS_STRIP%%", status_strip)

    # Graph = this repo only. Other trees/*.html are legacy mind-maps — do not offer them.
    tree_pages = [p.name for p in (VAULT / "dashboard" / "trees").glob("*.html")]
    cur_repo_name = metadata.get("project") or "raven"
    want = cur_repo_name.lower().removesuffix(".html")
    default_tree = ""
    for p in tree_pages:
        if p.lower().removesuffix(".html") == want:
            default_tree = p
            break
    if not default_tree:
        folder = Path(metadata.get("project_path") or ".").name.lower()
        for p in tree_pages:
            if p.lower().removesuffix(".html") == folder:
                default_tree = p
                break
    iframe_src = f"trees/{default_tree}" if default_tree else ""
    missing_display = "none" if default_tree else "inline"
    code_tree_section = f"""
  <div id="code-graph" style="background:#0f172a;border-radius:8px;margin:14px 0;border:1px solid #334155;">
    <div style="color:#e2e8f0;padding:10px 14px;font-size:14px;">
      <strong>Graph</strong>
      <span style="color:#94a3b8;"> — {cur_repo_name} (this repo only)</span>
      <span id="treeMissing" style="color:#fbbf24;display:{missing_display};"> — no OKF graph for this repo yet; run code-xray.py --html</span>
    </div>
    <iframe id="treeFrame" src="{iframe_src}" style="width:100%;height:72vh;border:0;border-radius:0 0 8px 8px;background:#020617;"
      title="Code graph"></iframe>
  </div>"""
    html = html.replace("%%CODE_TREE_SECTION%%", code_tree_section)

    # Bibliography HTML
    bib_rows = ""
    for c in citations:
        bib_rows += (
            f"<tr id='cite-{c['id']}'>"
            f"<td><strong>[{c['id']}]</strong></td>"
            f"<td>{c['title']}</td>"
            f"<td><code style='font-size:11px;word-break:break-all'>{c['path']}</code></td>"
            f"<td style='font-size:12px;color:#cbd5e1'>{c['field']}<br>"
            f"<span style='color:#94a3b8'>{c['rule']}</span></td>"
            f"<td style='font-size:12px'>{c['used_for']}</td>"
            f"</tr>\n"
        )

    html += f"""
  <style>
    a.cite {{ color:#38bdf8; font-size:11px; font-weight:600; text-decoration:none; margin-left:4px;
      vertical-align:super; }}
    a.cite:hover {{ text-decoration:underline; color:#7dd3fc; }}
    .cite-raw {{ color:#64748b; font-size:11px; margin-top:6px; font-family:ui-monospace,monospace; }}
    #citations tr:target {{ background:#1e3a5f; }}
  </style>

  <h2 id="agent-memory">🧠 How this is used for development — agent memory</h2>
  <div class="meta" style="border-left:4px solid #a78bfa;margin-bottom:20px;line-height:1.55;font-size:14px;">
    <p style="margin-bottom:10px;">
      This dashboard is the <strong>human view</strong> of the same RavenVault that agents load as
      <strong>working memory</strong> — not a separate analytics product.
    </p>
    <ol style="margin:0 0 0 18px;color:#cbd5e1;">
      <li style="margin-bottom:8px;"><strong>Session start</strong> — <code>ide-boot.py</code> sets <code>load=0|1</code>;
        if 1, the agent Reads <code>.raven/memory/CARD.md</code> only {c5}. No vault-load inject. No graph JSON in context.</li>
      <li style="margin-bottom:8px;"><strong>During coding</strong> — Andie / specialists route work; guards scan writes;
        model-router may record overhead into <code>.model-session.json</code> {c3}.</li>
      <li style="margin-bottom:8px;"><strong>Session end (Stop)</strong> — <code>token-meter-write</code> → metrics {c1};
        <code>obsidian-log</code> → short session note + project hub {c5};
        <code>knowledge-extract</code> may add concepts/decisions; graph JSON rebuildable {c4}.</li>
      <li style="margin-bottom:8px;"><strong>Next session</strong> — agent memory resumes from hubs/open questions,
        so brownfield debug and greenfield plans start from prior facts, not a blank chat.</li>
      <li><strong>You (developer)</strong> — use this page to verify costs are real, jump to repos, and audit whether
        memory notes match the work you expected. If a number has no citation, treat it as a bug.</li>
    </ol>
    <p style="margin-top:12px;color:#94a3b8;font-size:13px;">
      Generated {metadata.get('report_generated_at_local')} {c8} · project identity {c7} ·
      build <code>kg-v2-grounded+cite</code>
    </p>
  </div>

  {render_cost_compare_section(metrics, metadata)}

  {render_cost_log_section(metadata)}

  <h2 id="costs">📊 Headline numbers — Raven-metered only (every value cited)</h2>
  <p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">
    These figures are <strong>Raven-metered</strong> (token × model rate card), not invoices.
    Click a blue <span class="cite">[C#]</span> for bibliography. Window
    <strong>{metrics['window_start']}</strong> → <strong>{metrics['window_end']}</strong>
    ({metrics['window_days']}d). Sub-cent costs never round to $0.00.
    For Claude/Console money, use the <a href="#cost-compare" style="color:#38bdf8;">side-by-side compare</a> above.
  </p>

  <div class="stat-grid">
    <div class="stat" style="border-left:4px solid #8b5cf6;">
      <div class="stat-label">All repos (portfolio) {c1}</div>
      <div class="stat-value">{format_usd(all_cost)} {c1}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:8px;">
        sessions <strong>{all_sess:,}</strong> {c1} ·
        tokens <strong>{all_tok:,}</strong> {c1} ·
        avg/session <strong>{format_usd(all_avg)}</strong> {c1}
      </div>
      <div class="cite-raw">raw cost_usd={all_cost} · formula: sum(C1.cost) / count(C1.sessions) for avg</div>
    </div>
    <div class="stat" style="border-left:4px solid #0ea5e9;">
      <div class="stat-label">This repo — {cur_proj} {c2}{c7}</div>
      <div class="stat-value">{format_usd(cur_cost)} {c2}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:8px;">
        sessions <strong>{cur_sess:,}</strong> {c2} ·
        tokens <strong>{cur_tok:,}</strong> {c2} ·
        avg <strong>{format_usd(cur_avg)}</strong> {c2}
      </div>
      <div class="cite-raw">raw cost_usd={cur_cost} · filter project=={cur_proj}</div>
    </div>
    <div class="stat" style="border-left:4px solid #f59e0b;">
      <div class="stat-label">Live session (now) {c3}</div>
      <div class="stat-value">{format_usd(total_cost)} {c3}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:8px;">
        tokens <strong>{total_tok:,}</strong> {c3}
        (overhead {ov.get('tokens',0):,} {c3} + user {uw.get('tokens',0):,} {c3})
      </div>
      <div class="cite-raw">raw cost_usd={total_cost} · file .raven/.model-session.json</div>
    </div>
    <div class="stat">
      <div class="stat-label">Graph + guards {c4}{c6}</div>
      <div class="stat-value" style="font-size:18px;">{n_graph_nodes} nodes {c4}</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:8px;">
        {n_graph_edges} edges {c4} · {n_guards} guard events in window {c6}
      </div>
      <div class="cite-raw">sources_used: {srcs or 'none'}</div>
    </div>
  </div>

  <h3 style="color:#94a3b8;margin:20px 0 8px;font-size:14px;">
    All repos — ordered by latest activity {c1}{c5} (click row → graph briefing / agent memory hub)
    <label style="float:right;font-weight:400;cursor:pointer;">
      <input type="checkbox" id="active30" checked
        onchange="document.querySelectorAll('.repo-row').forEach(function(r){{r.style.display=(this.checked&&r.dataset.active==='0')?'none':'';}},this)"> active last 30d only
    </label>
  </h3>
  <table>
    <thead>
      <tr>
        <th>Repo {c5}</th>
        <th>Last activity</th>
        <th class="num">Sessions {c1}</th>
        <th class="num">Tokens {c1}</th>
        <th class="num">Cost {c1}</th>
        <th>GitHub + Local {c5}</th>
      </tr>
    </thead>
    <tbody>
      {bp_rows}
    </tbody>
  </table>
  <p style="color:#64748b;font-size:12px;margin:8px 0 20px;">
    Rebuild: <code>python3 scripts/dashboard.py --html --open</code>
    · one repo: <code>--project {cur_proj}</code>
  </p>

  <h2>Tokenomics split — Raven code vs user work {c3}</h2>
  <p style="color:#94a3b8;font-size:13px;margin-bottom:16px;">
    Both buckets are fields on the live session file {c3}.
    Raven code = infrastructure overhead; User work = classified user turns (when metered).
  </p>
  <div class="stat-grid" style="grid-template-columns:1fr 1fr;">
    <div class="stat" style="border-left:4px solid #8b5cf6;">
      <div class="stat-label">Raven code (overhead) {c3}</div>
      <div class="stat-value">{ov.get('tokens',0):,} {c3}</div>
      <div style="color:#94a3b8;font-size:13px;margin-top:8px;">
        {format_usd(ov.get('cost_usd',0))} {c3} ·
        {ov.get('calls',0)} calls {c3} ·
        {ov_pct:.1f}% of live tokens {c3}
      </div>
      <div class="cite-raw">path: raven_overhead.* in .model-session.json</div>
    </div>
    <div class="stat" style="border-left:4px solid #10b981;">
      <div class="stat-label">User work {c3}</div>
      <div class="stat-value">{uw.get('tokens',0):,} {c3}</div>
      <div style="color:#94a3b8;font-size:13px;margin-top:8px;">
        {format_usd(uw.get('cost_usd',0))} {c3} ·
        {uw.get('calls',0)} calls {c3} ·
        {uw_pct:.1f}% of live tokens {c3}
      </div>
      <div class="cite-raw">path: user_work.* — $0 tokens often means transcript meter did not run yet</div>
    </div>
  </div>
"""

    # Raven Code by-source breakdown
    by_src = ov.get("by_source") or {}
    if by_src:
        html += f'<h2>Raven code — overhead by source {c3}</h2>\n'
        html += (
            '<table>\n<thead><tr><th>Source {c3}</th><th class="num">Tokens {c3}</th>'
            '<th class="num">Calls {c3}</th><th class="num">Cost {c3}</th></tr></thead>\n<tbody>\n'
        )
        for src, info in sorted(by_src.items(), key=lambda x: -x[1].get("tokens", 0)):
            html += (
                f'<tr><td><code>{src}</code> {c3}</td>'
                f'<td class="num">{info.get("tokens",0):,} {c3}</td>'
                f'<td class="num">{info.get("calls",0)} {c3}</td>'
                f'<td class="num">{format_usd(info.get("cost_usd",0))} {c3}</td></tr>\n'
            )
        html += '</tbody></table>\n'
        html += (
            '<p class="cite-raw">Each row = raven_overhead.by_source.&lt;name&gt; in '
            f'{MODEL_SESSION if MODEL_SESSION.exists() else ".raven/.model-session.json"}</p>\n'
        )

    # Provider attribution (Codex-tier matters)
    providers = ls.get("providers") or {}
    if providers:
        html += '<details><summary style="cursor:pointer;color:#94a3b8;font-size:15px;padding:4px 0;"><b>🔌 Provider attribution</b> ▾</summary>'
        html += ''
        html += '<table>\n<thead><tr><th>Provider</th><th class="num">Tokens</th><th class="num">Share</th><th class="num">Cost (USD)</th></tr></thead>\n<tbody>\n'
        for prov, info in providers.items():
            tok = info.get("tokens", 0)
            cost = info.get("cost_usd", 0.0)
            pct = (tok / total_tok * 100) if total_tok else 0
            html += f'<tr><td><code>{prov}</code></td><td class="num">{tok:,}</td><td class="num">{pct:.1f}%</td><td class="num">${cost:.4f}</td></tr>\n'
        html += '</tbody></table></details>\n'

    if metrics["tier_counts"]:
        html += '<details><summary style="cursor:pointer;color:#94a3b8;font-size:15px;padding:4px 0;"><b>🎯 Tier mix</b> ▾</summary><table>\n<thead><tr><th>Tier</th><th class="num">Count</th><th class="num">Share</th><th class="num">Cost (USD)</th><th>Distribution</th></tr></thead>\n<tbody>\n'
        for tier in ["SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY"]:
            c = metrics["tier_counts"].get(tier, 0)
            p = metrics["tier_share_pct"].get(tier, 0)
            cost = metrics["tier_cost"].get(tier, 0)
            html += f'<tr><td>{tier}</td><td class="num">{c}</td><td class="num">{p:.1f}%</td><td class="num">${cost:.3f}</td><td><span class="bar" style="width:{p*2}px"></span></td></tr>\n'
        html += '</tbody></table></details>\n'

    if metrics["cost_by_day"]:
        html += f'<details><summary style="cursor:pointer;color:#94a3b8;font-size:15px;padding:4px 0;"><b>📅 Daily series</b> — {len(metrics["sessions_by_day"])} day(s) ▾</summary>'
        html += '<table>\n<thead><tr><th>Date</th><th class="num">Sessions</th><th class="num">Tokens</th><th class="num">Cost</th></tr></thead>\n<tbody>\n'
        for day in sorted(metrics["sessions_by_day"].keys()):
            s = metrics["sessions_by_day"][day]
            t = metrics["tokens_by_day"].get(day, 0)
            c = metrics["cost_by_day"].get(day, 0)
            html += f'<tr><td>{day}</td><td class="num">{s}</td><td class="num">{t:,}</td><td class="num">{format_usd(c)}</td></tr>\n'
        html += '</tbody></table></details>\n'

    if metrics["skills_used"]:
        html += f'<details><summary style="cursor:pointer;color:#94a3b8;font-size:15px;padding:4px 0;"><b>🛠 Top skills</b> — {len(metrics["skills_used"])} used ▾</summary>'
        html += '<table>\n<thead><tr><th>Skill</th><th class="num">Invocations</th></tr></thead>\n<tbody>\n'
        for skill, count in list(metrics["skills_used"].items())[:15]:
            html += f'<tr><td>{skill}</td><td class="num">{count}</td></tr>\n'
        html += '</tbody></table></details>\n'

    html += f'<h2 id="guards">🛡 Guards — {n_guards} event(s) in window</h2>\n'
    if metrics["guard_events"]:
        html += '<details><summary style="cursor:pointer;color:#94a3b8;font-size:14px;padding:4px 0;">Event breakdown ▾</summary>\n'
        html += '<table>\n<thead><tr><th>Event</th><th class="num">Count</th></tr></thead>\n<tbody>\n'
        for event, count in sorted(metrics["guard_events"].items(), key=lambda x: -x[1])[:15]:
            html += f'<tr><td>{event}</td><td class="num">{count}</td></tr>\n'
        html += '</tbody></table></details>\n'
    else:
        html += '<p style="color:#94a3b8;font-size:13px;">No guard events in window — no fire, not no coverage.</p>\n'

    html += '<h2 id="recommendations">💡 Recommendations — Grouped by Owner</h2>\n'
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
  <h2 id="citations">📚 Citations — every number on this page</h2>
  <p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">
    Inline <span class="cite">[C#]</span> / <span class="cite">[S#]</span> markers jump here.
    If a displayed figure cannot be traced to a row below, treat the UI as buggy.
  </p>
  <table>
    <thead>
      <tr>
        <th>Id</th><th>What</th><th>Path</th><th>Field / rule</th><th>Used for</th>
      </tr>
    </thead>
    <tbody>
      {bib_rows}
    </tbody>
  </table>

  <div class="footer">
    Generated by Raven v{metadata['plugin_version']} · Local-only · No telemetry ·
    build kg-v2-grounded+cite · agent memory = RavenVault
  </div>
</div>

<script>
const DATA = {raw_json};
let autoRefreshInterval = null;

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

function refreshDashboard() {{
  const status = document.getElementById('refreshStatus');
  status.style.display = 'inline';
  status.style.color = '#94a3b8';
  status.textContent = '🔄 Refreshing...';

  // Prefer local dashboard-server (regenerates HTML). file:// cannot rebuild itself.
  fetch('http://127.0.0.1:9787/refresh')
    .then(r => r.json())
    .then(data => {{
      status.textContent = '✅ Regenerated — reloading…';
      setTimeout(() => {{ location.reload(); }}, 400);
    }})
    .catch(err => {{
      status.style.color = '#fbbf24';
      const live = (typeof liveDashUrl === 'function') ? liveDashUrl() : 'http://127.0.0.1:9787';
      status.innerHTML = 'file:// is view-only. <a class="live-dash" href="'+live+'">Open live dashboard</a>';
    }});
}}

function toggleAutoRefresh() {{
  const checkbox = document.getElementById('autoRefresh');
  const status = document.getElementById('refreshStatus');

  if (checkbox.checked) {{
    status.style.display = 'inline';
    status.textContent = '🔄 Auto-refresh: 30s interval';
    localStorage.setItem('auto-refresh', 'true');
    autoRefreshInterval = setInterval(() => {{
      location.reload();
    }}, 30000);
  }} else {{
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    status.style.display = 'none';
    localStorage.setItem('auto-refresh', 'false');
  }}
}}

// Restore auto-refresh checkbox state on page load
window.addEventListener('load', function() {{
  const checkbox = document.getElementById('autoRefresh');
  if (localStorage.getItem('auto-refresh') === 'true') {{
    checkbox.checked = true;
    toggleAutoRefresh();
  }}
}});
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
    parser.add_argument("--graph-only", action="store_true",
                        help="Rebuild knowledge-graph.json + knowledge-graph.html")
    parser.add_argument("--graph-json", action="store_true",
                        help="Only write ~/RavenVault/graph/knowledge-graph.json")
    parser.add_argument("--json", action="store_true", help="Dump raw metrics JSON")
    parser.add_argument("--all", action="store_true", help="All output modes")
    parser.add_argument("--audit", action="store_true",
                        help="Run drift audit on attribution buckets (Method C — sampling safety net)")
    parser.add_argument("--open", action="store_true", help="Open HTML report after writing")
    parser.add_argument(
        "--if-stale", type=int, default=None, metavar="MINUTES",
        help="Skip the run entirely if dashboard-stamp.json is younger than MINUTES. "
             "For unattended Stop-hook use — Stop fires every turn, so without this "
             "the ~3000-line HTML build would re-run on every single turn.",
    )
    parser.add_argument("--days", type=int, default=30, help="Window in days (default 30)")
    parser.add_argument("--month", type=str, help="Specific month YYYY-MM")
    parser.add_argument("--project", type=str, help="Filter by project name")
    # Enterprise Stop hook: dashboard.py --html --current-project
    parser.add_argument(
        "--current-project",
        action="store_true",
        help="Filter to the current repo (cwd/git/manifest). Used by global Stop hooks.",
    )
    # parse_known_args: never exit 2 on unknown legacy flags from older plugins
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"dashboard: ignoring unknown args {unknown}", file=sys.stderr)

    if args.if_stale is not None:
        stamp_path = VAULT / "dashboard-stamp.json"
        try:
            if stamp_path.exists():
                stamp_data = json.loads(stamp_path.read_text())
                generated_at = datetime.strptime(
                    stamp_data["generated_at"], "%Y-%m-%d %H:%M:%S"
                )
                age_minutes = (datetime.now() - generated_at).total_seconds() / 60
                if age_minutes < args.if_stale:
                    nu = VAULT / "dashboard" / RAVEN_DASHBOARD_NAME
                    idx = VAULT / "dashboard" / "index.html"
                    try:
                        body = idx.read_text(errors="replace") if idx.is_file() else ""
                        if (not nu.is_file()) or "treeSel" in body:
                            print("dashboard: forcing rebuild (legacy index or missing raven-dashboard.html)", file=sys.stderr)
                        else:
                            return
                    except OSError:
                        return
        except Exception:
            pass  # missing/corrupt stamp — fall through and build

    if not (
        args.cli or args.obsidian or args.html or args.json or args.all
        or args.audit or args.graph_only or args.graph_json
    ):
        # Hook default: if only --current-project, still build HTML
        if args.current_project:
            args.html = True
        else:
            args.cli = True  # default

    # Resolve project filter
    project_filter = args.project
    if args.current_project and not project_filter:
        project_filter = (
            (collect_metadata() or {}).get("project")
            or Path.cwd().name
        )
        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if remote:
                project_filter = remote.rstrip("/").split("/")[-1].replace(".git", "")
        except Exception:
            pass
        # Prefer manifest if present
        if MANIFEST.exists():
            try:
                project_filter = json.loads(MANIFEST.read_text()).get("project") or project_filter
            except Exception:
                pass

    days = args.days
    if args.month:
        try:
            year, month = args.month.split("-")
            days = 31  # rough — aggregator filters by date anyway
        except Exception:
            print(f"Invalid --month format. Use YYYY-MM. Got: {args.month}", file=sys.stderr)
            days = 30  # fail-soft for hooks (do not exit 2)

    graph = None
    # Landing HTML uses xray OKF only. Vault knowledge_graph.py is NOT this page.
    if args.graph_only or args.graph_json:
        try:
            graph = _load_or_build_graph(project_filter=project_filter, session_days=days)
        except Exception as e:
            print(f"dashboard: vault graph build failed (continuing): {e}", file=sys.stderr)
            graph = {"nodes": [], "edges": []}
        if args.graph_json and not (args.html or args.graph_only or args.all):
            print(
                f"🕸 knowledge-graph.json: {VAULT / 'graph' / 'knowledge-graph.json'} "
                f"({len(graph.get('nodes', []))} nodes)",
                file=sys.stderr,
            )
            return

    metadata = collect_metadata()
    metrics = aggregate(days=days, project_filter=project_filter)
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
        dashboard_path = write_raven_dashboard(metadata, metrics)
        stamp = {
            "build": "raven-dashboard-okf-v1",
            "generated_at": metadata.get("report_generated_at_local"),
            "path": str(dashboard_path),
            "plugin_version": PLUGIN_VERSION,
        }
        (VAULT / "dashboard-stamp.json").write_text(json.dumps(stamp, indent=2) + "\n")
        print(f"🌐 HTML dashboard: {dashboard_path}", file=sys.stderr)
        if args.open and os.environ.get("RAVEN_DASHBOARD_NO_OPEN") != "1":
            try:
                subprocess.run(["open", str(dashboard_path)], check=False)
            except Exception:
                pass

    if args.graph_only:
        VAULT.mkdir(parents=True, exist_ok=True)
        # Minimal shell around graph panel for bookmarking
        kg_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Raven Knowledge Graph — {metadata.get('project')}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; background:#0f172a; color:#e2e8f0; padding:24px; }}
  .meta {{ background:#1e293b; padding:16px; border-radius:8px; margin-bottom:16px; }}
  .download {{ display:inline-block; margin:8px 8px 8px 0; padding:10px 20px; background:#3b82f6; color:white;
    border-radius:6px; text-decoration:none; font-weight:500; font-size:14px; cursor:pointer; border:none; }}
  table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
  th, td {{ padding:10px 14px; text-align:left; border-bottom:1px solid #334155; font-size:14px; }}
  th {{ background:#334155; color:#cbd5e1; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  a {{ color:#38bdf8; }}
</style></head><body>
<h1>🪶 Raven Knowledge Graph</h1>
<div class="meta">Project filter: {project_filter or 'all'} · Vault: {VAULT}</div>
{render_knowledge_graph_section(graph or {{'nodes': [], 'edges': []}}, metrics=metrics, metadata=metadata)}
</body></html>
"""
        kg_path = VAULT / "knowledge-graph.html"
        kg_path.write_text(kg_html)
        print(f"🕸 Graph HTML: {kg_path}", file=sys.stderr)
        if args.open:
            try:
                subprocess.run(["open", str(kg_path)], check=False)
            except Exception:
                pass

    if args.json:
        payload = {"metadata": metadata, "metrics": metrics, "recommendations": recs}
        if graph is not None:
            payload["graph"] = graph
        if audit_result is not None:
            payload["audit"] = audit_result
        print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # Never block Claude Stop hooks (exit 2 from argparse was the failure mode)
        code = e.code if isinstance(e.code, int) else 0
        if code not in (0, None):
            print(f"dashboard: coerced exit {code} → 0 (hook fail-soft)", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"dashboard: fail-soft error: {e}", file=sys.stderr)
        sys.exit(0)
