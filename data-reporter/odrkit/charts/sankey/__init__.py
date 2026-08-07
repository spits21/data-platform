"""sankey — flow diagram (node drag, flow hover are native Plotly Sankey
behavior). Expects a tidy link-list DataFrame: ``source, target, value``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source": ["Paid Search", "Paid Search", "Organic", "Organic", "Email"],
            "target": ["MQL", "Bounce", "MQL", "Bounce", "MQL"],
            "value": [420, 180, 260, 90, 140],
        }
    )


def build(
    df: pd.DataFrame,
    *,
    source_col: str = "source",
    target_col: str = "target",
    value_col: str = "value",
    value_title: str = "Count",
) -> go.Figure:
    nodes = list(dict.fromkeys(list(df[source_col]) + list(df[target_col])))
    index = {name: i for i, name in enumerate(nodes)}
    colorway = theme.COLORWAY
    node_colors = [colorway[i % len(colorway)] for i in range(len(nodes))]

    fig = go.Figure(
        go.Sankey(
            node={
                "label": nodes,
                "color": node_colors,
                "pad": 16,
                "thickness": 18,
                "line": {"color": theme.COLORS["border"], "width": 1},
            },
            link={
                "source": [index[s] for s in df[source_col]],
                "target": [index[t] for t in df[target_col]],
                "value": list(df[value_col]),
                "color": theme.COLORS["cyan_dim"],
                "hovertemplate": f"%{{source.label}} → %{{target.label}}<br>{value_title}: %{{value:,.0f}}<extra></extra>",
            },
        )
    )
    return theme.apply_theme(fig, "sankey")


CHART = ChartSpec(
    id="sankey",
    title="Sankey",
    family="flow",
    chart_type="sankey",
    build=build,
    sample=sample,
    interactions="node drag, flow hover",
)
