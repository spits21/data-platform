"""scatter_bubble — bubble scatter: size + continuous colorbar, rich hover,
optional y=x reference line. Expects a tidy DataFrame with x/y/size/color
columns (names configurable via cfg).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
            "x": [12.0, 18.0, 9.0, 24.0, 15.0],
            "y": [8.0, 22.0, 6.0, 19.0, 14.0],
            "size": [30, 80, 15, 60, 40],
            "color": [1.2, 3.4, 0.8, 2.9, 2.1],
        }
    )


def build(
    df: pd.DataFrame,
    *,
    x_col: str = "x",
    y_col: str = "y",
    size_col: str = "size",
    color_col: str = "color",
    name_col: str = "name",
    x_title: str = "X",
    y_title: str = "Y",
    size_title: str = "Size",
    color_title: str = "Value",
    add_refline: bool = False,
    size_ref_max: float = 46.0,
) -> go.Figure:
    sizes = df[size_col]
    max_size = float(sizes.max()) or 1.0
    scaled = (sizes / max_size) * size_ref_max + 6

    fig = go.Figure(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="markers",
            text=df[name_col] if name_col in df.columns else None,
            marker={
                "size": scaled,
                "color": df[color_col],
                "colorscale": theme.odr_sequential_colorscale(),
                "showscale": True,
                "colorbar": {"title": {"text": color_title}},
                "line": {"width": 1, "color": theme.COLORS["white"]},
            },
            hovertemplate=(
                "%{text}<br>"
                f"{x_title}: %{{x:,.1f}}<br>{y_title}: %{{y:,.1f}}<br>"
                f"{size_title}: %{{marker.size:,.0f}}<br>{color_title}: %{{marker.color:,.2f}}"
                "<extra></extra>"
            ),
        )
    )

    if add_refline:
        lo = float(min(df[x_col].min(), df[y_col].min()))
        hi = float(max(df[x_col].max(), df[y_col].max()))
        fig.add_trace(
            go.Scatter(
                x=[lo, hi],
                y=[lo, hi],
                mode="lines",
                line={"color": theme.COLORS["text_muted"], "dash": "dot", "width": 1},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        xaxis={"title": {"text": x_title}},
        yaxis={"title": {"text": y_title}},
        showlegend=False,
    )
    return theme.apply_theme(fig, "scatter")


CHART = ChartSpec(
    id="scatter_bubble",
    title="Bubble Scatter",
    family="scatter",
    chart_type="scatter",
    build=build,
    sample=sample,
    interactions="size + continuous colorbar, rich hover, optional y=x reference line",
)
