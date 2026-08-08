"""ui.backend.routes_api — all /api/* route handlers.

Design principle (see ui/README.md): there is exactly one way any user
intent reaches the `claude` subprocess — POST /api/chat. Skill cards and the
Quick Build form in the frontend are both just structured input into that
one audited path; neither gets its own privileged endpoint.
"""

from __future__ import annotations

import asyncio
import dataclasses
import shutil
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import artifacts, claude_bridge, doctor, roles, session, settings, skills, sse

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "claude_cli": settings.claude_binary(),
        "repo_root": str(settings.REPO_ROOT),
    }


@router.get("/api/doctor")
def doctor_status() -> dict:
    checks = doctor.run_doctor_checks()
    return {
        "ok": all(c.passed for c in checks),
        "checks": [dataclasses.asdict(c) for c in checks],
        "ran_at": time.time(),
    }


@router.get("/api/skills")
def list_skills() -> dict:
    return {"skills": [dataclasses.asdict(s) for s in skills.list_skills()]}


@router.get("/api/roles")
def list_roles() -> dict:
    return {"roles": [dataclasses.asdict(r) for r in roles.list_roles()]}


@router.get("/api/artifacts")
def list_artifacts(limit: int = 30) -> dict:
    return {"artifacts": [dataclasses.asdict(a) for a in artifacts.list_artifacts(limit=limit)]}


@router.get("/api/history")
def history() -> dict:
    state = session.STATE
    return {
        "session_id": state.session_id,
        "messages": [dataclasses.asdict(m) for m in state.messages],
    }


class ResetResponse(BaseModel):
    ok: bool


@router.post("/api/reset", response_model=ResetResponse)
async def reset() -> ResetResponse:
    state = session.STATE
    if state.current_proc is not None and state.current_proc.returncode is None:
        state.current_proc.kill()
    state.reset()
    return ResetResponse(ok=True)


class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(req: ChatRequest):
    state = session.STATE

    if state.lock.locked():
        raise HTTPException(status_code=409, detail="A turn is already in progress.")

    async def _stream():
        async with state.lock:
            state.messages.append(session.Message(role="user", text=req.message))
            assistant_text_parts: list[str] = []

            async for event in claude_bridge.run_turn(
                req.message, resume_session_id=state.session_id
            ):
                if event.type == "session" and not state.session_id:
                    state.session_id = event.data.get("session_id")
                elif event.type == "text":
                    assistant_text_parts.append(event.data.get("delta", ""))
                elif event.type == "done":
                    final_text = event.data.get("final_text") or "".join(assistant_text_parts)
                    state.messages.append(session.Message(role="assistant", text=final_text))

                yield sse.format_event(event)

    return StreamingResponse(_stream(), media_type="text/event-stream")
