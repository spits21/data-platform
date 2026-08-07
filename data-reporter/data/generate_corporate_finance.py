"""Generates the synthetic corporate_finance dataset (seed 20260709).

Run once from the repo root: ``uv run python data/generate_corporate_finance.py``

Writes four parquet files under ``data/corporate_finance/`` with an enforced
internal consistency spine:
    gross_profit = revenue - cogs
    ebitda       = gross_profit - opex_total
    sum(segment_revenue.revenue over a period) == quarterly_pnl.revenue
    sum(opex_breakdown.amount over a period)   == quarterly_pnl.opex_total

All figures are illustrative synthetic data — not real ODR figures.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260709
OUT_DIR = Path(__file__).resolve().parent / "corporate_finance"

QUARTERS = [
    f"{y}-Q{q}"
    for y in (2023, 2024, 2025, 2026)
    for q in (1, 2, 3, 4)
    if not (y == 2026 and q > 2)
]  # 2023-Q1 .. 2026-Q2 inclusive (14 quarters)

SEGMENTS = {
    "Enterprise": ["Software", "Services"],
    "SMB": ["Software", "Services"],
    "Public Sector": ["Software", "Services"],
}
OPEX_CATEGORIES = {
    "Salaries": 0.52,
    "R&D": 0.18,
    "Marketing": 0.14,
    "G&A": 0.11,
    "Other": 0.05,
}


def _quarter_start(period: str) -> pd.Timestamp:
    year, q = period.split("-Q")
    month = (int(q) - 1) * 3 + 1
    return pd.Timestamp(year=int(year), month=month, day=1)


def build_quarterly_pnl(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    revenue = 92.0  # $M, starting point
    for period in QUARTERS:
        growth = rng.normal(0.028, 0.012)  # ~2.8% QoQ average growth, noisy
        revenue = revenue * (1 + growth)
        cogs_ratio = rng.normal(0.42, 0.012)
        opex_ratio = rng.normal(0.335, 0.015)

        # Round the independent inputs FIRST, then derive gross_profit/ebitda
        # from the rounded values so the spine holds exactly, not just to
        # float precision.
        revenue_r = round(revenue, 2)
        cogs_r = round(revenue * cogs_ratio, 2)
        opex_total_r = round(revenue * opex_ratio, 2)
        gross_profit_r = round(revenue_r - cogs_r, 2)
        ebitda_r = round(gross_profit_r - opex_total_r, 2)
        rows.append(
            {
                "period": period,
                "quarter_start": _quarter_start(period),
                "revenue": revenue_r,
                "cogs": cogs_r,
                "gross_profit": gross_profit_r,
                "opex_total": opex_total_r,
                "ebitda": ebitda_r,
            }
        )
    df = pd.DataFrame(rows)
    df["gross_margin_pct"] = (df["gross_profit"] / df["revenue"] * 100).round(2)
    df["ebitda_margin_pct"] = (df["ebitda"] / df["revenue"] * 100).round(2)
    return df


def build_segment_revenue(pnl: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    # Slowly drifting weights per segment/subsegment, renormalized per period.
    base_weights = {
        ("Enterprise", "Software"): 0.34,
        ("Enterprise", "Services"): 0.14,
        ("SMB", "Software"): 0.22,
        ("SMB", "Services"): 0.09,
        ("Public Sector", "Software"): 0.15,
        ("Public Sector", "Services"): 0.06,
    }
    for _, row in pnl.iterrows():
        noise = {k: max(0.01, v + rng.normal(0, 0.01)) for k, v in base_weights.items()}
        total_weight = sum(noise.values())
        for (segment, subsegment), w in noise.items():
            rows.append(
                {
                    "period": row["period"],
                    "segment": segment,
                    "subsegment": subsegment,
                    "revenue": round(row["revenue"] * w / total_weight, 3),
                }
            )
    df = pd.DataFrame(rows)
    # Force exact reconciliation to quarterly_pnl.revenue per period (rounding drift).
    for period, sub in df.groupby("period"):
        target = pnl.loc[pnl["period"] == period, "revenue"].iloc[0]
        scale = target / sub["revenue"].sum()
        df.loc[sub.index, "revenue"] = (sub["revenue"] * scale).round(3)
    return df


def build_opex_breakdown(pnl: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for _, row in pnl.iterrows():
        noise = {
            cat: max(0.01, w + rng.normal(0, 0.01)) for cat, w in OPEX_CATEGORIES.items()
        }
        total_weight = sum(noise.values())
        for cat, w in noise.items():
            rows.append(
                {
                    "period": row["period"],
                    "category": cat,
                    "amount": round(row["opex_total"] * w / total_weight, 3),
                }
            )
    df = pd.DataFrame(rows)
    for period, sub in df.groupby("period"):
        target = pnl.loc[pnl["period"] == period, "opex_total"].iloc[0]
        scale = target / sub["amount"].sum()
        df.loc[sub.index, "amount"] = (sub["amount"] * scale).round(3)
    return df


def build_budget_vs_actual(pnl: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """One budget-vs-actual bridge row set per period, per top-line item.

    Budget is a smoothed plan set ~1 quarter ahead of actuals with a modest
    miss; favorable/unfavorable is business-logic (revenue/EBITDA beats are
    favorable, cost overruns are unfavorable), not sign-based.
    """
    rows = []
    for _, row in pnl.iterrows():
        revenue_actual = row["revenue"]
        cogs_actual = row["cogs"]
        opex_actual = row["opex_total"]
        ebitda_actual = row["ebitda"]

        revenue_budget = revenue_actual / (1 + rng.normal(0.012, 0.01))
        cogs_budget = cogs_actual / (1 + rng.normal(0.0, 0.012))
        opex_budget = opex_actual / (1 + rng.normal(-0.01, 0.012))
        ebitda_budget = revenue_budget - cogs_budget - opex_budget

        items = [
            ("Revenue", revenue_budget, revenue_actual, True),
            ("COGS", cogs_budget, cogs_actual, False),
            ("Opex", opex_budget, opex_actual, False),
        ]
        for line_item, budget, actual, higher_is_favorable in items:
            variance = actual - budget
            favorable = (variance >= 0) if higher_is_favorable else (variance <= 0)
            rows.append(
                {
                    "period": row["period"],
                    "line_item": line_item,
                    "budget": round(budget, 2),
                    "actual": round(actual, 2),
                    "variance": round(variance, 2),
                    "favorable": bool(favorable),
                }
            )
        rows.append(
            {
                "period": row["period"],
                "line_item": "EBITDA",
                "budget": round(ebitda_budget, 2),
                "actual": round(ebitda_actual, 2),
                "variance": round(ebitda_actual - ebitda_budget, 2),
                "favorable": bool(ebitda_actual - ebitda_budget >= 0),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pnl = build_quarterly_pnl(rng)
    segment_revenue = build_segment_revenue(pnl, rng)
    opex_breakdown = build_opex_breakdown(pnl, rng)
    budget_vs_actual = build_budget_vs_actual(pnl, rng)

    # Assert the consistency spine before writing anything.
    for period, sub in segment_revenue.groupby("period"):
        target = pnl.loc[pnl["period"] == period, "revenue"].iloc[0]
        assert abs(sub["revenue"].sum() - target) < 0.01, period
    for period, sub in opex_breakdown.groupby("period"):
        target = pnl.loc[pnl["period"] == period, "opex_total"].iloc[0]
        assert abs(sub["amount"].sum() - target) < 0.01, period
    assert ((pnl["revenue"] - pnl["cogs"] - pnl["gross_profit"]).abs() < 1e-6).all()
    assert ((pnl["gross_profit"] - pnl["opex_total"] - pnl["ebitda"]).abs() < 1e-6).all()

    pnl.to_parquet(OUT_DIR / "quarterly_pnl.parquet", index=False)
    segment_revenue.to_parquet(OUT_DIR / "segment_revenue.parquet", index=False)
    opex_breakdown.to_parquet(OUT_DIR / "opex_breakdown.parquet", index=False)
    budget_vs_actual.to_parquet(OUT_DIR / "budget_vs_actual.parquet", index=False)

    print(f"wrote {len(pnl)} quarters to {OUT_DIR}")
    print(pnl[["period", "revenue", "ebitda", "ebitda_margin_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
