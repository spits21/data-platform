"""PreToolUse hook for the ODR chat UI's restricted Claude Code subprocess.

Gates the ``Skill`` tool: only odr-report / odr-new-chart / odr-new-domain
may be invoked. Without this, `--tools` only restricts the toolset to
"Skill exists at all" — it can't say *which* skill; a user could otherwise
ask for any of the OTHER skills visible in a normal Claude Code session
(simplify, code-review, doctor, ...), which are not part of the ODR chat
UI's intended scope. Confirmed via testing: Skill tool_input has a `skill`
key, e.g. ``{"skill": "simplify"}``.
"""

from __future__ import annotations

import json
import sys

_ALLOWED_SKILLS = {"odr-report", "odr-new-chart", "odr-new-domain"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _emit_decision("deny", "Could not parse the tool call for permission checking.")
        return 0

    skill = payload.get("tool_input", {}).get("skill", "")

    if skill in _ALLOWED_SKILLS:
        _emit_decision("allow", "Matches the odr-report chat UI's allowed skill list.")
    else:
        _emit_decision(
            "deny",
            "This chat can only use the odr-report / odr-new-chart / odr-new-domain "
            "skills, not other Claude Code skills.",
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
