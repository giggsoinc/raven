#!/usr/bin/env python3
"""push-gate.py — PreToolUse: Educate is compulsory when mode=guided.

Default (missing .raven/educate.json) = guided. Mutating Write/Edit/Bash
is denied until .raven/.push-approved exists (UserPromptSubmit go-ahead).
mode=off (educate off / Lucky) allows writes. Read-only Bash always allowed.

SessionStart must NOT delete educate.json (preference persists).

Fail-closed: if the gate itself errors while educate is guided, the call is
denied and an audit row is written. A gate that exits 0 on error is a bypass.

Read-only detection is a quote-aware parser, not a token list. A command is
read-only only when every part of it is understood and safe. Anything the
parser cannot understand is treated as a write.
"""

import ast
import json
import os
import re
import shlex
import sys
import time
from datetime import datetime, timezone

NOTICE = (
    "🪶 Educate (guided): briefing first (WHAT/HOW/files, ≤200 words), then stop. "
    "User says go ahead / approved / proceed — then write. "
    "Turn off: educate off or Lucky (persists in .raven/educate.json). "
    "This write was DENIED."
)
ERROR_NOTICE = (
    "🪶 Educate gate error — failing closed. The gate could not classify this "
    "call, so it was DENIED. See .raven/audit/. Turn off: educate off or Lucky."
)

# Heads that only read, whatever their arguments (redirects are checked apart).
SIMPLE_HEADS = {
    "ls", "cat", "head", "tail", "grep", "egrep", "fgrep", "wc", "pwd", "which",
    "type", "file", "stat", "du", "echo", "printf", "uname", "diff", "cmp",
    "basename", "dirname", "cut", "column", "true", "false", "test", "[", "[[",
    "cd", "jq", "readlink", "realpath", "hostname", "whoami", "id", "nl",
}
READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "rev-parse", "ls-files", "blame",
    "shortlog", "describe", "ls-tree", "cat-file", "rev-list", "name-rev",
}
PY_HEADS = {"python", "python3"}
# Research / classify / tests — not a repo write.
PY_READ_FLAGS = {
    "--status", "--help", "-h", "--version", "--json", "--digest",
    "--cli", "--query-type", "--gaps", "--prompt",
}
PY_WRITE_FLAGS = {
    "--set", "--enable", "--disable", "--session-start", "--html",
    "--write-json", "--build", "--open", "--all", "--obsidian", "--hook",
}
# Scripts that only print when given no write flag.
PY_SCRIPTS_OK = {"educate.py"}
PY_MODULES_OK = {"unittest", "pytest", "json.tool"}
PY_INTERPRETER_FLAGS = {"-I", "-B", "-E", "-s", "-S", "-u", "-q", "-O"}

SHELL_KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!"}
SHELL_CLOSERS = {"fi", "done", "esac"}

FIND_ACTIONS = {
    "-delete", "-exec", "-execdir", "-ok", "-okdir",
    "-fprint", "-fprint0", "-fprintf", "-fls",
}
GIT_BRANCH_WRITE = {
    "-d", "-D", "-m", "-M", "-c", "-C", "-u", "-f", "-t",
    "--delete", "--move", "--copy", "--force", "--track", "--no-track",
    "--unset-upstream", "--edit-description",
}
GIT_TAG_WRITE = {
    "-d", "-a", "-s", "-f", "-m", "-F", "-u", "-e",
    "--delete", "--annotate", "--sign", "--force", "--message", "--file",
    "--local-user", "--edit",
}
GIT_LIST_FLAGS = {
    "-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged",
    "--points-at",
}

# A redirect is harmless only when it goes to /dev/null or duplicates a stream.
REDIR_OK = re.compile(
    r">{1,2}\s*/dev/(?:null|stderr|stdout)(?![\w/.-])|>&\s*[0-9](?!\w)|>&-"
)

APPROVAL_TTL_SEC = 3600


def repo_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


# ── shell splitting ──────────────────────────────────────────────────────────

def _split_segments(command: str):
    """Split on every unquoted separator. None = cannot be analysed safely.

    Splits on && || ; | & and newline. Returns None for command substitution,
    backticks, heredocs, process substitution, unbalanced quotes, and any
    redirect that is not /dev/null or a stream duplicate.
    """
    segments: list = []
    buf: list = []
    quote = None
    i, n = 0, len(command)

    def flush() -> None:
        segments.append("".join(buf))
        buf.clear()

    while i < n:
        c = command[i]
        if quote == "'":
            buf.append(c)
            if c == "'":
                quote = None
            i += 1
            continue
        if c == "\\":
            nxt = command[i + 1] if i + 1 < n else ""
            buf.append(" " if nxt == "\n" else c + nxt)
            i += 2
            continue
        if c == "`" or (c == "$" and command[i + 1:i + 2] == "("):
            return None
        if quote == '"':
            buf.append(c)
            if c == '"':
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            buf.append(c)
            i += 1
            continue
        if c in ("\n", ";"):
            flush()
            i += 1
            continue
        if c == "|":
            flush()
            i += 2 if command[i + 1:i + 2] in ("|", "&") else 1
            continue
        if c == "&":
            nxt = command[i + 1:i + 2]
            if nxt == "&":
                flush()
                i += 2
                continue
            if nxt == ">":  # &>/dev/null
                m = REDIR_OK.match(command, i + 1)
                if not m:
                    return None
                i = m.end()
                continue
            flush()  # single & = background job, a separate command
            i += 1
            continue
        if c == ">":
            m = REDIR_OK.match(command, i)
            if not m:
                return None
            # drop the fd digit left behind by "2>/dev/null"
            if buf and buf[-1].isdigit() and (len(buf) == 1 or buf[-2] in " \t"):
                buf.pop()
            i = m.end()
            continue
        if c == "<":
            if command[i + 1:i + 2] in ("<", "("):
                return None
            buf.append(c)
            i += 1
            continue
        buf.append(c)
        i += 1
    if quote:
        return None
    flush()
    return segments


# ── python -c snippets ───────────────────────────────────────────────────────

AST_IMPORTS_OK = {
    "json", "sys", "re", "os", "pathlib", "ast", "tomllib", "collections",
    "itertools", "textwrap", "hashlib", "datetime", "glob", "fnmatch", "typing",
}
AST_OS_ATTRS_OK = {
    "path", "getcwd", "listdir", "environ", "sep", "linesep", "getenv",
    "stat", "scandir", "walk", "cpu_count", "name", "curdir",
}
AST_SYS_ATTRS_OK = {
    "argv", "version", "version_info", "platform", "path", "executable",
    "stdout", "stderr", "stdin", "exit", "maxsize",
}
AST_ATTR_DENY = {
    "write", "writelines", "write_text", "write_bytes", "unlink", "remove",
    "removedirs", "rmdir", "rename", "renames", "replace", "mkdir", "makedirs",
    "system", "popen", "truncate", "touch", "chmod", "chown", "symlink_to",
    "hardlink_to", "rmtree", "dump", "kill", "putenv", "unsetenv", "exec",
    "spawn", "fork", "startfile", "modules",
}
AST_CALL_DENY = {
    "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "breakpoint", "input",
}


def _mode_is_write(call: ast.Call, position: int) -> bool:
    """True when an open() call can write, or its mode is not a plain literal."""
    mode = None
    if len(call.args) > position:
        mode = call.args[position]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(ch in mode.value for ch in "wax+")
    return True


def snippet_is_read_only(code: str) -> bool:
    """Allowlist check for `python3 -c`: inspection only, no writes or exec."""
    if len(code) > 4000:
        return False
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname or alias.name.split(".")[0] not in AST_IMPORTS_OK:
                    return False
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level or root not in AST_IMPORTS_OK or root == "os":
                return False
            if any(alias.asname for alias in node.names):
                return False
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in AST_ATTR_DENY:
                return False
            if isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr not in AST_OS_ATTRS_OK:
                    return False
                if node.value.id == "sys" and node.attr not in AST_SYS_ATTRS_OK:
                    return False
        elif isinstance(node, ast.Name):
            if node.id.startswith("__") and node.id not in ("__name__", "__file__"):
                return False
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in AST_CALL_DENY:
                    return False
                if func.id == "open" and _mode_is_write(node, 1):
                    return False
            elif isinstance(func, ast.Attribute) and func.attr == "open":
                if _mode_is_write(node, 0):
                    return False
    return True


# ── per-command rules ────────────────────────────────────────────────────────

def _script_path_ok(path: str) -> bool:
    if ".." in path.split("/"):
        return False
    if os.path.isabs(path):
        root = os.path.realpath(repo_root())
        real = os.path.realpath(path)
        return real.startswith(root + os.sep) or "/.claude/plugins/" in real
    return True


def python_is_read_only(tokens: list) -> bool:
    """python3 --status / -m unittest / educate.py (no --set) / simple -c reads."""
    rest = tokens[1:]
    while rest and rest[0] in PY_INTERPRETER_FLAGS:
        rest = rest[1:]
    if not rest:
        return True
    if rest[0] == "-c":
        return len(rest) >= 2 and snippet_is_read_only(rest[1])
    if rest[0] == "-m":
        return (
            len(rest) >= 2
            and rest[1] in PY_MODULES_OK
            and not any(a in PY_WRITE_FLAGS for a in rest[2:])
        )
    if rest[0].startswith("-"):
        return rest[0] in ("--version", "-V", "--help", "-h")
    script, args = rest[0], rest[1:]
    if not _script_path_ok(script) or any(a in PY_WRITE_FLAGS for a in args):
        return False
    if os.path.basename(script) in PY_SCRIPTS_OK:
        return True
    return any(a in PY_READ_FLAGS for a in args)


def _git_branch_ok(args: list) -> bool:
    if any(a in GIT_BRANCH_WRITE or a.startswith("--set-upstream") for a in args):
        return False
    positional = [a for a in args if not a.startswith("-")]
    return not positional or any(a in GIT_LIST_FLAGS for a in args)


def _git_tag_ok(args: list) -> bool:
    if any(a in GIT_TAG_WRITE for a in args):
        return False
    positional = [a for a in args if not a.startswith("-")]
    return not positional or any(a in GIT_LIST_FLAGS for a in args)


def _git_remote_ok(args: list) -> bool:
    if all(a in ("-v", "--verbose") for a in args):
        return True
    return bool(args) and args[0] in ("show", "get-url")


def _git_ok(args: list) -> bool:
    i = 0
    while i < len(args):
        if args[i] == "-C" and i + 1 < len(args):
            i += 2
        elif args[i] in ("--no-pager", "-P", "--no-optional-locks"):
            i += 1
        else:
            break
    if i >= len(args):
        return False
    sub, rest = args[i], args[i + 1:]
    if any(a.startswith("--output") for a in rest):
        return False
    if sub in READ_ONLY_GIT_SUBCOMMANDS:
        return True
    if sub == "branch":
        return _git_branch_ok(rest)
    if sub == "tag":
        return _git_tag_ok(rest)
    if sub == "remote":
        return _git_remote_ok(rest)
    return False


def _head_is_read_only(head: str, args: list, tokens: list) -> bool:
    if head in SIMPLE_HEADS:
        return True
    if head == "git":
        return _git_ok(args)
    if head in PY_HEADS:
        return python_is_read_only(tokens)
    if head == "env":
        return not args  # bare `env` prints; `env CMD` runs CMD
    if head == "find":
        return not any(a in FIND_ACTIONS for a in args)
    if head == "sort":
        return not any(a == "-o" or a.startswith("--output") for a in args)
    if head == "uniq":
        return len([a for a in args if not a.startswith("-")]) <= 1
    if head == "date":
        return not any(a in ("-s", "--set") for a in args)
    if head == "tree":
        return "-o" not in args
    if head == "rg":
        return not any(a.startswith("--pre") for a in args)
    return False


def _segment_is_read_only(segment: str) -> bool:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    while tokens and tokens[0] in SHELL_KEYWORDS:
        tokens.pop(0)
    if not tokens:
        return True
    if tokens[0] in SHELL_CLOSERS:
        return len(tokens) == 1
    if tokens[0] == "for":  # loop header only: for NAME [in WORDS]
        return len(tokens) == 2 or (len(tokens) >= 3 and tokens[2] == "in")
    head = os.path.basename(tokens[0])
    return _head_is_read_only(head, tokens[1:], tokens)


def bash_is_read_only(command: str) -> bool:
    segments = _split_segments(command)
    if segments is None:
        return False
    return all(_segment_is_read_only(seg) for seg in segments)


# ── mode, approval, audit ────────────────────────────────────────────────────

def educate_mode(root: str) -> str:
    path = os.path.join(root, ".raven", "educate.json")
    if not os.path.isfile(path):
        return "guided"
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return "guided"
    if isinstance(data, str):
        mode = data.strip().lower()
    elif isinstance(data, dict):
        mode = str(data.get("mode") or "guided").strip().lower()
    else:
        return "guided"
    if mode in ("auto", "lucky", "off"):
        return "off"
    return "guided"


def approval_ok(root: str) -> bool:
    path = os.path.join(root, ".raven", ".push-approved")
    if not os.path.isfile(path):
        return False
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return age <= APPROVAL_TTL_SEC


def audit(root: str, event: str, **extra) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(root, ".raven", "audit", f"{day}.log")
    row = {"ts": int(time.time()), "source": "push-gate", "event": event, **extra}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError as exc:
        print(f"push-gate audit failed: {exc}", file=sys.stderr)


def emit(decision, reason, message=None):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }
    if message:
        out["systemMessage"] = message
    print(json.dumps(out))


def fail_closed(root: str, why: str) -> None:
    """The gate could not decide. Deny unless the user turned educate off."""
    if educate_mode(root) == "off":
        sys.exit(0)
    audit(root, "gate-error", detail=why[:200])
    emit("deny", "Educate gate error — failing closed", ERROR_NOTICE)
    sys.exit(0)


def main() -> None:
    root = repo_root()
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name", "")
        if tool == "Bash":
            command = (payload.get("tool_input") or {}).get("command", "")
            mutating = not bash_is_read_only(command)
        else:
            mutating = tool in ("Write", "Edit", "MultiEdit", "NotebookEdit")
    except Exception as exc:  # unparseable payload or parser bug
        fail_closed(root, f"{type(exc).__name__}: {exc}")
        return

    if not mutating:
        sys.exit(0)

    if educate_mode(root) == "off":
        sys.exit(0)

    if approval_ok(root):
        sys.exit(0)

    emit("deny", "Educate guided — no go-ahead", NOTICE)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # anything the inner guard missed
        fail_closed(repo_root(), f"{type(exc).__name__}: {exc}")
