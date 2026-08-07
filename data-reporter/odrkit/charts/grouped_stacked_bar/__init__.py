"""grouped_stacked_bar — bar chart supporting both grouped and stacked
layouts from the same tidy long-format DataFrame: ``category, group, value``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "category": ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3"],
            "group": ["Salaries", "Other", "Salaries", "Other", "Salaries", "Other"],
            "value": [22.1, 8.4, 23.0, 9.1, 24.5, 8.9],
        }
    )


def build(
    df: pd.DataFrame,
    *,
    mode: str = "grouped",
    category_col: str = "category",
    group_col: str = "group",
    value_col: str = "value",
    y_title: str = "$M",
) -> go.Figure:
    fig = go.Figure()
    for group_name, sub in df.groupby(group_col, sort=False):
        fig.add_trace(
            go.Bar(
                x=list(sub[category_col]),
                y=list(sub[value_col]),
                name=str(group_name),
                hovertemplate=(
                    f"%{{x}}<br>{group_name} ({y_title}): %{{y:,.1f}}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        barmode="stack" if mode == "stacked" else "group",
        yaxis={"title": {"text": y_title}},
    )
    return theme.apply_theme(fig, "bar")


CHART = ChartSpec(
    id="grouped_stacked_bar",
    title="Grouped / Stacked Bar",
    family="bar",
    chart_type="bar",
    build=build,
    sample=sample,
    interactions="grouped/stacked, hover, legend toggle",
)
