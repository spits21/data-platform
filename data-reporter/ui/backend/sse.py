"""ui.backend.sse — Server-Sent Events wire-format helper.

``humanize_tool_call``/``explain_error`` live in claude_bridge.py (next to
the parser that produces the data they operate on); this module is just the
``ChatEvent -> "event: ...\\ndata: ...\\n\\n"`` framing, kept separate so the
wire format is a one-line change independent of parsing logic.
"""

from __future__ import annotations

import json

from .claude_bridge import ChatEvent


def format_event(event: ChatEvent) -> str:
    payload = json.dumps(event.data, default=str)
    return f"event: {event.type}\ndata: {payload}\n\n"
