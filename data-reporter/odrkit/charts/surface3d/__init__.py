"""surface3d — 3-D surface (orbit/rotate/zoom + colorbar are native Plotly
Surface behavior). Expects a tidy long-format DataFrame (``x, y, z``),
pivoted internally into a grid.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rows = []
    for xi in range(6):
        for yi in range(5):
            rows.append({"x": xi, "y": yi, "z": (xi - 2.5) ** 2 + (yi - 2) ** 2})
    return pd.DataFrame(rows)


def build(
    df: pd.DataFrame,
    *,
    x_col: str = "x",
    y_col: str = "y",
    z_col: str = "z",
    x_title: str = "X",
    y_title: str = "Y",
    z_title: str = "Value",
) -> go.Figure:
    pivot = df.pivot(index=y_col, columns=x_col, values=z_col)

    fig = go.Figure(
        go.Surface(
            x=list(pivot.columns),
            y=list(pivot.index),
            z=pivot.values,
            colorscale=theme.odr_sequential_colorscale(),
            colorbar={"title": {"text": z_title}},
            hovertemplate=(
                f"{x_title}: %{{x}}<br>{y_title}: %{{y}}<br>{z_title}: %{{z:,.2f}}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        scene={
            "xaxis": {"title": {"text": x_title}},
            "yaxis": {"title": {"text": y_title}},
            "zaxis": {"title": {"text": z_title}},
        }
    )
    return theme.apply_theme(fig, "surface3d")


CHART = ChartSpec(
    id="surface3d",
    title="3D Surface",
    family="3-D",
    chart_type="surface3d",
    build=build,
    sample=sample,
    interactions="orbit / rotate / zoom, colorbar",
)
