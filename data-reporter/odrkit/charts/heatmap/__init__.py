"""heatmap — matrix chart from a tidy long-format DataFrame
(``row, col, value``), pivoted internally. Supports the ODR on-brand
sequential colorscale (default) or the Turbo colorscale for percentile heat.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rows = []
    for dept in ["Sales", "Eng", "Marketing"]:
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            rows.append(
                {
                    "row": dept,
                    "col": quarter,
                    "value": {"Sales": 12, "Eng": 22, "Marketing": 8}[dept]
                    + hash((dept, quarter)) % 5,
                }
            )
    return pd.DataFrame(rows)


def build(
    df: pd.DataFrame,
    *,
    row_col: str = "row",
    col_col: str = "col",
    value_col: str = "value",
    colorscale: str = "odr",
    value_title: str = "Value",
) -> go.Figure:
    pivot = df.pivot(index=row_col, columns=col_col, values=value_col)
    scale = theme.turbo_colorscale() if colorscale == "turbo" else theme.odr_sequential_colorscale()

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale=scale,
            colorbar={"title": {"text": value_title}},
            hovertemplate=(
                f"%{{y}} / %{{x}}<br>{value_title}: %{{z:,.1f}}<extra></extra>"
            ),
        )
    )
    return theme.apply_theme(fig, "heatmap")


CHART = ChartSpec(
    id="heatmap",
    title="Heatmap",
    family="matrix",
    chart_type="heatmap",
    build=build,
    sample=sample,
    interactions="Turbo or on-brand ODR colorscale, colorbar",
)
