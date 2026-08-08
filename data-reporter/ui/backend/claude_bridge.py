"""ui.backend.claude_bridge — spawns the restricted `claude` CLI subprocess
and translates its stream-json output into typed ChatEvents.

## The sandbox (verified against a real top-level subprocess — see below)

Two layers:

1. **`--tools "Read,Glob,Grep,Bash,Skill"`** restricts the ENTIRE tool
   registry to exactly these five — not a permission check, an existence
   check. Everything else (Write, Edit, WebFetch, Task, PowerShell, and any
   tool added in a future Claude Code version we haven't audited) simply
   isn't there to call. This is deliberately an allow-list, not
   `--disallowedTools` enumerating what to block: a deny-list only covers
   tools we thought to name, so a new tool shipped in a later Claude Code
   version would silently default-allow. Confirmed empirically that
   `--disallowedTools` alone left `PowerShell` completely unrestricted (it
   got "blocked" a few times by unrelated built-in content heuristics, not
   by anything we configured) — `--tools` closes that gap by removing it
   from the session entirely.

2. **Two `PreToolUse` hooks** (`ui/settings/bash_gate.py`,
   `ui/settings/skill_gate.py`, wired via `ui/settings/claude-settings.json`)
   narrow the two tools that need finer-than-tool-level scoping:
   - `Bash` → only commands starting with `uv run odr` (how the skills
     actually shell out — see CLAUDE.md).
   - `Skill` → only odr-report / odr-new-chart / odr-new-domain (`--tools`
     says "Skill may be used," not "which skill" — without this a user
     could invoke any other skill visible in a normal session, e.g.
     `simplify` or `code-review`, well outside this UI's intended scope).

   Why hooks and not `--allowedTools "Bash(uv run odr *)"`: that flag only
   pre-approves a pattern (skips the prompt) — it does NOT deny non-matching
   commands. Confirmed empirically: with only that allow rule, an unrelated
   command like `whoami` still ran, unrestricted. A hook is the only
   mechanism that sees the actual attempted command/skill and can make a
   real allow/deny call. Also confirmed empirically that this design
   actually works end-to-end through a genuine top-level subprocess (spawned
   fresh, not nested inside another Claude session — the earlier
   nested-subprocess spike where the hook silently didn't fire was the
   confound, not the hook mechanism): a live `df -h` attempt came back
   denied with exactly `bash_gate.py`'s own denial text.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

from . import settings

_SYSTEM_PROMPT_ADDENDUM = (
    "You are running in a restricted, business-user-facing session for the "
    "Ops Data Reporter chat UI. You can build and inspect reports via "
    "`uv run odr ...` and the odr-report / odr-new-chart / odr-new-domain "
    "skills, and you can read files. General shell access, file writes/edits, "
    "and web access are intentionally disabled for this session's safety, "
    "not a misconfiguration — if a tool is denied, briefly say it's outside "
    "this chat's scope rather than speculating about a broken setup."
)

_ALLOWED_TOOL_SET = "Read,Glob,Grep,Bash,Skill"

_WROTE_RE = re.compile(r"\bwrote\s+(\S.*?\.html)\b")

_ERROR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"MissingCredentialsError|Postgres credentials not configured", re.I),
        "Missing database credentials — check the repo's .env file.",
    ),
    (
        re.compile(r"permission denied for (view|table|relation)", re.I),
        "The database user doesn't have access to that table/view — check Postgres grants.",
    ),
    (
        re.compile(r"ValueError.*period", re.I),
        "That period isn't available for this role — ask for a period the role actually has data for.",
    ),
]


@dataclass
class ChatEvent:
    type: str
    data: dict[str, Any]


def _rendered_settings_json() -> str:
    """Load the checked-in settings template and substitute both hooks'
    interpreter/script paths with the running Python's actual absolute
    paths (resolved at call time, not baked into the template file, since
    the template ships in the repo and must work on any machine)."""
    obj = json.loads(settings.CLAUDE_SETTINGS_TEMPLATE.read_text(encoding="utf-8"))
    pre_tool_use = obj["hooks"]["PreToolUse"]
    pre_tool_use[0]["hooks"][0]["command"] = f'"{sys.executable}" "{settings.BASH_GATE_SCRIPT}"'
    pre_tool_use[1]["hooks"][0]["command"] = f'"{sys.executable}" "{settings.SKILL_GATE_SCRIPT}"'
    return json.dumps(obj)


def build_argv(message: str, *, resume_session_id: str | None) -> list[str]:
    argv = [
        "claude",
        "-p", message,
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--permission-mode", "manual",
        "--tools", _ALLOWED_TOOL_SET,
        "--settings", _rendered_settings_json(),
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--append-system-prompt", _SYSTEM_PROMPT_ADDENDUM,
    ]
    if resume_session_id:
        argv += ["--resume", resume_session_id]
    return argv


def humanize_tool_call(name: str, tool_input: dict) -> str:
    if name == "Bash":
        return f"Running: {tool_input.get('command', '')}"
    if name == "Skill":
        skill_name = tool_input.get("skill") or tool_input.get("name") or tool_input.get("command") or ""
        return f"Invoking skill: {skill_name}" if skill_name else "Invoking a skill"
    if name in ("Read", "Glob", "Grep"):
        target = tool_input.get("file_path") or tool_input.get("pattern") or tool_input.get("path") or ""
        verb = "Searching" if name in ("Glob", "Grep") else "Reading"
        return f"{verb}: {target}" if target else verb
    return f"Using {name}"


def explain_error(raw: str) -> str:
    for pattern, friendly in _ERROR_PATTERNS:
        if pattern.search(raw):
            return friendly
    return raw[:500] if raw else "Something went wrong."


def _artifact_url_path(matched_path: str) -> str | None:
    """`wrote <path>` in a Bash tool_result gives an absolute filesystem
    path (odr build-role writes under _ARTIFACTS_DIR, always absolute).
    Convert it to the relative path the frontend can turn straight into
    ``/artifacts/<value>`` — path handling belongs here, not in JS."""
    try:
        resolved = Path(matched_path).resolve()
        rel = resolved.relative_to(settings.ARTIFACTS_DIR.resolve())
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def _translate(obj: dict) -> list[ChatEvent]:
    t = obj.get("type")

    if t == "system" and obj.get("subtype") == "init":
        sid = obj.get("session_id")
        return [ChatEvent("session", {"session_id": sid})] if sid else []

    if t == "system" and obj.get("subtype") == "permission_denied":
        tool_name = obj.get("tool_name", "tool")
        return [
            ChatEvent(
                "tool_denied",
                {
                    "tool": tool_name,
                    "label": f"Blocked: {tool_name}",
                    "detail": obj.get("message", ""),
                },
            )
        ]

    if t == "stream_event":
        event = obj.get("event", {})
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if text:
                    return [ChatEvent("text", {"delta": text})]
        return []

    if t == "assistant":
        out = []
        for block in obj.get("message", {}).get("content", []) or []:
            if block.get("type") == "tool_use":
                name = block.get("name", "")
                tool_input = block.get("input", {}) or {}
                out.append(
                    ChatEvent(
                        "tool_start",
                        {
                            "tool": name,
                            "label": humanize_tool_call(name, tool_input),
                            "raw_input": tool_input,
                        },
                    )
                )
        return out

    if t == "user":
        out = []
        for block in obj.get("message", {}).get("content", []) or []:
            if block.get("type") != "tool_result":
                continue
            content = block.get("content", "")
            content_text = content if isinstance(content, str) else json.dumps(content)
            is_error = bool(block.get("is_error"))

            payload: dict[str, Any] = {
                "summary": explain_error(content_text) if is_error else content_text[:400],
                "is_error": is_error,
            }
            m = _WROTE_RE.search(content_text)
            if m:
                url_path = _artifact_url_path(m.group(1).strip())
                if url_path:
                    payload["wrote_artifact"] = url_path
            out.append(ChatEvent("tool_result", payload))
        return out

    if t == "result":
        if obj.get("is_error"):
            return [
                ChatEvent(
                    "error",
                    {"message": explain_error(obj.get("result", "") or ""), "kind": "nonzero_exit"},
                )
            ]
        return [
            ChatEvent(
                "done",
                {
                    "final_text": obj.get("result", ""),
                    "cost_usd": obj.get("total_cost_usd"),
                    "duration_ms": obj.get("duration_ms"),
                },
            )
        ]

    return []


async def run_turn(message: str, *, resume_session_id: str | None) -> AsyncIterator[ChatEvent]:
    """Run one chat turn against the restricted `claude` subprocess,
    yielding ChatEvents as they arrive. Always ends with exactly one
    terminal event (``done`` xor ``error``), including on timeout or an
    unexpected process exit."""
    if settings.claude_binary() is None:
        yield ChatEvent(
            "error",
            {"message": "Claude Code CLI isn't available on this machine.", "kind": "cli_not_found"},
        )
        return

    argv = build_argv(message, resume_session_id=resume_session_id)

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(settings.REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        yield ChatEvent("error", {"message": f"Failed to start claude: {exc}", "kind": "cli_not_found"})
        return

    terminal_sent = False
    deadline = time.monotonic() + settings.CHAT_TIMEOUT_SECONDS

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                await proc.wait()
                yield ChatEvent(
                    "error",
                    {"message": "This is taking longer than expected — try again or check odr doctor.", "kind": "timeout"},
                )
                terminal_sent = True
                break

            try:
                raw_line = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            except asyncio.TimeoutError:
                continue  # loop back, the deadline check above will fire

            if not raw_line:  # EOF
                break

            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # one malformed line never kills the whole turn

            for ev in _translate(obj):
                if ev.type in ("done", "error"):
                    terminal_sent = True
                yield ev

        if proc.returncode is None:
            await proc.wait()
    finally:
        if proc.returncode is None:
            proc.kill()
        if not terminal_sent:
            stderr_text = ""
            if proc.stderr is not None:
                try:
                    raw_err = await asyncio.wait_for(proc.stderr.read(), timeout=5)
                    stderr_text = raw_err.decode("utf-8", errors="replace").strip()
                except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                    pass
            yield ChatEvent(
                "error",
                {
                    "message": stderr_text[:2000] or "The claude process ended unexpectedly.",
                    "kind": "nonzero_exit",
                },
            )
