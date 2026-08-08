"""ui.backend.artifacts — recent-reports listing for the sidebar."""

from __future__ import annotations

from dataclasses import dataclass

from . import settings


@dataclass
class ArtifactInfo:
    role: str
    filename: str
    rel_path: str  # relative to artifacts/, e.g. "opsgov_incidents/foo.html" — used to build /artifacts/<rel_path>
    mtime: float


def list_artifacts(limit: int = 30) -> list[ArtifactInfo]:
    if not settings.ARTIFACTS_DIR.exists():
        return []

    items: list[ArtifactInfo] = []
    for path in settings.ARTIFACTS_DIR.glob("**/*.html"):
        rel = path.relative_to(settings.ARTIFACTS_DIR)
        role = rel.parts[0] if len(rel.parts) > 1 else ""
        items.append(
            ArtifactInfo(
                role=role,
                filename=path.name,
                rel_path=str(rel).replace("\\", "/"),
                mtime=path.stat().st_mtime,
            )
        )

    items.sort(key=lambda a: a.mtime, reverse=True)
    return items[:limit]
