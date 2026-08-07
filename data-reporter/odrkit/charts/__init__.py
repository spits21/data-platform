"""odrkit.charts — the auto-discovered chart registry.

Every immediate subpackage of ``odrkit/charts/`` that exports a module-level
``CHART = ChartSpec(...)`` is picked up automatically and added to
``REGISTRY`` keyed by ``CHART.id``. Adding a chart means dropping a folder
here — this file never needs editing.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from ._base import ChartSpec

_PKG_DIR = Path(__file__).resolve().parent


def _discover() -> dict[str, ChartSpec]:
    registry: dict[str, ChartSpec] = {}
    for info in pkgutil.iter_modules([str(_PKG_DIR)]):
        if not info.ispkg or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        chart = getattr(module, "CHART", None)
        if chart is None:
            continue
        if not isinstance(chart, ChartSpec):
            raise TypeError(
                f"odrkit.charts.{info.name}.CHART must be a ChartSpec, "
                f"got {type(chart)!r}"
            )
        if chart.id in registry:
            raise ValueError(
                f"duplicate chart id {chart.id!r}: registered by both "
                f"{registry[chart.id]} and {info.name}"
            )
        registry[chart.id] = chart
    return dict(sorted(registry.items()))


REGISTRY: dict[str, ChartSpec] = _discover()

__all__ = ["REGISTRY", "ChartSpec"]
