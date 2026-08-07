"""ridgeline — layered density ("joyplot") read across categories.
Expects a tidy long-format DataFrame: ``category, value`` (many rows per
category). KDE is computed by hand (Gaussian kernel, Silverman bandwidth) to
avoid a scipy dependency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    for cat, mu, sigma in [("Q1", 10, 2.5), ("Q2", 13, 2.0), ("Q3", 16, 3.0), ("Q4", 12, 2.2)]:
        for v in rng.normal(mu, sigma, 200):
            rows.append({"category": cat, "value": v})
    return pd.DataFrame(rows)


def _kde(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    n = len(values)
    std = float(np.std(values)) or 1.0
    bandwidth = 1.06 * std * n ** (-1 / 5)  # Silverman's rule of thumb
    diffs = (grid[:, None] - values[None, :]) / bandwidth
    density = np.exp(-0.5 * diffs**2).sum(axis=1) / (n * bandwidth * np.sqrt(2 * np.pi))
    return density


def _to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def build(
    df: pd.DataFrame,
    *,
    category_col: str = "category",
    value_col: str = "value",
    x_title: str = "Value",
    category_order: list[str] | None = None,
) -> go.Figure:
    categories = category_order or list(dict.fromkeys(df[category_col]))
    grid = np.linspace(df[value_col].min(), df[value_col].max(), 200)

    densities = {}
    peak = 0.0
    for cat in categories:
        vals = df.loc[df[category_col] == cat, value_col].to_numpy()
        d = _kde(vals, grid)
        densities[cat] = d
        peak = max(peak, float(d.max()))

    offset_step = peak * 0.75 or 1.0
    colorway = theme.COLORWAY

    fig = go.Figure()
    tickvals, ticktext = [], []
    for i, cat in enumerate(categories):
        baseline = i * offset_step
        color = colorway[i % len(colorway)]

        # Invisible baseline trace MUST be added before the density trace:
        # fill="tonexty" on the density trace fills against the PRECEDING
        # trace in the data array, which is this baseline.
        fig.add_trace(
            go.Scatter(
                x=grid,
                y=[baseline] * len(grid),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=grid,
                y=baseline + densities[cat],
                mode="lines",
                line={"color": color, "width": 1.5},
                fill="tonexty",
                fillcolor=_to_rgba(color, 0.35),
                name=str(cat),
                hovertemplate=f"{cat}<br>{x_title}: %{{x:,.1f}}<extra></extra>",
            )
        )
        tickvals.append(baseline)
        ticktext.append(str(cat))

    fig.update_layout(
        xaxis={"title": {"text": x_title}},
        yaxis={"tickvals": tickvals, "ticktext": ticktext, "showgrid": False, "zeroline": False},
        showlegend=False,
    )
    return theme.apply_theme(fig, "ridgeline")


CHART = ChartSpec(
    id="ridgeline",
    title="Ridgeline",
    family="distribution",
    chart_type="ridgeline",
    build=build,
    sample=sample,
    interactions="layered density read",
)
