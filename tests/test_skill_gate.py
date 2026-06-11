"""Tests for raven-skill-gate.py (PreToolUse) + raven-mark-skill.py.

The gate enforces a workflow invariant — "a gated specialist skill ran this
session" — via marker files. It never classifies prompts. Honest contract:
it guarantees the skill RAN, not that its output was used well.
"""
import json
import os
import pathlib
import subprocess
import time

_ROOT = pathlib.Path(__file__).parent.parent
GATE = _ROOT / "scripts" / "raven-skill-gate.py"
MARK = _ROOT / "scripts" / "raven-mark-skill.py"


def _policy(root, **over):
    base = {
        "mode": "hard",
        "required_skills": ["andie", "andie-jr"],
        "scope": [],
        "exclude": ["docs/**", "*.md"],
        "freshness_hours": 4,
        "override_uses": 3,
    }
    base.update(over)
    state = root / ".raven" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "routing-policy.json").write_text(json.dumps(base))
    return state


def _run_gate(root, tool="Edit", file_path="src/app.py", session_id="s1"):
    payload = json.dumps({
        "tool_name": tool,
        "tool_input": {"file_path": str(root / file_path)},
        "session_id": session_id,
    })
    return subprocess.run(
        ["python3", str(GATE)], cwd=root, input=payload,
        capture_output=True, text=True, timeout=10,
    )


def _mark(root, skill, session_id="s1"):
    env = dict(os.environ, CLAUDE_SESSION_ID=session_id)
    return subprocess.run(
        ["python3", str(MARK), skill], cwd=root, env=env,
        capture_output=True, text=True, timeout=10,
    )


def test_no_policy_allows(tmp_path):
    r = _run_gate(tmp_path)
    assert r.returncode == 0


def test_edit_blocked_without_marker(tmp_path):
    _policy(tmp_path)
    r = _run_gate(tmp_path)
    assert r.returncode == 2
    assert "BLOCKED by raven-skill-gate" in r.stderr


def test_edit_allowed_after_marker(tmp_path):
    _policy(tmp_path)
    assert _mark(tmp_path, "andie-jr").returncode == 0
    r = _run_gate(tmp_path)
    assert r.returncode == 0, r.stderr


def test_stale_marker_blocks(tmp_path):
    state = _policy(tmp_path)
    # Marker written BEFORE this session started (session stamp is newer).
    marker = {"ts": int(time.time()) - 60, "skill": "andie-jr", "session_id": "old"}
    (state / "skill-invocations.jsonl").write_text(json.dumps(marker) + "\n")
    stamp = state / ".session-start"
    stamp.touch()
    os.utime(stamp, (time.time(), time.time()))
    r = _run_gate(tmp_path, session_id="s2")
    assert r.returncode == 2


def test_shadow_mode_logs_never_blocks(tmp_path):
    _policy(tmp_path, mode="shadow")
    r = _run_gate(tmp_path)
    assert r.returncode == 0
    audit_dir = tmp_path / ".raven" / "audit"
    logs = list(audit_dir.glob("*.log"))
    assert logs and "violation" in logs[0].read_text()
    obs = tmp_path / "docs" / "observations" / "security_log.md"
    assert obs.exists() and "shadow-mode violation" in obs.read_text()


def test_soft_mode_warns_never_blocks(tmp_path):
    _policy(tmp_path, mode="soft")
    r = _run_gate(tmp_path)
    assert r.returncode == 0
    assert "raven-skill-gate (soft)" in r.stdout


def test_override_allows_and_logs(tmp_path):
    state = _policy(tmp_path)
    (state / "gate-override").write_text("2")
    r = _run_gate(tmp_path)
    assert r.returncode == 0
    assert "override used" in r.stdout
    audit = next((tmp_path / ".raven" / "audit").glob("*.log")).read_text()
    assert "override-used" in audit
    # allowance decremented, then exhausted file removed
    assert (state / "gate-override").read_text() == "1"
    _run_gate(tmp_path)
    assert not (state / "gate-override").exists()
    assert _run_gate(tmp_path).returncode == 2  # back to blocking


def test_out_of_scope_allowed(tmp_path):
    _policy(tmp_path)
    r = _run_gate(tmp_path, file_path="docs/notes.md")
    assert r.returncode == 0


def test_gate_latency_under_100ms(tmp_path):
    _policy(tmp_path)
    _mark(tmp_path, "andie")
    start = time.perf_counter()
    _run_gate(tmp_path)
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 100, f"gate took {elapsed:.0f}ms (budget 100ms)"
