"""ui.backend.app — FastAPI app: static mounts, /theme.css, /api/* routes,
and a startup hook that opens a browser tab when `odr ui` asked for one.

Runnable two ways: `odr ui` (uvicorn.run("backend.app:app", app_dir=...))
or directly (`uvicorn backend.app:app`, e.g. inside the optional Docker
image) — the browser-open behavior is gated on an env var so it never fires
in a headless/container context by accident.
"""

from __future__ import annotations

import os
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from odrkit import theme

from . import settings
from .routes_api import router as api_router


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if os.environ.get("ODR_UI_OPEN_BROWSER"):
        host = os.environ.get("ODR_UI_HOST", settings.DEFAULT_HOST)
        port = os.environ.get("ODR_UI_PORT", str(settings.DEFAULT_PORT))
        # 0.0.0.0 isn't a browsable address — open localhost instead.
        display_host = "127.0.0.1" if host == "0.0.0.0" else host
        webbrowser.open(f"http://{display_host}:{port}/")
    yield


app = FastAPI(title="Ops Data Reporter — Chat UI", lifespan=_lifespan)

app.include_router(api_router)

settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(settings.UI_DIR / "static")), name="assets")
app.mount("/artifacts", StaticFiles(directory=str(settings.ARTIFACTS_DIR)), name="artifacts")


@app.get("/theme.css")
def theme_css() -> Response:
    """Live brand CSS vars, straight from odrkit.theme — single source of
    truth, zero duplication (see odrkit/theme.py)."""
    return Response(theme.to_css_vars(), media_type="text/css")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(settings.UI_DIR / "static" / "index.html"))
