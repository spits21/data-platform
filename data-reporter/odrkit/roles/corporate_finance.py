"""odrkit.roles.corporate_finance — FP&A quarterly business review for the CFO.

The reference role: single source of truth for the deck AND the custom doc
(and, in ``quarto/corporate_finance/corporate_finance.qmd``, the Quarto
doc) — all three read the SAME period-parameterized shapers below and drive
the SAME library chart builders, so they can never drift.

No metric is invented: every KPI and every narrative sentence in
``build_narrative`` is computed directly from ``data/corporate_finance/``.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from .. import data
from ..charts import REGISTRY as _LIB
from ..report_spec import KPI, ReportSpec, SectionSpec

ROLE = "corporate_finance"
DEFAULT_PERIOD = "2026-Q1"

TRAILING_QUARTERS = 8


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def available_periods() -> list[str]:
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    return sorted(pnl["period"].unique())


def _trailing(df: pd.DataFrame, period: str, n: int, period_col: str = "period") -> pd.DataFrame:
    periods = sorted(df[period_col].unique())
    if period not in periods:
        raise ValueError(
            f"unknown period {period!r} for role {ROLE!r}; available: {periods}"
        )
    pos = periods.index(period)
    window = set(periods[max(0, pos - n + 1) : pos + 1])
    return df[df[period_col].isin(window)].copy()


def _delta_pct(cur: float, prior: float | None) -> str:
    if prior is None or prior == 0:
        return ""
    delta = (cur - prior) / abs(prior) * 100
    return f"{'+' if delta >= 0 else ''}{delta:.1f}% QoQ"


def _delta_ppt(cur: float, prior: float | None) -> str:
    if prior is None:
        return ""
    delta = cur - prior
    return f"{'+' if delta >= 0 else ''}{delta:.1f}ppt QoQ"


# ---------------------------------------------------------------------------
# Data shapers — each returns a DataFrame in the column shape the target
# LIBRARY chart's build() already expects (see odrkit/charts/<id>/).
# ---------------------------------------------------------------------------

def shape_kpis(period: str) -> list[KPI]:
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    periods = sorted(pnl["period"].unique())
    pos = periods.index(period)
    cur = pnl[pnl["period"] == period].iloc[0]
    prior = pnl[pnl["period"] == periods[pos - 1]].iloc[0] if pos > 0 else None

    return [
        KPI(
            "Revenue ($M)",
            f"{cur['revenue']:,.1f}",
            _delta_pct(cur["revenue"], prior["revenue"] if prior is not None else None),
        ),
        KPI(
            "EBITDA ($M)",
            f"{cur['ebitda']:,.1f}",
            _delta_pct(cur["ebitda"], prior["ebitda"] if prior is not None else None),
        ),
        KPI(
            "EBITDA Margin",
            f"{cur['ebitda_margin_pct']:.1f}%",
            _delta_ppt(
                cur["ebitda_margin_pct"],
                prior["ebitda_margin_pct"] if prior is not None else None,
            ),
        ),
        KPI(
            "Gross Margin",
            f"{cur['gross_margin_pct']:.1f}%",
            _delta_ppt(
                cur["gross_margin_pct"],
                prior["gross_margin_pct"] if prior is not None else None,
            ),
        ),
    ]


def shape_revenue_trend(period: str) -> pd.DataFrame:
    """-> timeseries_multi shape: date, series, value."""
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    sub = _trailing(pnl, period, TRAILING_QUARTERS).sort_values("quarter_start")
    rows = []
    for _, r in sub.iterrows():
        rows.append({"date": r["quarter_start"], "series": "Revenue", "value": r["revenue"]})
        rows.append({"date": r["quarter_start"], "series": "EBITDA", "value": r["ebitda"]})
    return pd.DataFrame(rows)


def shape_opex_breakdown(period: str) -> pd.DataFrame:
    """-> grouped_stacked_bar shape: category (quarter), group (opex category), value."""
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    opex = data.load_cached(ROLE, "opex_breakdown")
    window = set(_trailing(pnl, period, TRAILING_QUARTERS)["period"])
    sub = opex[opex["period"].isin(window)]
    return sub.rename(columns={"period": "category", "category": "group", "amount": "value"})[
        ["category", "group", "value"]
    ]


def shape_segment_mix(period: str) -> pd.DataFrame:
    """-> treemap shape: segment, subsegment, value."""
    seg = data.load_cached(ROLE, "segment_revenue")
    sub = seg[seg["period"] == period]
    return sub.rename(columns={"revenue": "value"})[["segment", "subsegment", "value"]]


def shape_budget_bridge(period: str) -> pd.DataFrame:
    """-> waterfall (variance mode) shape: category, value, favorable."""
    bva = data.load_cached(ROLE, "budget_vs_actual")
    sub = bva[bva["period"] == period]
    return sub.rename(columns={"line_item": "category", "variance": "value"})[
        ["category", "value", "favorable"]
    ]


def shape_margin_heatmap(period: str) -> pd.DataFrame:
    """-> heatmap shape: row (margin metric), col (quarter), value (%)."""
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    sub = _trailing(pnl, period, 12).sort_values("quarter_start")
    rows = []
    for _, r in sub.iterrows():
        rows.append({"row": "Gross Margin %", "col": r["period"], "value": r["gross_margin_pct"]})
        rows.append({"row": "EBITDA Margin %", "col": r["period"], "value": r["ebitda_margin_pct"]})
    return pd.DataFrame(rows)


def build_narrative(period: str) -> str:
    """A short narrative paragraph computed entirely from data — every
    number and quarter reference below is read out of the role's datasets,
    never invented."""
    pnl = data.load_cached(ROLE, "quarterly_pnl")
    bva = data.load_cached(ROLE, "budget_vs_actual")

    sub = _trailing(pnl, period, TRAILING_QUARTERS).sort_values("quarter_start").copy()
    sub["revenue_qoq"] = sub["revenue"].pct_change() * 100
    growth_rows = sub.dropna(subset=["revenue_qoq"])
    best = growth_rows.loc[growth_rows["revenue_qoq"].idxmax()]

    ebitda_row = bva[(bva["period"] == period) & (bva["line_item"] == "EBITDA")].iloc[0]
    verb = "beat" if ebitda_row["favorable"] else "missed"

    revenue_row = bva[(bva["period"] == period) & (bva["line_item"] == "Revenue")].iloc[0]
    rev_verb = "beat" if revenue_row["favorable"] else "missed"

    return (
        f"Over the trailing {TRAILING_QUARTERS} quarters ending **{period}**, revenue growth "
        f"peaked in **{best['period']}** at {best['revenue_qoq']:+.1f}% QoQ. "
        f"In **{period}**, revenue {rev_verb} budget by "
        f"${abs(revenue_row['variance']):.1f}M and EBITDA {verb} budget by "
        f"${abs(ebitda_row['variance']):.1f}M."
    )


# ---------------------------------------------------------------------------
# Per-report registry: section id -> ChartSpec bound to real, period-filtered
# data. The library `build()` is reused UNMODIFIED; only `sample()` (and the
# id, so it can be looked up by section id) is rebound.
# ---------------------------------------------------------------------------

def build_registry(period: str) -> dict:
    return {
        "revenue_trend": replace(
            _LIB["timeseries_multi"], id="revenue_trend", sample=lambda: shape_revenue_trend(period)
        ),
        "opex_breakdown": replace(
            _LIB["grouped_stacked_bar"],
            id="opex_breakdown",
            sample=lambda: shape_opex_breakdown(period),
        ),
        "segment_mix": replace(
            _LIB["treemap"], id="segment_mix", sample=lambda: shape_segment_mix(period)
        ),
        "budget_bridge": replace(
            _LIB["waterfall"], id="budget_bridge", sample=lambda: shape_budget_bridge(period)
        ),
        "margin_heatmap": replace(
            _LIB["heatmap"], id="margin_heatmap", sample=lambda: shape_margin_heatmap(period)
        ),
    }


def build_report_spec(period: str) -> ReportSpec:
    return ReportSpec(
        title="Corporate Finance — Quarterly Business Review",
        eyebrow="FP&A",
        subtitle=f"Fiscal quarter {period} · trailing {TRAILING_QUARTERS}-quarter trend",
        id_badge=period,
        synthetic=True,
        sections=[
            SectionSpec(
                kind="section",
                id="exec_summary",
                title="Executive Summary",
                subtitle="Headline performance and budget variance",
                body_md=build_narrative(period),
            ),
            SectionSpec(
                kind="kpi_row",
                id="headline_kpis",
                title="Headline KPIs",
                eyebrow="FP&A",
                subtitle=f"As of {period}, vs. prior quarter",
                kpis=shape_kpis(period),
            ),
            SectionSpec(
                kind="chart",
                id="revenue_trend",
                title="Revenue & EBITDA Trend",
                eyebrow="Time Series",
                subtitle=f"Trailing {TRAILING_QUARTERS} quarters",
                cfg={"y_title": "$M", "metric_name": ""},
                show_code=True,
            ),
            SectionSpec(
                kind="chart",
                id="opex_breakdown",
                title="Operating Expense by Category",
                eyebrow="Cost Structure",
                subtitle=f"Trailing {TRAILING_QUARTERS} quarters, stacked by category",
                cfg={"mode": "stacked", "y_title": "$M"},
            ),
            SectionSpec(
                kind="chart",
                id="segment_mix",
                title="Revenue by Segment",
                eyebrow="Business Mix",
                subtitle=f"{period} revenue split, segment → subsegment",
                cfg={"value_title": "$M", "root_label": f"{period} Revenue"},
            ),
            SectionSpec(
                kind="chart",
                id="budget_bridge",
                title="Budget vs. Actual Bridge",
                eyebrow="Variance",
                subtitle=f"{period} favorable / unfavorable variance by line item",
                cfg={"mode": "variance", "y_title": "$M"},
                show_code=True,
            ),
            SectionSpec(
                kind="chart",
                id="margin_heatmap",
                title="Margin Trend",
                eyebrow="Profitability",
                subtitle="Gross margin and EBITDA margin by quarter",
                cfg={"colorscale": "odr", "value_title": "%"},
            ),
            SectionSpec(kind="disclaimer"),
        ],
    )
