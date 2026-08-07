"""ohlc_box — range chart with two modes:

- ``mode="box"`` (default) — a box plot per category, for reading the spread
  of a continuous metric across categories.
- ``mode="ohlc"`` — a financial open/high/low/close range chart.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for cat, mu, sigma in [("Low", 8, 2), ("Medium", 14, 3), ("High", 22, 5)]:
        for v in rng.normal(mu, sigma, 20):
            rows.append({"category": cat, "value": max(0.0, v)})
    return pd.DataFrame(rows)


def _build_box(df: pd.DataFrame, category_col: str, value_col: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    for cat, sub in df.groupby(category_col, sort=False):
        fig.add_trace(
            go.Box(
                y=sub[value_col],
                name=str(cat),
                boxpoints="outliers",
                marker={"color": theme.COLORS["cyan"]},
                line={"color": theme.COLORS["dark_teal"]},
                hovertemplate=f"{cat}<br>{y_title}: %{{y:,.1f}}<extra></extra>",
            )
        )
    fig.update_layout(yaxis={"title": {"text": y_title}}, showlegend=False)
    return fig


def _build_ohlc(df: pd.DataFrame, date_col: str, open_col: str, high_col: str, low_col: str, close_col: str, y_title: str) -> go.Figure:
    fig = go.Figure(
        go.Ohlc(
            x=df[date_col],
            open=df[open_col],
            high=df[high_col],
            low=df[low_col],
            close=df[close_col],
            increasing={"line": {"color": theme.COLORS["dark_teal"]}},
            decreasing={"line": {"color": theme.COLORS["red"]}},
        )
    )
    fig.update_layout(yaxis={"title": {"text": y_title}}, xaxis={"rangeslider": {"visible": False}})
    return fig


def build(
    df: pd.DataFrame,
    *,
    mode: str = "box",
    category_col: str = "category",
    value_col: str = "value",
    date_col: str = "date",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    y_title: str = "Value",
) -> go.Figure:
    if mode == "ohlc":
        fig = _build_ohlc(df, date_col, open_col, high_col, low_col, close_col, y_title)
    else:
        fig = _build_box(df, category_col, value_col, y_title)
    return theme.apply_theme(fig, "distribution")


CHART = ChartSpec(
    id="ohlc_box",
    title="OHLC / Box Range",
    family="range",
    chart_type="distribution",
    build=build,
    sample=sample,
    interactions="OHLC / box range reading",
)
