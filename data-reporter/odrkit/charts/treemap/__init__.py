"""treemap — two-level hierarchy drill (native click-to-zoom) with a
magnitude colorbar on the ODR sequential colorscale.

Expects a tidy DataFrame with a value column plus 1-2 path columns
(``path_cols``), e.g. ``segment, subsegment, value``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "segment": ["Enterprise", "Enterprise", "SMB", "SMB", "Public Sector"],
            "subsegment": ["Software", "Services", "Software", "Services", "Software"],
            "value": [42.0, 18.5, 21.0, 9.5, 12.0],
        }
    )


def _path_to_treemap(
    df: pd.DataFrame, path_cols: tuple[str, ...], value_col: str, root_label: str
):
    ids: list[str] = [root_label]
    labels: list[str] = [root_label]
    parents: list[str] = [""]
    values: list[float] = [df[value_col].sum()]

    lvl1 = df.groupby(path_cols[0])[value_col].sum()
    for name, val in lvl1.items():
        node_id = f"{root_label}/{name}"
        ids.append(node_id)
        labels.append(str(name))
        parents.append(root_label)
        values.append(val)

    if len(path_cols) > 1:
        lvl2 = df.groupby(list(path_cols))[value_col].sum()
        for key, val in lvl2.items():
            p1, p2 = key
            parent_id = f"{root_label}/{p1}"
            node_id = f"{parent_id}/{p2}"
            ids.append(node_id)
            labels.append(str(p2))
            parents.append(parent_id)
            values.append(val)

    return ids, labels, parents, values


def build(
    df: pd.DataFrame,
    *,
    path_cols: tuple[str, ...] = ("segment", "subsegment"),
    value_col: str = "value",
    root_label: str = "Total",
    value_title: str = "$M",
) -> go.Figure:
    ids, labels, parents, values = _path_to_treemap(df, path_cols, value_col, root_label)

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker={
                "colors": values,
                "colorscale": theme.odr_sequential_colorscale(),
                "showscale": True,
                "colorbar": {"title": {"text": value_title}},
            },
            hovertemplate=f"%{{label}}<br>{value_title}: %{{value:,.1f}}<extra></extra>",
        )
    )
    return theme.apply_theme(fig, "treemap")


CHART = ChartSpec(
    id="treemap",
    title="Treemap",
    family="hierarchy",
    chart_type="treemap",
    build=build,
    sample=sample,
    interactions="native click-to-zoom drill, colorbar",
)
