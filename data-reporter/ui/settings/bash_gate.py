"""PreToolUse hook for the ODR chat UI's restricted Claude Code subprocess.

Gates the ``Bash`` tool: only commands starting with ``uv run odr`` are
allowed (that's how odr-report/odr-new-chart/odr-new-domain actually shell
out — see CLAUDE.md); everything else is denied. This is the enforcement
layer for the "restricted to ODR skills" permission scope decided for the
chat UI — see ui/README.md and the plan this was built from.

Why a hook and not just ``--allowedTools``/``--disallowedTools``: those CLI
flags only pre-approve a pattern (skip the prompt) or fully disable a tool —
they cannot express "allow only this sub-pattern, deny everything else" for
one tool. A ``PreToolUse`` hook receives the actual attempted command and can
make that finer-grained decision (confirmed empirically; see the plan's
verification notes).

Claude Code invokes this as: ``python bash_gate.py`` with the tool-call JSON
on stdin, expecting a ``PreToolUse`` hookSpecificOutput JSON on stdout.
"""

from __future__ import annotations

import json
import re
import sys

_ALLOWED_PREFIX = re.compile(r"^\s*uv run odr\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input from Claude Code itself would be unusual; fail
        # closed (deny) rather than silently allowing.
        _emit_decision("deny", "Could not parse the tool call for permission checking.")
        return 0

    command = payload.get("tool_input", {}).get("command", "")

    if _ALLOWED_PREFIX.match(command):
        _emit_decision("allow", "Matches the odr-report chat UI's allowed command prefix.")
    else:
        _emit_decision(
            "deny",
            "This chat is restricted to running 'uv run odr ...' commands "
            "(building/inspecting reports). General shell access is disabled.",
        )
    return 0


def _emit_decision(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


if __name__ == "__main__":
    sys.exit(main())
