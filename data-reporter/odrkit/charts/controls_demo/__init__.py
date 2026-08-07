"""controls_demo — interactive control surface: a native ``updatemenus``
dropdown to toggle between two metrics (cross-filter-style trace
visibility swap), plus a play/pause animation slider stepping through
frames. Expects a tidy long-format DataFrame: ``frame, category, count,
avg`` (column names configurable via cfg).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ... import theme
from .._base import ChartSpec


def sample() -> pd.DataFrame:
    rows = []
    counts = {"2026-Q1": [40, 30, 20, 10], "2026-Q2": [35, 34, 25, 12], "2026-Q3": [50, 28, 22, 15]}
    avgs = {"2026-Q1": [4.2, 3.1, 5.5, 2.0], "2026-Q2": [4.5, 3.4, 5.1, 2.4], "2026-Q3": [4.0, 3.6, 5.8, 2.1]}
    categories = ["Enterprise", "SMB", "Public Sector", "Partner"]
    for frame, c_vals in counts.items():
        a_vals = avgs[frame]
        for cat, c, a in zip(categories, c_vals, a_vals):
            rows.append({"frame": frame, "category": cat, "count": c, "avg": a})
    return pd.DataFrame(rows)


def build(
    df: pd.DataFrame,
    *,
    frame_col: str = "frame",
    category_col: str = "category",
    count_col: str = "count",
    avg_col: str = "avg",
    count_title: str = "Count",
    avg_title: str = "Avg",
) -> go.Figure:
    frames_list = list(dict.fromkeys(df[frame_col]))
    categories = list(dict.fromkeys(df[category_col]))

    def series(sub: pd.DataFrame, col: str) -> list[float]:
        s = sub.set_index(category_col)[col]
        return [float(s.get(c, 0.0)) for c in categories]

    first = df[df[frame_col] == frames_list[0]]
    trace_count = go.Bar(
        x=categories,
        y=series(first, count_col),
        name=count_title,
        marker={"color": theme.COLORS["cyan"]},
        visible=True,
        hovertemplate=f"%{{x}}<br>{count_title}: %{{y:,.1f}}<extra></extra>",
    )
    trace_avg = go.Bar(
        x=categories,
        y=series(first, avg_col),
        name=avg_title,
        marker={"color": theme.COLORS["dark_teal"]},
        visible=False,
        hovertemplate=f"%{{x}}<br>{avg_title}: %{{y:,.1f}}<extra></extra>",
    )
    fig = go.Figure(data=[trace_count, trace_avg])

    frames = []
    for fr in frames_list:
        sub = df[df[frame_col] == fr]
        frames.append(
            go.Frame(
                name=str(fr),
                data=[go.Bar(y=series(sub, count_col)), go.Bar(y=series(sub, avg_col))],
                traces=[0, 1],
            )
        )
    fig.frames = frames

    slider_steps = [
        {
            "method": "animate",
            "label": str(fr),
            "args": [
                [str(fr)],
                {"mode": "immediate", "frame": {"duration": 400, "redraw": True}, "transition": {"duration": 200}},
            ],
        }
        for fr in frames_list
    ]

    fig.update_layout(
        margin={"t": 110},
        updatemenus=[
            {
                "type": "dropdown",
                "x": 1.0,
                "y": 1.28,
                "xanchor": "right",
                "showactive": True,
                "buttons": [
                    {"label": count_title, "method": "update", "args": [{"visible": [True, False]}]},
                    {"label": avg_title, "method": "update", "args": [{"visible": [False, True]}]},
                ],
            },
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "y": 1.28,
                "xanchor": "left",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [None, {"fromcurrent": True, "frame": {"duration": 500, "redraw": True}, "transition": {"duration": 200}}],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}}],
                    },
                ],
            },
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.12,
                "y": 1.22,
                "len": 0.82,
                "currentvalue": {"prefix": "Period: "},
                "steps": slider_steps,
            }
        ],
        yaxis={"title": {"text": count_title}},
    )
    return theme.apply_theme(fig, "bar")


CHART = ChartSpec(
    id="controls_demo",
    title="Interactive Controls Demo",
    family="interactive",
    chart_type="bar",
    build=build,
    sample=sample,
    interactions="native updatemenus dropdown, cross-filter + animation play/pause slider",
)
