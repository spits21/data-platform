"""capacity_lines — time series with a breach/threshold line, a shaded
breach region, and an annotation on the worst breach point.
Expects ``date, value`` (+ an optional per-row ``threshold_col``, else a
constant ``threshold`` cfg value).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec

_BREACH_FILL = "rgba(208,2,24,0.15)"


def sample() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=12, freq="W")
    values = [62, 68, 74, 79, 83, 91, 88, 76, 70, 85, 94, 81]
    return pd.DataFrame({"date": dates, "value": values})


def build(
    df: pd.DataFrame,
    *,
    date_col: str = "date",
    value_col: str = "value",
    threshold: float = 80.0,
    threshold_col: str | None = None,
    y_title: str = "Value",
    series_name: str = "Value",
) -> go.Figure:
    d = df.sort_values(date_col)
    threshold_series = (
        d[threshold_col] if threshold_col and threshold_col in d.columns
        else pd.Series([threshold] * len(d), index=d.index)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=d[date_col],
            y=threshold_series,
            mode="lines",
            line={"dash": "dash", "color": theme.COLORS["text_muted"], "width": 1.5},
            name="Threshold",
            hovertemplate=f"Threshold ({y_title}): %{{y:,.1f}}<extra></extra>",
        )
    )

    breach_y = d[value_col].where(d[value_col] > threshold_series, threshold_series)
    fig.add_trace(
        go.Scatter(
            x=d[date_col],
            y=breach_y,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=_BREACH_FILL,
            name="Breach",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=d[date_col],
            y=d[value_col],
            mode="lines+markers",
            name=series_name,
            line={"color": theme.COLORS["cyan"]},
            hovertemplate=f"%{{x|%b %d}}<br>{series_name} ({y_title}): %{{y:,.1f}}<extra></extra>",
        )
    )

    breaches = d[d[value_col] > threshold_series]
    if not breaches.empty:
        worst = breaches.loc[breaches[value_col].idxmax()]
        fig.add_annotation(
            x=worst[date_col],
            y=worst[value_col],
            text=f"Peak breach: {worst[value_col]:,.1f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-32,
            font={"color": theme.COLORS["red"], "size": 11},
        )

    fig.update_layout(yaxis={"title": {"text": y_title}})
    return theme.apply_theme(fig, "timeseries")


CHART = ChartSpec(
    id="capacity_lines",
    title="Capacity / Threshold Line",
    family="time series",
    chart_type="timeseries",
    build=build,
    sample=sample,
    interactions="breach/threshold line + shaded region + annotation",
)
