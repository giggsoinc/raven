#!/usr/bin/env python3
"""
Model Router v1 — Dynamic Model Routing for Raven

Classifies user queries and context into tiers (SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY)
based on signal detection, and outputs routing decision to .raven/.model-session.json.

Usage:
  - Library: from model_router import classify
    tier, score, reasons, model = classify(prompt, context)

  - CLI: python3 model-router.py --prompt "..." [--context "{...}"]
"""

import argparse
import json
import hashlib
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict


# Signal definitions (keywords, weights)
SECURITY_KEYWORDS = {
    "vuln", "vulnerability", "cve", "exploit", "auth", "authentication",
    "token", "jwt", "oauth", "injection", "sql", "xss", "csrf", "credential",
    "secret", "password", "key", "cipher", "encrypt", "decrypt", "hash",
    "breach", "attack", "malicious", "threat", "vulnerability"
}

ARCHITECTURE_KEYWORDS = {
    "design", "schema", "database", "migrate", "migration", "refactor",
    "refactoring", "plan", "tradeoff", "architecture", "pattern",
    "structure", "class", "interface", "module", "component", "system",
    "api", "endpoint", "route", "handler", "service", "layer"
}

REASONING_KEYWORDS = {
    "compare", "which", "approach", "pros", "cons", "tradeoff", "should",
    "recommendation", "best", "optimal", "efficient", "trade-off",
    "advantage", "disadvantage", "alternative"
}


def _score_signal(prompt: str, context: str) -> Tuple[int, List[str]]:
    """
    Score the prompt and context on signal presence.

    Returns:
        (total_score, list_of_reasons)
    """
    score = 0
    reasons = []

    # Combine prompt and context for searching
    combined = f"{prompt} {context}".lower()

    # Security keywords (+3)
    for keyword in SECURITY_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"security_keyword:{keyword}")
            break  # Count once per category

    # Architecture keywords (+3)
    for keyword in ARCHITECTURE_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"architecture_keyword:{keyword}")
            break  # Count once per category

    # Reasoning keywords (+3)
    for keyword in REASONING_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"reasoning_keyword:{keyword}")
            break  # Count once per category

    # Multi-file scope (+2): references to multiple files
    file_count = len(re.findall(r'\b[a-z_]+\.(py|ts|js|go|java|rs|sql)\b', prompt))
    if file_count >= 3:
        score += 2
        reasons.append(f"multi_file_scope:{file_count}_files")
    elif "across the codebase" in prompt.lower() or "across" in prompt.lower():
        score += 2
        reasons.append("multi_file_scope:across_codebase")

    # Test/doc generation (+1)
    if any(x in prompt.lower() for x in ["write test", "write tests", "write unit test", "write unittest", "document", "docstring", "generate test"]):
        score += 1
        reasons.append("test_or_doc_generation")

    # Debugging with stack trace (+1)
    if "traceback" in combined or "error:" in combined or "failed" in combined:
        score += 1
        reasons.append("debugging_with_error")

    # Single-file bounded edit (-1): "fix typo", "rename variable", etc.
    if any(x in prompt.lower() for x in ["fix typo", "rename", "what does", "what is", "return"]):
        if not any(x in prompt.lower() for x in ["across", "multiple", "several"]):
            score = max(0, score - 1)
            reasons.append("single_file_bounded_edit")

    return score, reasons


def _detect_secrets(context: str) -> bool:
    """
    Detect if secrets or sensitive credentials are present in context.

    FORCE → LOCAL_ONLY if true.
    """
    # Check for common secret patterns
    secret_patterns = [
        r'manifest\.secrets',
        r'\.env',
        r'SECRET_KEY\s*=',
        r'API_KEY\s*=',
        r'password\s*=',
        r'token\s*=',
        r'private\s+key',
        r'-----BEGIN',
        r'-----END',
    ]

    context_lower = context.lower()
    for pattern in secret_patterns:
        if re.search(pattern, context_lower, re.IGNORECASE):
            return True

    # Check for credential markers in context
    if any(x in context for x in ['PRIVATE', 'SECRET', '-----BEGIN']):
        return True

    return False


def _find_project_root() -> Path:
    """Walk up from cwd to the nearest .git directory. Falls back to cwd."""
    d = Path.cwd()
    for candidate in [d, *d.parents]:
        if (candidate / ".git").is_dir():
            return candidate
    return d


def detect_host(env: Optional[Dict] = None) -> str:
    """Same host keys as ide-boot / .raven/boot.json."""
    env = env if env is not None else os.environ
    boot = _find_project_root() / ".raven" / "boot.json"
    hosts = {}
    try:
        hosts = json.loads(boot.read_text(encoding="utf-8")).get("hosts") or {}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    for name, spec in hosts.items():
        for key in (spec or {}).get("env_any") or []:
            if env.get(key):
                return name
    root = _find_project_root()
    if (root / ".agents" / "agents.md").is_file() or (root / ".agents" / "AGENTS.md").is_file():
        return "antigravity"
    return "unknown"


def _educate_mode() -> str:
    try:
        edu = _find_project_root() / ".raven" / "educate.json"
        if not edu.is_file():
            return "guided"
        data = json.loads(edu.read_text(encoding="utf-8"))
        mode = data if isinstance(data, str) else (data or {}).get("mode")
        mode = str(mode or "guided").strip().lower()
        if mode in ("auto", "lucky", "off"):
            return "off"
        return "guided"
    except Exception:
        return "guided"


def _host_rules(host: str) -> str:
    """Rules file path for this host from .raven/boot.json."""
    boot = _find_project_root() / ".raven" / "boot.json"
    try:
        data = json.loads(boot.read_text(encoding="utf-8"))
        hosts = data.get("hosts") or {}
        rules = (hosts.get(host) or {}).get("rules")
        if rules:
            return str(rules)
        return str(data.get("default_rules") or "AGENTS.md")
    except (OSError, json.JSONDecodeError, TypeError):
        return "AGENTS.md"


def format_turn_toast(tier: str, model: str, reasons: List[str], host: str = "", prompt_chars: int = 0) -> str:
    """One line every turn: host, tier, recommend, why, applied=false."""
    host = host or detect_host()
    why = ", ".join(r.split(":", 1)[0] for r in (reasons or [])[:2]) or "no strong signals"
    spawn = ""
    if host == "grok" and model == "grok-4.5":
        spawn = " · MUST spawn_subagent model=grok-4.5"
    elif host == "grok" and model == "grok-4.6":
        spawn = " · stay grok-4.6"
    money = ""
    try:
        _cc_dir = Path(__file__).resolve().parents[1] / "session"
        if str(_cc_dir) not in sys.path:
            sys.path.insert(0, str(_cc_dir))
        from cost_calc import start_money_line
        money = start_money_line(model, prompt_chars or 0)
    except Exception:
        money = "💰 total-cost=? last_turn=? est=?"
    edu = _educate_mode()
    return (
        f"🔀 Router · host={host} · {tier} → recommend {model} "
        f"· why: {why} · applied=false until spawn{spawn}\n{money}\n"
        f"educate={edu} expected={model}"
    )


def _host_tier_defaults(host: str) -> Dict[str, str]:
    boot = _find_project_root() / ".raven" / "boot.json"
    try:
        hosts = json.loads(boot.read_text(encoding="utf-8")).get("hosts") or {}
        tiers = (hosts.get(host) or {}).get("tiers") or {}
        if isinstance(tiers, dict) and tiers:
            out = {k: str(v) for k, v in tiers.items() if k in ("SIMPLE", "MEDIUM", "COMPLEX", "LOCAL_ONLY")}
            if out:
                return out
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    if host == "claude":
        return {
            "SIMPLE": "anthropic/claude-haiku-4-5",
            "MEDIUM": "anthropic/claude-sonnet-5",
            "COMPLEX": "anthropic/claude-sonnet-5-high",
            "LOCAL_ONLY": "ollama/dolphin-mistral",
        }
    return {
        "SIMPLE": f"{host}-fast" if host != "unknown" else "session-fast",
        "MEDIUM": host if host != "unknown" else "session-default",
        "COMPLEX": f"{host}-high" if host != "unknown" else "session-high",
        "LOCAL_ONLY": "ollama/dolphin-mistral",
    }


def _load_model_env(host: str = "") -> Dict[str, str]:
    """Tier map for this IDE. boot.json hosts.*.tiers, then .model.env [routing.HOST] or [routing]."""
    host = host or detect_host()
    defaults = _host_tier_defaults(host)
    model_env_path = _find_project_root() / ".model.env"
    if not model_env_path.exists():
        model_env_path = Path.home() / ".model.env"
    if not model_env_path.exists():
        return defaults

    models = dict(defaults)
    host_section = f"[routing.{host}]"
    current = None
    host_hit = False
    try:
        with open(model_env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if line.startswith("["):
                    current = line
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                tier = key.strip()
                if tier not in ("LOCAL_ONLY", "SIMPLE", "MEDIUM", "COMPLEX"):
                    continue
                if current == host_section:
                    models[tier] = val.strip()
                    host_hit = True
                elif current == "[routing]" and host in ("claude", "unknown") and not host_hit:
                    models[tier] = val.strip()
    except Exception as e:
        print(f"Warning: Failed to parse .model.env: {e}", file=sys.stderr)

    for tier, default_model in defaults.items():
        if tier not in models:
            models[tier] = default_model
    return models


def classify(
    prompt: str,
    context: str = ""
) -> Tuple[str, int, List[str], str]:
    """
    Classify a query into tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY.

    Args:
        prompt: User query text
        context: Additional context (e.g., previous messages, file content)

    Returns:
        (tier, score, reasons, model_string)
    """
    # Force LOCAL_ONLY if secrets detected
    if _detect_secrets(context):
        return "LOCAL_ONLY", 999, ["secrets_in_context"], "local_only"

    # Score the query
    score, reasons = _score_signal(prompt, context)

    # Assign tier based on score
    if score >= 6:
        tier = "COMPLEX"
    elif score >= 3:
        tier = "MEDIUM"
    else:
        tier = "SIMPLE"

    host = detect_host()
    models = _load_model_env(host)
    model_string = models.get(tier, models.get("MEDIUM", "session-default"))

    return tier, score, reasons, model_string


def write_session_json(tier: str, score: int, reasons: List[str], model: str, prompt: str, source: str = "user_work") -> Path:
    """
    Write classification result to .raven/.model-session.json.

    Two-bucket schema:
      - raven_overhead: tokens from Raven internals (hooks, skill loads, banners)
      - user_work: tokens from the user's actual prompt + Claude's response

    Default source = user_work (this is the typical case — Claude is responding
    to a user prompt). When called from a hook context that's purely overhead,
    pass --source raven_overhead.

    Returns:
        Path to written file
    """
    raven_dir = Path.cwd() / ".raven"
    raven_dir.mkdir(exist_ok=True)

    session_file = raven_dir / ".model-session.json"

    # Load existing or init two-bucket schema
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
        except Exception:
            data = {}
    else:
        data = {}

    # Backfill missing schema keys only — never reset keys that already hold
    # real data. token-meter-write.py (Stop hook) may have already populated
    # user_work.tokens/cost_usd from actual transcript usage; wiping the file
    # here on every UserPromptSubmit call would erase that real data (this was
    # the root cause of user_work always reading back as 0 tokens/$0).
    data.setdefault("session_started_at", datetime.utcnow().isoformat() + "Z")
    data.setdefault("raven_overhead", {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}})
    data.setdefault("user_work", {
        "tokens": 0,
        "cost_usd": 0.0,
        "calls": 0,
        "tier_counts": {"SIMPLE": 0, "MEDIUM": 0, "COMPLEX": 0, "LOCAL_ONLY": 0},
        "last_classification": None,
    })
    data["user_work"].setdefault("tier_counts", {"SIMPLE": 0, "MEDIUM": 0, "COMPLEX": 0, "LOCAL_ONLY": 0})
    data.setdefault("providers", {})

    # Update the appropriate bucket
    bucket = data[source] if source in ("user_work", "raven_overhead") else data["user_work"]
    bucket["calls"] += 1
    if source == "user_work":
        bucket["tier_counts"][tier] = bucket["tier_counts"].get(tier, 0) + 1
        bucket["last_classification"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_query_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "tier": tier,
            "score": score,
            "reasons": reasons,
            "model_for_tier": model,
            "recommended_model": model,
            "host": detect_host(),
            "applied": False,
            "note": "recommended only — session model unchanged unless this IDE swapped (LiteLLM not wired)",
            "prompt_chars": len(prompt),
        }
        try:
            _cc_dir = Path(__file__).resolve().parents[1] / "session"
            if str(_cc_dir) not in sys.path:
                sys.path.insert(0, str(_cc_dir))
            from cost_calc import estimate as _est
            est = _est(model, len(prompt))
            bucket["last_classification"].update({
                "est_cost_usd": est.get("est_cost_usd"),
                "tokens_in_est": est.get("tokens_in_est"),
                "needs_rate": est.get("needs_rate"),
                "in_router": est.get("in_router"),
            })
        except Exception:
            pass

    # Write atomically
    try:
        session_file.write_text(json.dumps(data, indent=2))
        return session_file
    except Exception as e:
        print(f"Error writing {session_file}: {e}", file=sys.stderr)
        raise


ROUTER_STATE_FILE = ".router-state.json"


def _router_state_path() -> Path:
    return _find_project_root() / ".raven" / ROUTER_STATE_FILE


def load_router_state() -> Dict:
    try:
        p = _router_state_path()
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {
        "mode": "router",
        "session_id": "",
        "announced": False,
        "backend": "claude",
        "mandatory": True,
    }


def arm_base_router() -> Dict:
    """SessionStart: base routing ON. LiteLLM is not the backend yet."""
    state = load_router_state()
    state["mode"] = "router"
    state["mandatory"] = True
    state["backend"] = detect_host()
    save_router_state(state)
    return state


def save_router_state(state: Dict) -> None:
    try:
        p = _router_state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"Warning: failed to write router state: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Classify query into model tier (SIMPLE/MEDIUM/COMPLEX/LOCAL_ONLY)"
    )
    parser.add_argument("--prompt", default=None, help="User query text (optional in --hook mode: read from stdin)")
    parser.add_argument("--context", default="", help="Additional context (JSON or text)")
    parser.add_argument("--write-json", action="store_true", help="Write result to .raven/.model-session.json")
    parser.add_argument("--hook", action="store_true",
                        help="UserPromptSubmit hook mode: emit hook JSON with a "
                             "user-visible systemMessage toaster instead of raw JSON")
    parser.add_argument("--source", default="user_work",
                        choices=["user_work", "raven_overhead"],
                        help="Attribution bucket: user_work (default) or raven_overhead")
    parser.add_argument("--enable", action="store_true", help="Turn router mode ON (delegation directives active)")
    parser.add_argument("--disable", action="store_true", help="Turn router mode OFF (session default model only)")
    parser.add_argument("--status", action="store_true", help="Show router mode and state")
    parser.add_argument(
        "--session-start",
        action="store_true",
        help="Arm base routing (mandatory ON for this session). Called from SessionStart.",
    )

    args = parser.parse_args()

    # Mode toggles — used by the /router skill, not the hook
    if args.session_start or args.enable or args.disable or args.status:
        if args.session_start:
            try:
                _ops = Path(__file__).resolve().parents[1] / "ops"
                if str(_ops) not in sys.path:
                    sys.path.insert(0, str(_ops))
                import github_version as _gv

                _gv.maybe_print_once(always=True)
            except Exception:
                pass
            state = arm_base_router()
            host = state.get("backend") or detect_host()
            models = _load_model_env(host)
            edu = _educate_mode()
            rules = _host_rules(host)
            ver = "5.5.6"
            try:
                vp = _find_project_root() / "raven-core" / "VERSION"
                if vp.is_file():
                    ver = vp.read_text(encoding="utf-8").strip() or ver
            except OSError:
                pass
            print(
                f"🪶 Raven v{ver} session start · host={host} · rules={rules} · educate={edu}\n"
                f"expected route: SIMPLE→{models.get('SIMPLE','')} "
                f"MEDIUM→{models.get('MEDIUM','')} "
                f"COMPLEX→{models.get('COMPLEX','')}\n"
                "First load (Claude/Codex/Grok/AntiGravity/Cursor/Windsurf/VSCode/Gemini/Replit): "
                "ide-boot → Read memory= if load=1 → this --session-start → every-turn router.\n"
                "🔀 Base router ON (mandatory). First user turn: "
                "python3 scripts/ops/raven-first.py --prompt \"…\"\n"
                "applied=false until this IDE spawns/swaps. "
                "guided = briefing then go-ahead before writes."
            )
            return 0
        state = load_router_state()
        if args.enable:
            state["mode"] = "router"
            state["mandatory"] = True
            save_router_state(state)
            print("🔀 Raven router: ON — SIMPLE must use a Haiku subagent when "
                  "self-contained. Primary /model is unchanged (no per-turn swap).")
        elif args.disable:
            state["mode"] = "default"
            state["mandatory"] = False
            save_router_state(state)
            print("Raven router: OFF this session — SessionStart will turn it ON again.")
        else:
            st = load_router_state()
            host = detect_host()
            st["host"] = host
            st["tiers"] = _load_model_env(host)
            print(json.dumps(st, indent=2))
        return 0

    # Hook / miswired-hook recovery: read prompt + session_id from Claude Code
    # stdin JSON. Fatal historical bug: global settings.json called this script
    # as `model-router.py --write-json` with no --prompt → argparse exit 2 and
    # Claude blocked every UserPromptSubmit. stdin is the only channel hooks
    # have; accept --hook, --write-json, or CLAUDE_HOOK_EVENT as stdin signals.
    hook_session_id = ""
    wants_stdin = bool(
        args.hook
        or args.write_json
        or os.environ.get("CLAUDE_HOOK_EVENT")
    )
    if wants_stdin and args.prompt is None:
        try:
            payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        args.prompt = (
            payload.get("prompt")
            or payload.get("userMessage")
            or payload.get("message")
            or payload.get("user_message")
            or payload.get("text")
            or ""
        )
        if not args.prompt and isinstance(payload.get("content"), str):
            args.prompt = payload.get("content") or ""
        hook_session_id = payload.get("session_id", "") or ""
        if not args.context:
            extra = payload.get("additionalContext")
            if extra is not None:
                args.context = extra if isinstance(extra, str) else json.dumps(extra, default=str)

    # Interactive CLI still needs --prompt. Hook/write-json with empty payload
    # must fail-soft (exit 0) so chat is never blocked.
    if args.prompt is None:
        parser.error("--prompt is required outside --hook / --write-json mode")
    if args.prompt == "":
        return 0

    try:
        _ops = Path(__file__).resolve().parents[1] / "ops"
        if str(_ops) not in sys.path:
            sys.path.insert(0, str(_ops))
        import github_version as _gv

        _gv.maybe_print_once(always=False)
    except Exception:
        pass

    # Method B inference — if called from a hook context, override to overhead
    # CLAUDE_HOOK_EVENT is set by Claude Code when a hook fires
    if os.environ.get("CLAUDE_HOOK_EVENT") and args.source == "user_work":
        # Still default to user_work because the user prompt IS user work,
        # even though model-router runs from a hook. The hook FIRES it but
        # the work being classified IS the user's. Leave as user_work.
        pass

    # Classify
    tier, score, reasons, model = classify(args.prompt, args.context)
    try:
        _cc_dir = Path(__file__).resolve().parents[1] / "session"
        if str(_cc_dir) not in sys.path:
            sys.path.insert(0, str(_cc_dir))
        from cost_calc import append_turn_log, estimate, running_total_usd, repo_name
        est = estimate(model, len(args.prompt or ""))
        stamp = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()) / ".raven" / ".route-stamp"
        try:
            stamp.parent.mkdir(parents=True, exist_ok=True)
            stamp.write_text(datetime.utcnow().isoformat() + "Z\n", encoding="utf-8")
        except OSError:
            pass
        obs_url, obs_run, redteam = "", "", ""
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
            from dash_settings import load as _set_load, obs_link
            st = _set_load()
            obs_url = obs_link()
            if (st.get("observability") or "off") != "off":
                obs_run = hashlib.sha256((args.prompt or "").encode()).hexdigest()[:16]
            if st.get("airtaas_enabled") and any(
                "security" in (x or "") or "auth" in (x or "") for x in (reasons or [])
            ):
                redteam = "airtaas"
        except Exception:
            pass
        _this_est = est.get("est_cost_usd")
        try:
            _this_est_f = float(_this_est) if _this_est is not None else 0.0
        except (TypeError, ValueError):
            _this_est_f = 0.0
        append_turn_log({
            "ts": datetime.utcnow().isoformat() + "Z",
            "repo": repo_name(),
            "ide": detect_host(),
            "host": detect_host(),
            "tier": tier,
            "recommend": model,
            "applied": False,
            "est_cost_usd": est.get("est_cost_usd"),
            "total_cost_usd": round(running_total_usd() + _this_est_f, 6),
            "needs_rate": est.get("needs_rate"),
            "prompt_chars": len(args.prompt or ""),
            "why": (reasons or [])[:3],
            "obs_url": obs_url,
            "obs_run_id": obs_run,
            "redteam": redteam,
        })
        try:
            from obs_trace import emit as _obs_emit
            _obs_emit({
                "obs_run_id": obs_run,
                "repo": repo_name(),
                "ide": detect_host(),
                "tier": tier,
                "recommend": model,
                "prompt_chars": len(args.prompt or ""),
                "est_cost_usd": est.get("est_cost_usd"),
                "obs_url": obs_url,
            })
        except Exception:
            pass
    except Exception:
        pass

    # Persist the classification in hook mode too — the cost log's pre-turn
    # estimate column reads last_classification from .model-session.json, so
    # a hook run that classifies but never records would starve it.
    if args.write_json or args.hook:
        session_file = write_session_json(tier, score, reasons, model, args.prompt, source=args.source)
        if args.write_json:
            print(f"# Written to {session_file} (bucket: {args.source})", file=sys.stderr)

    if args.hook:
        # Hook mode: one-line toaster the user actually sees + context for the
        # model. Raven never routes silently.
        #
        # Claude Code cannot swap the primary session model. Base routing is
        # still mandatory: SessionStart arms the router; SIMPLE must spawn a
        # Haiku Agent when the prompt is self-contained. Context-bound
        # questions stay on the session model. LiteLLM is not wired yet.
        state = load_router_state()
        router_on = state.get("mode") == "router"

        # First prompt of a NEW session: disclose the session model and offer
        # the router, instead of silently classifying. The hook cannot see
        # which model the session runs on (Claude Code doesn't expose it here)
        # — but Claude knows its own model, so the disclosure is delegated to
        # Claude via additionalContext.
        first = bool(hook_session_id and hook_session_id != state.get("session_id"))
        if first:
            state["session_id"] = hook_session_id
            state["announced"] = True
            save_router_state(state)

        if not router_on and tier != "LOCAL_ONLY":
            return 0

        toast = format_turn_toast(tier, model, reasons, prompt_chars=len(args.prompt or ""))
        if first:
            toast = "🪶 Base router ON this session. " + toast

        if tier == "SIMPLE":
            host = detect_host()
            delegation_note = (
                f"RAVEN_MODEL_TIER=SIMPLE host={host} recommend={model} applied=false. "
                f"Your first written lines MUST be Intent: plan|debug|direct and session=<your model>. "
                f"The UserPromptSubmit toaster is not enough. git/status/log is not an exemption. "
                f"If self-contained, spawn a subagent on {model}. If context-bound, stay on session "
                f"and say why in one line. Never claim model_for_tier is what you ran."
            )
        else:
            host = detect_host()
            delegation_note = (
                f"RAVEN_MODEL_TIER={tier} host={host} recommend={model} applied=false. "
                f"Your first written lines MUST be Intent: plan|debug|direct and session=<your model>. "
                f"The toaster is not a skip. git/status is not outside the router. "
                f"You are still the session model. Recommend {model} for subagents. "
                f"Do not say you are anthropic/claude-* unless host=claude. "
                + ("SECRETS DETECTED: do NOT spawn cloud agents; local model only."
                   if tier == "LOCAL_ONLY" else "")
            )

        print(json.dumps({
            "systemMessage": toast,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    delegation_note
                ),
            },
        }))
        return 0

    toast = format_turn_toast(tier, model, reasons, prompt_chars=len(args.prompt or ""))
    if "--json" in sys.argv:
        print(json.dumps({
            "tier": tier,
            "score": score,
            "reasons": reasons,
            "model": model,
            "recommended_model": model,
            "host": detect_host(),
            "applied": False,
            "source": args.source,
            "toast": toast,
        }, indent=2))
    else:
        print(toast)
        print(json.dumps({
            "tier": tier,
            "score": score,
            "reasons": reasons,
            "model": model,
            "recommended_model": model,
            "host": detect_host(),
            "applied": False,
            "source": args.source,
        }, indent=2))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        # parser.error → SystemExit(2). For hook-shaped invocations never block chat.
        if code != 0 and (
            "--hook" in sys.argv
            or "--write-json" in sys.argv
            or os.environ.get("CLAUDE_HOOK_EVENT")
        ):
            print(f"model-router fail-soft (exit {code})", file=sys.stderr)
            sys.exit(0)
        sys.exit(code)
    except Exception as exc:
        print(f"model-router fail-soft: {exc}", file=sys.stderr)
        sys.exit(0)
