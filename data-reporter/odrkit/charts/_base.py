"""odrkit.charts._base — the ChartSpec contract every chart plugin implements.

A chart is a folder under ``odrkit/charts/<id>/`` exporting ``CHART =
ChartSpec(...)``. The registry in ``odrkit/charts/__init__.py``
auto-discovers it: adding a chart means dropping a folder, no registry edit.

Load-bearing rules for ``build(df, **cfg) -> go.Figure``:
- Must return an ALREADY-THEMED figure — last line is
  ``return theme.apply_theme(fig, chart_type)``.
- ``chart_type`` must be one of ``theme.VALID_CHART_TYPES``.
- ``sample() -> pd.DataFrame`` returns tiny illustrative data so
  ``build(sample())`` renders standalone — this is what ``self_test()`` calls.
- Hover labels must name metric AND unit explicitly (e.g. "Revenue ($M)"),
  never a bare unit.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go

from .. import theme


@dataclass(frozen=True)
class ChartSpec:
    """A registered, self-testing, themed chart plugin.

    ``id`` is the registry key (and the folder name by convention).
    ``family`` is a coarse grouping used by ``list-charts`` / the viz catalog
    (e.g. "time series", "bar", "hierarchy") — display metadata only.
    """

    id: str
    title: str
    family: str
    chart_type: str
    build: Callable[..., go.Figure]
    sample: Callable[[], pd.DataFrame]
    interactions: str = ""

    def __post_init__(self) -> None:
        if self.chart_type not in theme.VALID_CHART_TYPES:
            raise ValueError(
                f"chart {self.id!r}: chart_type {self.chart_type!r} not in "
                f"theme.VALID_CHART_TYPES {theme.VALID_CHART_TYPES}"
            )

    def source_code(self) -> str:
        """Return the source of this chart's ``build`` function (for the
        "view code" drawer / viz catalog). Degrades to '' if unavailable
        (e.g. dynamically defined)."""
        try:
            return inspect.getsource(self.build)
        except (OSError, TypeError):
            return ""

    def self_test(self) -> go.Figure:
        """Build the chart from its own ``sample()`` and assert the
        resulting figure is themed. Raises AssertionError on failure.

        This is the contract ``odr doctor`` runs against every registered
        chart: a broken sample, a build() that forgets to theme, or a
        chart_type typo all fail loudly here rather than at report-render
        time.
        """
        df = self.sample()
        assert isinstance(df, pd.DataFrame), (
            f"chart {self.id!r}: sample() must return a DataFrame"
        )
        assert not df.empty, f"chart {self.id!r}: sample() returned an empty DataFrame"

        fig = self.build(df)
        assert isinstance(fig, go.Figure), (
            f"chart {self.id!r}: build() must return a go.Figure"
        )

        layout = fig.to_plotly_json().get("layout", {})
        assert layout.get("paper_bgcolor") == "rgba(0,0,0,0)", (
            f"chart {self.id!r}: build() output is not themed "
            f"(paper_bgcolor != transparent — did you forget "
            f"theme.apply_theme(fig, chart_type)?)"
        )
        assert "colorway" in layout, (
            f"chart {self.id!r}: build() output is missing colorway "
            f"(did you forget theme.apply_theme?)"
        )
        return fig
