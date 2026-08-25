#!/usr/bin/env python3
"""Lightweight in/out token cost math. No network.

  cost = tokens_in/1e6 * input_per_1m + tokens_out/1e6 * output_per_1m

Unknown model: record a local row (needs_rate=true), return cost=None.
Never silently price as gpt-4o.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
PRICING_FILE = _HERE / "model-pricing.json"
_RAVEN = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()) / ".raven"
LOCAL_PRICING = _RAVEN / "model-pricing.local.json"
COST_LOG = _RAVEN / "cost-log.jsonl"
LAST_TURN = _RAVEN / ".last-turn-cost.json"
TURN_LOG = _RAVEN / "turn-log.jsonl"


def _norm(model: str) -> str:
    m = (model or "").strip()
    if "/" in m:
        m = m.split("/", 1)[-1]
    return m.lower()


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def load_table() -> dict[str, dict]:
    """Merge shipped table + local discoveries. Keys are normalized model ids."""
    shipped = _read_json(PRICING_FILE)
    models = dict(shipped.get("models") or {})
    aliases = dict(shipped.get("aliases") or {})
    local = _read_json(LOCAL_PRICING)
    for k, v in (local.get("models") or {}).items():
        if not isinstance(v, dict):
            continue
        shipped_row = models.get(k) or models.get(_norm(k))
        local_blank = v.get("input_per_1m") is None or v.get("output_per_1m") is None
        if local_blank and shipped_row and shipped_row.get("input_per_1m") is not None:
            continue
        models[k] = v
    out = {}
    for k, v in models.items():
        if not isinstance(v, dict):
            continue
        out[_norm(k)] = v
    for src, dst in aliases.items():
        nk, nd = _norm(str(src)), _norm(str(dst))
        if nd in out:
            out[nk] = out[nd]
    return out


def repo_name(root: Optional[Path] = None) -> str:
    root = root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    man = root / ".raven" / "manifest.json"
    try:
        raw = json.loads(man.read_text(encoding="utf-8")).get("project")
        if isinstance(raw, dict):
            raw = raw.get("name") or raw.get("project")
        name = str(raw or "").strip()
        if name:
            return name
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return root.name


def detect_ide(env: Optional[dict] = None) -> str:
    """IDE name from boot.json env keys (claude, grok, codex, …)."""
    env = env if env is not None else os.environ
    boot = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()) / ".raven" / "boot.json"
    try:
        hosts = json.loads(boot.read_text(encoding="utf-8")).get("hosts") or {}
    except (OSError, json.JSONDecodeError, TypeError):
        return "unknown"
    for name, spec in hosts.items():
        for key in (spec or {}).get("env_any") or []:
            if env.get(key):
                return str(name)
    return "unknown"


def router_models(root: Optional[Path] = None) -> set[str]:
    root = root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    boot = root / ".raven" / "boot.json"
    found: set[str] = set()
    try:
        hosts = json.loads(boot.read_text(encoding="utf-8")).get("hosts") or {}
    except (OSError, json.JSONDecodeError, TypeError):
        return found
    for spec in hosts.values():
        for val in (spec.get("tiers") or {}).values():
            found.add(_norm(str(val)))
    return found


def ensure_model(model: str) -> dict:
    """If model has no rates, append needs_rate row to local table. Fast."""
    key = _norm(model)
    table = load_table()
    row = table.get(key)
    if row and row.get("input_per_1m") is not None and row.get("output_per_1m") is not None:
        return row
    local = _read_json(LOCAL_PRICING)
    local.setdefault("models", {})
    if key not in local["models"]:
        in_router = key in router_models()
        local["models"][key] = {
            "input_per_1m": None,
            "output_per_1m": None,
            "needs_rate": True,
            "in_router": in_router,
            "source": model,
        }
        try:
            LOCAL_PRICING.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_PRICING.write_text(json.dumps(local, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
    return local["models"].get(key) or {"needs_rate": True}


def get_cost(
    model: str,
    tokens_in: int,
    tokens_out: int,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> Optional[float]:
    """USD. None if rates missing (row recorded).

    cache_read bills at 0.1× input_per_1m; cache_creation at 1.25× input_per_1m
    (same multipliers token-meter-write uses for Claude Stop rows).
    """
    row = ensure_model(model)
    inn = row.get("input_per_1m")
    out = row.get("output_per_1m")
    if inn is None or out is None:
        return None
    try:
        inn_f, out_f = float(inn), float(out)
    except (TypeError, ValueError):
        return None
    tin, tout = max(0, int(tokens_in or 0)), max(0, int(tokens_out or 0))
    cr, cc = max(0, int(cache_read or 0)), max(0, int(cache_creation or 0))
    base = (tin / 1_000_000.0) * inn_f + (tout / 1_000_000.0) * out_f
    cache = (cr / 1_000_000.0) * inn_f * 0.1 + (cc / 1_000_000.0) * inn_f * 1.25
    return round(base + cache, 6)


def estimate(model: str, prompt_chars: int, reply_out_guess: int = 500) -> dict[str, Any]:
    """Pre-turn guess from prompt size. Labeled estimate; never merged with actuals."""
    tokens_in = max(0, int((prompt_chars or 0) / 4))
    usd = get_cost(model, tokens_in, reply_out_guess)
    row = ensure_model(model)
    return {
        "model": _norm(model),
        "tokens_in_est": tokens_in,
        "tokens_out_est": reply_out_guess,
        "est_cost_usd": usd,
        "needs_rate": bool(row.get("needs_rate") or usd is None),
        "input_per_1m": row.get("input_per_1m"),
        "output_per_1m": row.get("output_per_1m"),
        "in_router": _norm(model) in router_models(),
    }


def _fmt_usd(v) -> str:
    if v is None:
        return "?"
    try:
        return f"${float(v):.4f}"
    except (TypeError, ValueError):
        return "?"


def _sum_jsonl(path: Path, field: str, session_id: str = "") -> float:
    total = 0.0
    if not path.is_file():
        return 0.0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if session_id and row.get("session_id") and row.get("session_id") != session_id:
                continue
            try:
                total += float(row.get(field) or 0)
            except (TypeError, ValueError):
                continue
    except OSError:
        return 0.0
    return round(total, 6)


def spend_kind(session_id: str = "") -> tuple[str, float]:
    """Return ('actual', usd) from cost-log, else ('estimated', usd) from turn-log.

    Authoritative money is computed_cost_usd in cost-log.jsonl (Stop / token-meter-write).
    If that file is missing or all zeros, this is an estimate — callers must label it.
    Host-agnostic: the Stop write can fail on Claude as well as Grok/Codex (missing
    hook path, swallowed stderr, empty stdin, or transcript schema). Not IDE-specific.
    """
    actual = _sum_jsonl(COST_LOG, "computed_cost_usd", session_id)
    if actual > 0:
        return "actual", actual
    return "estimated", _sum_jsonl(TURN_LOG, "est_cost_usd", session_id)


def calculator_spend() -> dict:
    """Actual = one snapshot per cost-log session (max out), including cache.

    Prefer computed_cost_usd on that row (token-meter already applied cache
    rates). Estimated = turn-log recommend + chars/4 in + 500 out per fire.
    """
    sessions: dict = {}
    if COST_LOG.is_file():
        for line in COST_LOG.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ide = str(r.get("ide") or r.get("host") or "")
            model = str(r.get("model") or "")
            if ide == "grok" and "grok" not in model.lower():
                continue
            sid = str(r.get("session_id") or r.get("ts") or "")
            tout = int(r.get("tokens_out") or 0)
            prev = sessions.get(sid)
            if prev is None or tout >= int(prev.get("tokens_out") or 0):
                sessions[sid] = r
    actual = 0.0
    for r in sessions.values():
        raw = r.get("computed_cost_usd")
        if raw is not None and str(raw) != "":
            try:
                usd = float(raw)
            except (TypeError, ValueError):
                usd = None
        else:
            usd = None
        if usd is None:
            usd = get_cost(
                str(r.get("model") or ""),
                int(r.get("tokens_in") or 0),
                int(r.get("tokens_out") or 0),
                int(r.get("cache_read") or 0),
                int(r.get("cache_creation") or 0),
            )
        if usd:
            actual += float(usd)
    covered_ide = {str(r.get("ide") or r.get("host") or "") for r in sessions.values()}
    est = 0.0
    if TURN_LOG.is_file():
        for line in TURN_LOG.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ide = str(r.get("ide") or r.get("host") or "")
            if ide in covered_ide and ide == "claude":
                continue
            model = str(r.get("recommend") or "")
            tin = max(0, int(r.get("prompt_chars") or 0) // 4)
            usd = get_cost(model, tin, 500) if model else None
            if usd:
                est += usd
    if actual > 0 and est > 0:
        kind = "mixed"
    elif actual > 0:
        kind = "actual"
    else:
        kind = "estimated"
    return {
        "kind": kind,
        "usd": round(actual + est, 6),
        "actual": round(actual, 6),
        "estimated": round(est, 6),
    }


def running_total_usd(session_id: str = "") -> float:
    """Numeric running total. Prefer actuals; else estimates. See spend_kind()."""
    _kind, usd = spend_kind(session_id)
    return usd


def load_last_turn() -> dict:
    return _read_json(LAST_TURN)


def write_turn_end(
    *,
    turn_usd: Optional[float],
    running_total: float,
    model: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    session_id: str = "",
) -> dict:
    """Stop hook: this turn + running total (addition)."""
    rec = {
        "turn_usd": turn_usd,
        "total_cost_usd": round(float(running_total or 0), 6),
        "model": model,
        "tokens_in": int(tokens_in or 0),
        "tokens_out": int(tokens_out or 0),
        "session_id": session_id or "",
    }
    try:
        LAST_TURN.parent.mkdir(parents=True, exist_ok=True)
        LAST_TURN.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    except OSError:
        pass
    return rec


def append_turn_log(rec: dict) -> None:
    """One JSONL line per router fire. Fast append. Fail-soft."""
    try:
        TURN_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(rec, separators=(",", ":")) + "\n"
        with TURN_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def tail_jsonl(path: Path, n: int = 40) -> list:
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


def start_money_line(model: str, prompt_chars: int) -> str:
    """Router start: cost so far + estimate for this classify."""
    total = running_total_usd()
    last = load_last_turn()
    est = estimate(model, prompt_chars)
    last_s = _fmt_usd(last.get("turn_usd")) if last else "$0.0000"
    note = " needs_rate (fill .raven/model-pricing.local.json)" if est.get("needs_rate") else ""
    return (
        f"💰 total-cost={_fmt_usd(total)} last_turn={last_s} "
        f"est={_fmt_usd(est.get('est_cost_usd'))}{note}"
    )


def end_money_line(rec: dict) -> str:
    return (
        f"💰 turn={_fmt_usd(rec.get('turn_usd'))} "
        f"total-cost={_fmt_usd(rec.get('total_cost_usd'))} "
        f"(last total-cost + turn)"
    )


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if len(args) >= 3:
        m, tin, tout = args[0], int(args[1]), int(args[2])
        print(json.dumps({"model": m, "cost_usd": get_cost(m, tin, tout), **ensure_model(m)}))
    elif args[:1] == ["--start"] and len(args) >= 2:
        chars = int(args[2]) if len(args) > 2 else 0
        print(start_money_line(args[1], chars))
    elif args[:1] == ["--end"]:
        rec = load_last_turn()
        print(end_money_line(rec) if rec else "💰 turn=? total-cost=? (no Stop write yet)")
    else:
        print("usage: cost_calc.py MODEL TOKENS_IN TOKENS_OUT | --start MODEL [CHARS] | --end", file=sys.stderr)
        raise SystemExit(2)
