#!/usr/bin/env python3
"""
Raven — Skill-Routing Gate (PreToolUse hook)

Deterministic enforcement of specialist-skill routing. The advisory layer
(session-start / skill-reminder banners) ASKS the model to invoke a specialist;
this gate makes code edits physically impossible until one actually ran.

Gates the ACTION, not the intent: no prompt classification here. Enforced
skills append a marker via raven-mark-skill.py; this hook checks for a fresh
marker before allowing Edit/Write/NotebookEdit.

Config: .raven/state/routing-policy.json
    {
      "mode": "soft",                  // shadow | soft | hard | off
      "required_skills": ["andie", "andie-jr"],   // any one marker satisfies
      "scope": ["src/**", "*.py"],     // globs of gated paths; [] = gate all
      "exclude": ["docs/**", "*.md"],  // never gated
      "freshness_hours": 4,            // fallback window
      "override_uses": 3               // tool calls one override touch allows
    }

Modes (mirrors guard two-tier discipline):
    shadow — never blocks; logs would-block violations
    soft   — never blocks; warns via stdout + logs (default for new installs,
             grace period before hard — same pattern as architecture-guard)
    hard   — exit 2 blocks the tool call until a fresh marker exists
    off    — gate disabled

Freshness: marker must match the current session_id (from hook stdin) OR be
newer than the session-start stamp (.raven/state/.session-start, touched by
session-start.py) OR fall inside freshness_hours.

Escape hatch: `touch .raven/state/gate-override` allows the next N tool calls.
NEVER silent — every override use is appended to .raven/audit/YYYY-MM-DD.log.

No policy file → exit 0 immediately (zero friction, <5ms).
Honest contract: guarantees the skill RAN, not that its output was used well.
Local-only. No telemetry. Zero model tokens except the one block message.
"""

import fnmatch
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(".raven") / "state"
POLICY_FILE = STATE_DIR / "routing-policy.json"
MARKER_FILE = STATE_DIR / "skill-invocations.jsonl"
SESSION_STAMP = STATE_DIR / ".session-start"
OVERRIDE_FILE = STATE_DIR / "gate-override"
AUDIT_DIR = Path(".raven") / "audit"
OBSERVATION_LOG = Path("docs") / "observations" / "security_log.md"

GATED_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _audit(event: str, detail: dict) -> None:
    """Append one JSONL audit line. Best-effort, never raises."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        log = AUDIT_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
        with log.open("a") as fh:
            fh.write(json.dumps({
                "ts": int(time.time()), "source": "raven-skill-gate",
                "event": event, **detail,
            }) + "\n")
    except Exception:
        pass


def _observe(message: str) -> None:
    """Soft/shadow violation note — same sink task-observer uses."""
    try:
        OBSERVATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with OBSERVATION_LOG.open("a") as fh:
            fh.write(f"- [{stamp}] raven-skill-gate: {message}\n")
    except Exception:
        pass


def _in_scope(path: str, policy: dict) -> bool:
    """True if `path` is gated by the policy's scope/exclude globs."""
    if not path:
        return False
    for pattern in policy.get("exclude", []):
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern):
            return False
    scope = policy.get("scope", [])
    if not scope:  # empty scope = gate everything not excluded
        return True
    return any(
        fnmatch.fnmatch(path, p) or fnmatch.fnmatch(Path(path).name, p)
        for p in scope
    )


def _fresh_marker(policy: dict, session_id: str) -> str | None:
    """Return the satisfying skill name if a fresh marker exists, else None."""
    required = set(policy.get("required_skills", []))
    if not required or not MARKER_FILE.exists():
        return None
    window = float(policy.get("freshness_hours", 4)) * 3600
    now = time.time()
    session_started = SESSION_STAMP.stat().st_mtime if SESSION_STAMP.exists() else None
    try:
        lines = MARKER_FILE.read_text().splitlines()
    except Exception:
        return None
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("skill") not in required:
            continue
        ts = float(rec.get("ts", 0))
        if session_id and rec.get("session_id") == session_id:
            return rec["skill"]
        if session_started is not None:
            if ts >= session_started:
                return rec["skill"]
            continue  # stamp exists and marker predates this session → stale
        if now - ts <= window:  # no stamp: fall back to the time window
            return rec["skill"]
    return None


def _consume_override() -> bool:
    """One override touch-file allows N tool calls. Logged, never silent."""
    if not OVERRIDE_FILE.exists():
        return False
    try:
        content = OVERRIDE_FILE.read_text().strip()
        remaining = int(content) if content.isdigit() else None
    except Exception:
        remaining = None
    if remaining is None:  # fresh touch — read allowance from policy later
        remaining = 3
    remaining -= 1
    try:
        if remaining <= 0:
            OVERRIDE_FILE.unlink()
        else:
            OVERRIDE_FILE.write_text(str(remaining))
    except Exception:
        pass
    _audit("override-used", {"remaining": max(remaining, 0)})
    return True


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    if not POLICY_FILE.exists():
        return 0  # no policy → gate disabled, zero friction
    try:
        policy = json.loads(POLICY_FILE.read_text())
    except Exception:
        _audit("policy-parse-error", {})
        return 0  # fail-soft: a broken policy must not lock the user out

    mode = policy.get("mode", "soft")
    if mode == "off":
        return 0

    tool = hook_input.get("tool_name", "")
    if tool not in GATED_TOOLS:
        return 0
    file_path = (hook_input.get("tool_input") or {}).get("file_path", "") or \
                (hook_input.get("tool_input") or {}).get("notebook_path", "")
    try:
        rel = str(Path(file_path).resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        rel = file_path
    if not _in_scope(rel, policy):
        return 0

    session_id = hook_input.get("session_id", "")
    skill = _fresh_marker(policy, session_id)
    if skill:
        return 0  # invariant satisfied

    required = ", ".join(policy.get("required_skills", [])) or "a specialist"
    if _consume_override():
        print(f"⚠️ raven-skill-gate: override used — edit allowed without "
              f"specialist marker (logged to .raven/audit/).")
        return 0

    detail = {"tool": tool, "file": rel, "mode": mode, "required": required}
    if mode == "hard":
        _audit("blocked", detail)
        print(
            f"BLOCKED by raven-skill-gate: no specialist skill invoked this "
            f"session. Invoke the matching specialist (e.g. andie-jr for bugs, "
            f"andie for design) before editing — its first step runs "
            f"raven-mark-skill.py, which unlocks edits. "
            f"Override: touch .raven/state/gate-override (logged).",
            file=sys.stderr,
        )
        return 2
    # shadow / soft
    _audit("violation", detail)
    _observe(f"{mode}-mode violation — {tool} on {rel} without fresh "
             f"specialist marker (required: {required})")
    if mode == "soft":
        print(f"⚠️ raven-skill-gate (soft): edit to {rel} without a specialist "
              f"marker — invoke {required} first. This becomes a hard block "
              f"after the grace period.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
