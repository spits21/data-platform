"""funnel — stage-conversion funnel with percent-of-initial annotations.
Expects a tidy DataFrame of ordered stages: ``stage, value``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stage": ["Leads", "Qualified", "Proposal", "Negotiation", "Closed Won"],
            "value": [1000, 620, 340, 210, 130],
        }
    )


def build(
    df: pd.DataFrame,
    *,
    stage_col: str = "stage",
    value_col: str = "value",
    value_title: str = "Count",
) -> go.Figure:
    fig = go.Figure(
        go.Funnel(
            y=list(df[stage_col]),
            x=list(df[value_col]),
            textposition="inside",
            textinfo="value+percent initial",
            marker={"color": theme.COLORWAY[: len(df)]},
            connector={"line": {"color": theme.COLORS["border"], "width": 1}},
            hovertemplate=f"%{{y}}<br>{value_title}: %{{x:,.0f}}<extra></extra>",
        )
    )
    return theme.apply_theme(fig, "funnel")


CHART = ChartSpec(
    id="funnel",
    title="Funnel",
    family="funnel",
    chart_type="funnel",
    build=build,
    sample=sample,
    interactions="stage conversion, percent-of-initial",
)
