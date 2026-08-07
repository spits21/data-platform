"""kpi_indicators — a row of Plotly Indicator "number + delta" cards.

Domain-agnostic: any role can drive it with a tidy DataFrame of
``label, value`` (+ optional ``prior`` for the delta and ``suffix`` for a
unit string appended to the number, e.g. "$M", "%").
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label": ["Revenue ($M)", "EBITDA Margin (%)", "Headcount"],
            "value": [128.4, 24.1, 412],
            "prior": [121.9, 22.6, 398],
            "suffix": ["", "", ""],
        }
    )


def build(
    df: pd.DataFrame,
    *,
    label_col: str = "label",
    value_col: str = "value",
    prior_col: str = "prior",
    suffix_col: str = "suffix",
    number_format: str = ",.1f",
) -> go.Figure:
    n = len(df)
    fig = go.Figure()
    width = 1.0 / n
    for i, row in enumerate(df.itertuples(index=False)):
        label = getattr(row, label_col)
        value = getattr(row, value_col)
        prior = getattr(row, prior_col, None) if prior_col in df.columns else None
        suffix = getattr(row, suffix_col, "") if suffix_col in df.columns else ""

        delta_cfg = None
        if prior is not None and pd.notna(prior):
            delta_cfg = {
                "reference": prior,
                "valueformat": number_format,
                "increasing": {"color": theme.COLORS["dark_teal"]},
                "decreasing": {"color": theme.COLORS["red"]},
            }

        fig.add_trace(
            go.Indicator(
                mode="number+delta" if delta_cfg else "number",
                value=value,
                number={"valueformat": number_format, "suffix": suffix},
                delta=delta_cfg,
                title={"text": str(label), "font": {"size": 14}},
                domain={"x": [i * width, (i + 1) * width - 0.02], "y": [0, 1]},
            )
        )

    fig.update_layout(grid={"rows": 1, "columns": n, "pattern": "independent"})
    return theme.apply_theme(fig, "indicator")


CHART = ChartSpec(
    id="kpi_indicators",
    title="KPI Indicators",
    family="indicator",
    chart_type="indicator",
    build=build,
    sample=sample,
    interactions="number + delta cards / gauges",
)
