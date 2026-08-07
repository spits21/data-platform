"""timeseries_multi — multi-series line chart with a rangeslider, 1Y/3Y/All
range-selector buttons, legend isolate, and unified hover.

Expects a tidy long-format DataFrame: ``date, series, value`` (column names
configurable via cfg).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=24, freq="MS")
    rows = []
    for series, base, slope in [("Revenue", 90, 1.6), ("Opex", 60, 0.7)]:
        for i, d in enumerate(dates):
            rows.append({"date": d, "series": series, "value": base + slope * i})
    return pd.DataFrame(rows)


def build(
    df: pd.DataFrame,
    *,
    date_col: str = "date",
    series_col: str = "series",
    value_col: str = "value",
    y_title: str = "$M",
    metric_name: str = "Value",
) -> go.Figure:
    fig = go.Figure()
    for series_name, sub in df.groupby(series_col, sort=False):
        sub = sub.sort_values(date_col)
        label = f"{series_name} {metric_name}".strip() if metric_name else str(series_name)
        fig.add_trace(
            go.Scatter(
                x=sub[date_col],
                y=sub[value_col],
                mode="lines+markers",
                name=str(series_name),
                hovertemplate=(
                    f"%{{x|%b %Y}}<br>{label} ({y_title}): %{{y:,.1f}}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        yaxis={"title": {"text": y_title}},
        xaxis={
            "rangeslider": {"visible": True},
            "rangeselector": {
                "buttons": [
                    {"count": 12, "label": "1Y", "step": "month", "stepmode": "backward"},
                    {"count": 36, "label": "3Y", "step": "month", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ]
            },
        },
        hovermode="x unified",
    )
    return theme.apply_theme(fig, "timeseries")


CHART = ChartSpec(
    id="timeseries_multi",
    title="Multi-Series Time Series",
    family="time series",
    chart_type="timeseries",
    build=build,
    sample=sample,
    interactions="rangeslider, 1Y/3Y/All range buttons, legend isolate, unified hover",
)
