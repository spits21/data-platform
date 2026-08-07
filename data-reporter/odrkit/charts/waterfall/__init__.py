"""waterfall — bridge chart with two modes:

- ``mode="level"`` — a standard cumulative bridge (native ``go.Waterfall``,
  ``measure`` in {"relative","total"}): e.g. Revenue -> COGS -> Opex -> EBITDA.
- ``mode="variance"`` — a zero-based budget-vs-actual variance bridge colored
  by favorable/unfavorable (NOT by arithmetic sign — an opex overrun is an
  unfavorable *increase*, colored red even though the bar goes up). Built by
  hand on ``go.Bar`` with running offsets since native Waterfall coloring is
  sign-based only.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "category": ["Revenue", "COGS", "Opex", "EBITDA"],
            "value": [128.4, -54.2, -43.5, 30.7],
            "measure": ["relative", "relative", "relative", "total"],
            "favorable": [True, False, False, True],
        }
    )


def _build_level(df: pd.DataFrame, category_col: str, value_col: str, measure_col: str, y_title: str) -> go.Figure:
    measures = list(df[measure_col]) if measure_col in df.columns else (
        ["relative"] * (len(df) - 1) + ["total"]
    )
    fig = go.Figure(
        go.Waterfall(
            x=list(df[category_col]),
            y=list(df[value_col]),
            measure=measures,
            increasing={"marker": {"color": theme.COLORS["dark_teal"]}},
            decreasing={"marker": {"color": theme.COLORS["red"]}},
            totals={"marker": {"color": theme.COLORS["black"]}},
            connector={"line": {"color": theme.COLORS["border"], "width": 1}},
            hovertemplate=f"%{{x}}<br>{y_title}: %{{y:,.1f}}<extra></extra>",
        )
    )
    fig.update_layout(yaxis={"title": {"text": y_title}}, showlegend=False)
    return fig


def _build_variance(df: pd.DataFrame, category_col: str, value_col: str, favorable_col: str, y_title: str) -> go.Figure:
    running = 0.0
    bases, colors, texts = [], [], []
    for row in df.itertuples(index=False):
        v = getattr(row, value_col)
        favorable = getattr(row, favorable_col) if favorable_col in df.columns else v >= 0
        bases.append(running if v >= 0 else running + v)
        colors.append(theme.COLORS["dark_teal"] if favorable else theme.COLORS["red"])
        texts.append(f"{'+' if v >= 0 else ''}{v:,.1f}")
        running += v

    fig = go.Figure(
        go.Bar(
            x=list(df[category_col]),
            y=[abs(getattr(row, value_col)) for row in df.itertuples(index=False)],
            base=bases,
            marker={"color": colors},
            text=texts,
            textposition="outside",
            hovertemplate=(
                f"%{{x}}<br>Variance ({y_title}): %{{customdata:+.1f}}<extra></extra>"
            ),
            customdata=list(df[value_col]),
        )
    )
    fig.update_layout(
        yaxis={"title": {"text": f"Cumulative {y_title}"}},
        showlegend=False,
    )
    return fig


def build(
    df: pd.DataFrame,
    *,
    mode: str = "level",
    category_col: str = "category",
    value_col: str = "value",
    measure_col: str = "measure",
    favorable_col: str = "favorable",
    y_title: str = "$M",
) -> go.Figure:
    if mode == "variance":
        fig = _build_variance(df, category_col, value_col, favorable_col, y_title)
    else:
        fig = _build_level(df, category_col, value_col, measure_col, y_title)
    return theme.apply_theme(fig, "waterfall")


CHART = ChartSpec(
    id="waterfall",
    title="Waterfall / Bridge",
    family="bridge",
    chart_type="waterfall",
    build=build,
    sample=sample,
    interactions="level bridge and zero-based variance bridge (favorable/unfavorable colors)",
)
