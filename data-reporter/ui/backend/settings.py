"""ui.backend.settings — paths and small config for the ODR chat UI backend.

Deliberately tiny: everything here is either a path derived from this
file's own location (so it works regardless of cwd) or an env var the `odr
ui` CLI command sets before starting uvicorn.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent  # data-reporter/ui
REPO_ROOT = UI_DIR.parent  # data-reporter/
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

SETTINGS_DIR = UI_DIR / "settings"
CLAUDE_SETTINGS_TEMPLATE = SETTINGS_DIR / "claude-settings.json"
BASH_GATE_SCRIPT = SETTINGS_DIR / "bash_gate.py"
SKILL_GATE_SCRIPT = SETTINGS_DIR / "skill_gate.py"

DEFAULT_HOST = os.environ.get("ODR_UI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ODR_UI_PORT", "8110") or "8110")
OPEN_BROWSER = bool(os.environ.get("ODR_UI_OPEN_BROWSER"))

# Overall wall-clock budget for one chat turn (subprocess kill + error event
# past this, so the frontend never hangs on a dead stream).
CHAT_TIMEOUT_SECONDS = 600


def claude_binary() -> str | None:
    return shutil.which("claude")
