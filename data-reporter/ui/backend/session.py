"""ui.backend.session — single in-memory conversation state.

The ODR chat UI runs locally per business user (see ui/README.md) — one
running server instance, one active conversation at a time. ``lock`` is the
literal enforcement of that: ``POST /api/chat`` holds it for the duration of
a turn and a second concurrent request gets a calm 409 instead of a
corrupted interleaved stream.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "user" | "assistant"
    text: str
    ts: float = field(default_factory=time.time)


@dataclass
class SessionState:
    session_id: str | None = None
    messages: list[Message] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    current_proc: asyncio.subprocess.Process | None = None

    def reset(self) -> None:
        self.session_id = None
        self.messages = []
        self.current_proc = None


STATE = SessionState()
