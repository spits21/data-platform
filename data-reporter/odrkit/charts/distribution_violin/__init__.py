"""distribution_violin — violin + inner box + jittered points per category.
Expects a tidy long-format DataFrame: ``category, value``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    rows = []
    for cat, mu, sigma in [("Fixed", 2.1, 0.6), ("ARM", 3.4, 1.1), ("Hybrid", 2.8, 0.9)]:
        for v in rng.normal(mu, sigma, 60):
            rows.append({"category": cat, "value": v})
    return pd.DataFrame(rows)


def build(
    df: pd.DataFrame,
    *,
    category_col: str = "category",
    value_col: str = "value",
    y_title: str = "Value",
) -> go.Figure:
    colorway = theme.COLORWAY
    fig = go.Figure()
    for i, (cat, sub) in enumerate(df.groupby(category_col, sort=False)):
        color = colorway[i % len(colorway)]
        fig.add_trace(
            go.Violin(
                y=sub[value_col],
                name=str(cat),
                box_visible=True,
                points="all",
                pointpos=0,
                jitter=0.35,
                meanline_visible=True,
                line={"color": color},
                fillcolor=color,
                opacity=0.55,
                marker={"size": 3, "color": color},
                hovertemplate=f"{cat}<br>{y_title}: %{{y:,.2f}}<extra></extra>",
            )
        )
    fig.update_layout(yaxis={"title": {"text": y_title}}, showlegend=False)
    return theme.apply_theme(fig, "violin")


CHART = ChartSpec(
    id="distribution_violin",
    title="Violin Distribution",
    family="distribution",
    chart_type="violin",
    build=build,
    sample=sample,
    interactions="violin + box + points",
)
