#!/usr/bin/env python3
"""On-demand memory-card hook.

Run first on every turn. Run again on exit, check-in, push, and pull.
If .raven/memory/CARD.md is missing, invalid, or older than stale_after_hours,
print "memory updating" and rebuild the card from the Obsidian project hub.
Always print one log line and append the same line to .raven/logs/memory-card.log.

Never fails the caller (exit 0). Does not read secrets.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from vault_common import (  # noqa: E402
    CARD_SCHEMA,
    ensure_project_hub,
    manifest_project_name,
    memory_card_path,
    write_memory_card,
)

END_EVENTS = {"exit", "checkin", "push", "pull"}


def _root() -> Path:
    import os

    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()


def _meta(card: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    try:
        lines = card.read_text(encoding="utf-8", errors="replace").splitlines()[:12]
    except OSError:
        return meta
    for line in lines:
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    return meta


def card_state(card: Path) -> str:
    """missing | unavailable | stale | fresh."""
    if not card.is_file():
        return "missing"
    meta = _meta(card)
    if meta.get("schema") != str(CARD_SCHEMA):
        return "unavailable"
    if meta.get("status", "").upper() == "INVALID":
        return "unavailable"
    written = meta.get("written_at") or ""
    try:
        hours = float(meta.get("stale_after_hours") or "24")
        stamp = datetime.datetime.strptime(written, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
    except (TypeError, ValueError):
        return "stale"
    age = datetime.datetime.now(datetime.timezone.utc) - stamp
    if age.total_seconds() > hours * 3600:
        return "stale"
    return "fresh"


def refresh_card(root: Path) -> Path:
    """Rebuild CARD.md from the Obsidian project hub."""
    name = manifest_project_name(root) or "raven"
    try:
        ensure_project_hub(name)
    except Exception:
        pass
    return write_memory_card(root, project=name)


def _log(root: Path, line: str) -> None:
    print(line, flush=True)
    path = root / ".raven" / "logs" / "memory-card.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            handle.write(f"{stamp} {line}\n")
    except OSError:
        pass


def run(event: str, root: Path | None = None) -> int:
    root = root or _root()
    event = event if event in {"turn", *END_EVENTS} else "turn"
    card = memory_card_path(root)
    state = card_state(card)
    needs_update = event in END_EVENTS or state != "fresh"
    if needs_update:
        print("memory updating", flush=True)
        try:
            card = refresh_card(root)
            state = "updated"
        except Exception as exc:
            state = f"update-failed:{type(exc).__name__}"
    rel = ".raven/memory/CARD.md"
    _log(root, f"memory: event={event} state={state} card={rel}")
    if card.is_file() and event == "turn":
        print(f"memory: read {rel}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    event = "turn"
    if "--event" in args:
        i = args.index("--event")
        if i + 1 < len(args):
            event = args[i + 1].strip().lower()
    elif args and not args[0].startswith("-"):
        event = args[0].strip().lower()
    return run(event)


if __name__ == "__main__":
    raise SystemExit(main())
