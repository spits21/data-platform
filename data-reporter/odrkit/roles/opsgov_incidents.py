"""odrkit.roles.opsgov_incidents — Incident & Change Request quarterly review
for IT operations governance.

REAL DATA (see CLAUDE.md): unlike the four synthetic roles, this role reads
live from Postgres (``analytics.incidents_with_change_requests``) via
``odrkit.data.query_postgres_cached`` — there is no local file under
``data/opsgov_incidents/``. ``ReportSpec.synthetic`` is set to ``False`` so
reports do NOT carry the "illustrative synthetic data" marker.

No metric is invented: every KPI, chart, and narrative sentence below is
computed directly from the table. Several charts are explicitly scoped to
what the schema actually supports — e.g. the "capacity" chart uses weekly
*opened* volume (a real time series) rather than a fabricated historical
backlog curve, since the table only carries current `state`, not a
state-change history.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import pandas as pd

from .. import data
from ..charts import REGISTRY as _LIB
from ..dashboard_spec import DashboardKPI, DashboardSpec, FilterSpec, GroupSpec, PanelSpec, TabSpec
from ..report_spec import KPI, ReportSpec, SectionSpec

ROLE = "opsgov_incidents"
DEFAULT_PERIOD = "2026-Q1"  # the only quarter present in the source table as of authoring

TABLE = "analytics.incidents_with_change_requests"


@lru_cache(maxsize=1)
def _dsn() -> str:
    """Postgres DSN for this role, built from env vars (see .env.example) —
    never hardcoded. Cached since it's read on every shaper call; the env
    doesn't change mid-process."""
    return data.postgres_dsn_from_env("ODR_PG")


PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
OPEN_STATES = ("New", "In Progress", "On Hold")


# ---------------------------------------------------------------------------
# Raw load + normalization (cached process-wide via query_postgres_cached).
# ---------------------------------------------------------------------------

def _to_period(ts: pd.Timestamp) -> str:
    return f"{ts.year}-Q{(ts.month - 1) // 3 + 1}"


def _raw(period: str | None = None) -> pd.DataFrame:
    df = data.query_postgres_cached(_dsn(), f"SELECT * FROM pg.{TABLE}").copy()

    # Source data has inconsistent casing on impact/urgency ("Medium" vs
    # "medium") — normalize once here so every downstream shaper agrees.
    df["priority"] = df["priority"].str.replace(r"^\d+\s*-\s*", "", regex=True).str.strip()
    df["impact"] = df["impact"].str.strip().str.title()
    df["urgency"] = df["urgency"].str.strip().str.title()

    df["has_change"] = df["change_request_number"].notna()
    df["period"] = df["created_at"].apply(_to_period)
    df["resolution_hours"] = (df["updated_at"] - df["created_at"]).dt.total_seconds() / 3600.0
    df["is_resolved"] = df["state"].isin(["Resolved", "Closed"])
    df["week_start"] = df["created_at"].dt.to_period("W").apply(lambda p: p.start_time)
    df["resolved_week_start"] = df["updated_at"].dt.to_period("W").apply(lambda p: p.start_time)

    if period is not None:
        df = df[df["period"] == period]
    return df


def available_periods() -> list[str]:
    df = data.query_postgres_cached(_dsn(), f"SELECT created_at FROM pg.{TABLE}")
    return sorted({_to_period(ts) for ts in df["created_at"]})


# ---------------------------------------------------------------------------
# Data shapers — each returns a DataFrame (or KPI list) in the column shape
# the target LIBRARY chart's build() already expects.
# ---------------------------------------------------------------------------

def shape_kpis(period: str) -> list[KPI]:
    raw = _raw(period)
    total = len(raw)
    critical = int((raw["priority"] == "Critical").sum())
    resolved = raw[raw["is_resolved"]]

    return [
        KPI("Total Incidents", f"{total:,}", f"{critical} Critical"),
        KPI(
            "Change-Caused Rate",
            f"{raw['has_change'].mean() * 100:.1f}%",
            f"{int(raw['has_change'].sum())} of {total} incidents",
        ),
        KPI(
            "Median Resolution Time",
            f"{resolved['resolution_hours'].median():,.0f} hrs" if not resolved.empty else "N/A",
            f"{len(resolved):,} resolved/closed",
        ),
        KPI(
            "Open Backlog",
            f"{int((~raw['is_resolved']).sum()):,}",
            "New + In Progress + On Hold",
        ),
    ]


def shape_volume_trend(period: str) -> pd.DataFrame:
    """-> timeseries_multi shape: date, series, value (weekly opened vs resolved)."""
    raw = _raw(period)
    opened = raw.groupby("week_start").size()
    resolved = raw[raw["is_resolved"]].groupby("resolved_week_start").size()
    weeks = sorted(set(opened.index) | set(resolved.index))

    rows = []
    for w in weeks:
        rows.append({"date": w, "series": "Opened", "value": int(opened.get(w, 0))})
        rows.append({"date": w, "series": "Resolved", "value": int(resolved.get(w, 0))})
    return pd.DataFrame(rows)


def shape_backlog_bridge(period: str) -> pd.DataFrame:
    """-> waterfall (level mode) shape: category, value, measure.

    Ties out by construction: Opened - Resolved - Closed == Open Backlog.
    """
    raw = _raw(period)
    total_opened = len(raw)
    resolved_count = int((raw["state"] == "Resolved").sum())
    closed_count = int((raw["state"] == "Closed").sum())
    still_open = total_opened - resolved_count - closed_count

    return pd.DataFrame(
        {
            "category": ["Opened", "Resolved", "Closed", "Open Backlog"],
            "value": [total_opened, -resolved_count, -closed_count, still_open],
            "measure": ["relative", "relative", "relative", "total"],
        }
    )


def shape_lifecycle_funnel(period: str) -> pd.DataFrame:
    """-> funnel shape: stage, value.

    A snapshot-based "how far along" funnel from current `state` (the table
    has no historical state-transition log, so this reads current position,
    not a true stage-by-stage conversion history).
    """
    raw = _raw(period)
    stage_rank = {"New": 0, "On Hold": 1, "In Progress": 1, "Resolved": 2, "Closed": 3}
    stage = raw["state"].map(stage_rank)

    labels = ["Opened", "Actively Worked (In Progress+)", "Resolved+", "Closed"]
    values = [int((stage >= k).sum()) for k in range(4)]
    return pd.DataFrame({"stage": labels, "value": values})


def shape_priority_state_sunburst(period: str) -> pd.DataFrame:
    """-> sunburst shape (via cfg path_cols=('priority','state')): priority, state, value."""
    raw = _raw(period)
    return raw.groupby(["priority", "state"]).size().reset_index(name="value")


def shape_weekday_priority_heatmap(period: str) -> pd.DataFrame:
    """-> heatmap shape (via cfg row_col='weekday', col_col='priority'): weekday, priority, value."""
    raw = _raw(period).copy()
    raw["weekday"] = pd.Categorical(
        raw["created_at"].dt.day_name(), categories=WEEKDAY_ORDER, ordered=True
    )
    raw["priority"] = pd.Categorical(raw["priority"], categories=PRIORITY_ORDER, ordered=True)
    grp = raw.groupby(["weekday", "priority"], observed=False).size().reset_index(name="value")
    # Keep weekday/priority as ORDERED Categorical — heatmap.build() pivots
    # on these columns and pandas preserves Categorical order through
    # pivot (plain str columns would sort alphabetically instead).
    return grp


def shape_resolution_by_priority(period: str) -> pd.DataFrame:
    """-> ohlc_box (mode='box', cfg category_col='priority') shape: priority, value."""
    raw = _raw(period)
    resolved = raw[raw["is_resolved"]].copy()
    resolved["priority"] = pd.Categorical(resolved["priority"], categories=PRIORITY_ORDER, ordered=True)
    resolved = resolved.sort_values("priority")
    return resolved.rename(columns={"resolution_hours": "value"})[["priority", "value"]]


def shape_resolution_by_impact(period: str) -> pd.DataFrame:
    """-> distribution_violin (cfg category_col='impact') shape: impact, value."""
    raw = _raw(period)
    resolved = raw[raw["is_resolved"]]
    return resolved.rename(columns={"resolution_hours": "value"})[["impact", "value"]]


def shape_resolution_change_caused(period: str) -> pd.DataFrame:
    """-> ridgeline (cfg category_col='group') shape: group, value.

    Compares resolution-time distribution for incidents caused by a change
    vs. incidents with no linked change.
    """
    raw = _raw(period)
    resolved = raw[raw["is_resolved"]].copy()
    resolved["group"] = resolved["has_change"].map({True: "Change-Caused", False: "Not Change-Caused"})
    return resolved.rename(columns={"resolution_hours": "value"})[["group", "value"]]


def _outcome_bucket(state: str) -> str:
    return "Open" if state in OPEN_STATES else state


def shape_priority_change_outcome_sankey(period: str) -> pd.DataFrame:
    """-> sankey shape: source, target, value (Priority -> Change-Caused? -> Outcome)."""
    raw = _raw(period).copy()
    raw["change_flag"] = raw["has_change"].map({True: "Change-Caused", False: "Not Change-Caused"})
    raw["outcome"] = raw["state"].map(_outcome_bucket)

    stage1 = raw.groupby(["priority", "change_flag"]).size().reset_index(name="value")
    stage1.columns = ["source", "target", "value"]

    stage2 = raw.groupby(["change_flag", "outcome"]).size().reset_index(name="value")
    stage2.columns = ["source", "target", "value"]

    return pd.concat([stage1, stage2], ignore_index=True)


def shape_ci_risk_scatter(period: str, top_n: int = 20) -> pd.DataFrame:
    """-> scatter_bubble shape: name, x (incident count), y (avg resolution
    hrs among its resolved incidents), size (critical count), color (%
    change-caused). Limited to the top-N CIs by incident count that have at
    least one resolved incident (an avg resolution time needs one)."""
    raw = _raw(period)
    counts = raw.groupby("ci_id").size().rename("incident_count")
    critical = raw.groupby("ci_id").apply(
        lambda g: int((g["priority"] == "Critical").sum()), include_groups=False
    ).rename("critical_count")
    change_share = raw.groupby("ci_id")["has_change"].mean().rename("change_share")
    avg_res = raw[raw["is_resolved"]].groupby("ci_id")["resolution_hours"].mean().rename("avg_resolution_hours")

    agg = pd.concat([counts, critical, change_share, avg_res], axis=1).dropna(subset=["avg_resolution_hours"])
    agg = agg.sort_values("incident_count", ascending=False).head(top_n).reset_index()
    agg["name"] = "CI " + agg["ci_id"].str[:8]

    return pd.DataFrame(
        {
            "name": agg["name"],
            "x": agg["incident_count"],
            "y": agg["avg_resolution_hours"],
            "size": agg["critical_count"].clip(lower=1),
            "color": agg["change_share"] * 100,
        }
    )


def shape_weekly_capacity(period: str) -> pd.DataFrame:
    """-> capacity_lines shape: date, value. Weekly *opened* volume against a
    data-derived capacity threshold (mean + 1 std of the period's own weekly
    volume) — not a fabricated historical backlog curve, since the table has
    no state-change history to reconstruct one from."""
    raw = _raw(period)
    weekly = raw.groupby("week_start").size().sort_index()
    return pd.DataFrame({"date": weekly.index, "value": weekly.values})


def weekly_capacity_threshold(period: str) -> float:
    weekly = _raw(period).groupby("week_start").size()
    return float(weekly.mean() + weekly.std(ddof=0))


def shape_compliance_indicators(period: str) -> pd.DataFrame:
    """-> kpi_indicators shape: label, value, suffix (no prior — only one
    quarter of history exists in the source table)."""
    raw = _raw(period)
    resolved = raw[raw["is_resolved"]]
    return pd.DataFrame(
        {
            "label": ["Resolved or Closed (%)", "Change-Caused (%)", "Avg Resolution (hrs)"],
            "value": [
                raw["is_resolved"].mean() * 100,
                raw["has_change"].mean() * 100,
                resolved["resolution_hours"].mean() if not resolved.empty else 0.0,
            ],
            "prior": [None, None, None],
            "suffix": ["", "", ""],
        }
    )


def shape_controls_demo(period: str) -> pd.DataFrame:
    """-> controls_demo shape: frame (week), category (priority), count, avg
    resolution hours — animated weekly, toggle Count vs. Avg via dropdown."""
    raw = _raw(period).copy()
    raw["priority"] = pd.Categorical(raw["priority"], categories=PRIORITY_ORDER, ordered=True)
    weeks = sorted(raw["week_start"].unique())

    rows = []
    for w in weeks:
        wk = raw[raw["week_start"] == w]
        for pr in PRIORITY_ORDER:
            sub = wk[wk["priority"] == pr]
            resolved = sub[sub["is_resolved"]]
            rows.append(
                {
                    "frame": w.strftime("%b %d"),
                    "category": pr,
                    "count": len(sub),
                    "avg": resolved["resolution_hours"].mean() if not resolved.empty else 0.0,
                }
            )
    return pd.DataFrame(rows)


def shape_dashboard_rows(period: str) -> pd.DataFrame:
    """Row-level, JSON-embeddable dataset for the interactive dashboard's
    client-side filtering (see odrkit/dashboard.py, dashboard.html.j2). Not
    a chart shape — one row per incident, columns named for direct use as
    filter fields (``created_at``, ``priority``, ``impact``, ...) and as the
    source the dashboard's JS reducers re-aggregate from, mirroring the
    shape_* functions above column-for-column so the two never drift.

    ``resolution_hours`` is null for unresolved incidents (the raw
    ``updated_at - created_at`` delta is not a resolution time until the
    incident is actually resolved/closed) so client-side aggregations don't
    need to re-derive ``is_resolved`` gating themselves.
    """
    raw = _raw(period).copy()
    resolution_hours = raw["resolution_hours"].where(raw["is_resolved"])
    return pd.DataFrame(
        {
            "created_at": raw["created_at"].dt.strftime("%Y-%m-%d"),
            "week_start": raw["week_start"].dt.strftime("%Y-%m-%d"),
            "resolved_week_start": raw["resolved_week_start"].dt.strftime("%Y-%m-%d"),
            "weekday": raw["created_at"].dt.day_name(),
            "priority": raw["priority"].astype(str),
            "impact": raw["impact"].astype(str),
            "state": raw["state"].astype(str),
            "has_change": raw["has_change"].astype(bool),
            "resolution_hours": resolution_hours.astype(float),
            "is_resolved": raw["is_resolved"].astype(bool),
            "ci_id": raw["ci_id"].astype(str),
        }
    )


def build_narrative(period: str) -> str:
    raw = _raw(period)
    total = len(raw)
    critical_share = (raw["priority"] == "Critical").mean() * 100
    change_rate = raw["has_change"].mean() * 100

    busiest_weekday = raw["created_at"].dt.day_name().value_counts().idxmax()

    resolved = raw[raw["is_resolved"]]
    by_priority = resolved.groupby("priority")["resolution_hours"].median()
    slowest_priority = by_priority.idxmax() if not by_priority.empty else "N/A"
    slowest_hours = by_priority.max() if not by_priority.empty else float("nan")

    top_ci = raw["ci_id"].value_counts().idxmax()
    top_ci_count = raw["ci_id"].value_counts().max()

    return (
        f"**{total}** incidents were logged in **{period}**, {critical_share:.1f}% of them Critical "
        f"priority. **{change_rate:.1f}%** were linked to a change request. Incident creation peaked "
        f"on **{busiest_weekday}s**. Among resolved/closed incidents, **{slowest_priority}**-priority "
        f"incidents took the longest to resolve at a median of **{slowest_hours:,.0f} hours**. "
        f"Configuration item **{top_ci[:8]}** generated the most incidents in the period "
        f"(**{top_ci_count}**)."
    )


# ---------------------------------------------------------------------------
# Per-report registry: section id -> ChartSpec bound to real, period-filtered
# data. The library `build()` is reused UNMODIFIED; only `sample()` (and the
# id, so it can be looked up by section id) is rebound.
# ---------------------------------------------------------------------------

def build_registry(period: str) -> dict:
    return {
        "volume_trend": replace(
            _LIB["timeseries_multi"], id="volume_trend", sample=lambda: shape_volume_trend(period)
        ),
        "backlog_bridge": replace(
            _LIB["waterfall"], id="backlog_bridge", sample=lambda: shape_backlog_bridge(period)
        ),
        "lifecycle_funnel": replace(
            _LIB["funnel"], id="lifecycle_funnel", sample=lambda: shape_lifecycle_funnel(period)
        ),
        "priority_state_sunburst": replace(
            _LIB["sunburst"],
            id="priority_state_sunburst",
            sample=lambda: shape_priority_state_sunburst(period),
        ),
        "weekday_priority_heatmap": replace(
            _LIB["heatmap"],
            id="weekday_priority_heatmap",
            sample=lambda: shape_weekday_priority_heatmap(period),
        ),
        "resolution_by_priority": replace(
            _LIB["ohlc_box"], id="resolution_by_priority", sample=lambda: shape_resolution_by_priority(period)
        ),
        "resolution_by_impact": replace(
            _LIB["distribution_violin"],
            id="resolution_by_impact",
            sample=lambda: shape_resolution_by_impact(period),
        ),
        "resolution_change_caused": replace(
            _LIB["ridgeline"],
            id="resolution_change_caused",
            sample=lambda: shape_resolution_change_caused(period),
        ),
        "priority_change_outcome_sankey": replace(
            _LIB["sankey"],
            id="priority_change_outcome_sankey",
            sample=lambda: shape_priority_change_outcome_sankey(period),
        ),
        "ci_risk_scatter": replace(
            _LIB["scatter_bubble"], id="ci_risk_scatter", sample=lambda: shape_ci_risk_scatter(period)
        ),
        "weekly_capacity": replace(
            _LIB["capacity_lines"], id="weekly_capacity", sample=lambda: shape_weekly_capacity(period)
        ),
        "compliance_indicators": replace(
            _LIB["kpi_indicators"],
            id="compliance_indicators",
            sample=lambda: shape_compliance_indicators(period),
        ),
        "controls_demo": replace(
            _LIB["controls_demo"], id="controls_demo", sample=lambda: shape_controls_demo(period)
        ),
    }


def build_report_spec(period: str) -> ReportSpec:
    return ReportSpec(
        title="Incidents & Change Requests — Quarterly Governance Review",
        eyebrow="ITSM / OpsGov",
        subtitle=f"Fiscal quarter {period} · sourced live from Postgres",
        id_badge=period,
        synthetic=False,
        sections=[
            SectionSpec(
                kind="section",
                id="exec_summary",
                title="Executive Summary",
                subtitle="Headline incident and change-request activity",
                body_md=build_narrative(period),
            ),
            SectionSpec(
                kind="kpi_row",
                id="headline_kpis",
                title="Headline KPIs",
                eyebrow="ITSM / OpsGov",
                subtitle=f"As of {period}",
                kpis=shape_kpis(period),
            ),
            SectionSpec(
                kind="chart",
                id="volume_trend",
                title="Weekly Incident Volume",
                eyebrow="Time Series",
                subtitle="Opened vs. resolved, by week",
                cfg={"y_title": "Incidents", "metric_name": ""},
                show_code=True,
            ),
            SectionSpec(
                kind="chart",
                id="backlog_bridge",
                title="Backlog Bridge",
                eyebrow="Flow",
                subtitle=f"{period}: opened → resolved/closed → ending open backlog",
                cfg={"mode": "level", "y_title": "Incidents"},
                show_code=True,
            ),
            SectionSpec(
                kind="chart",
                id="lifecycle_funnel",
                title="Incident Lifecycle Funnel",
                eyebrow="Pipeline",
                subtitle="Snapshot of how far incidents have progressed (current state, not stage history)",
                cfg={"value_title": "Incidents"},
            ),
            SectionSpec(
                kind="chart",
                id="priority_state_sunburst",
                title="Incidents by Priority → State",
                eyebrow="Hierarchy",
                subtitle="Click to drill from priority into state",
                cfg={"path_cols": ("priority", "state"), "value_col": "value", "root_label": "All Incidents", "value_title": "Incidents"},
            ),
            SectionSpec(
                kind="chart",
                id="weekday_priority_heatmap",
                title="Incident Volume by Weekday × Priority",
                eyebrow="Matrix",
                subtitle="Where critical incidents cluster during the week",
                cfg={"row_col": "weekday", "col_col": "priority", "value_col": "value", "colorscale": "turbo", "value_title": "Incidents"},
            ),
            SectionSpec(
                kind="chart",
                id="resolution_by_priority",
                title="Resolution Time by Priority",
                eyebrow="Distribution",
                subtitle="Hours to resolve, resolved/closed incidents only",
                cfg={"mode": "box", "category_col": "priority", "y_title": "Hours"},
            ),
            SectionSpec(
                kind="chart",
                id="resolution_by_impact",
                title="Resolution Time by Business Impact",
                eyebrow="Distribution",
                subtitle="Hours to resolve, split by reported impact",
                cfg={"category_col": "impact", "y_title": "Hours"},
            ),
            SectionSpec(
                kind="chart",
                id="resolution_change_caused",
                title="Resolution Time: Change-Caused vs. Not",
                eyebrow="Distribution",
                subtitle="Does a linked change request predict a slower resolution?",
                cfg={"category_col": "group", "x_title": "Hours to Resolve"},
                show_code=True,
            ),
            SectionSpec(
                kind="chart",
                id="priority_change_outcome_sankey",
                title="Priority → Change-Caused → Outcome",
                eyebrow="Flow",
                subtitle="How incidents at each priority flow to resolution",
                cfg={"value_title": "Incidents"},
            ),
            SectionSpec(
                kind="chart",
                id="ci_risk_scatter",
                title="Configuration Item Risk Map",
                eyebrow="Scatter",
                subtitle="Top 20 CIs by incident count — size = critical incidents, color = % change-caused",
                cfg={
                    "x_title": "Incident Count",
                    "y_title": "Avg Resolution (hrs)",
                    "size_title": "Critical Incidents",
                    "color_title": "% Change-Caused",
                },
            ),
            SectionSpec(
                kind="chart",
                id="weekly_capacity",
                title="Weekly Volume vs. Capacity Threshold",
                eyebrow="Capacity",
                subtitle="Threshold = mean + 1 std of the period's own weekly volume",
                cfg={"threshold": weekly_capacity_threshold(period), "y_title": "Incidents", "series_name": "Opened"},
            ),
            SectionSpec(
                kind="chart",
                id="compliance_indicators",
                title="Compliance Snapshot",
                eyebrow="Indicators",
                subtitle=f"{period} at a glance",
                cfg={"number_format": ".1f"},
            ),
            SectionSpec(
                kind="chart",
                id="controls_demo",
                title="Explore: Weekly Volume by Priority",
                eyebrow="Interactive",
                subtitle="Dropdown toggles Count vs. Avg Resolution Hours; play the weekly animation",
                cfg={"count_title": "Count", "avg_title": "Avg Resolution (hrs)"},
            ),
            SectionSpec(kind="disclaimer"),
        ],
    )


# ---------------------------------------------------------------------------
# Dashboard: grouped/tabbed front end with live client-side filtering.
# Initial panel figures reuse the SAME per-report registry as the deck/doc
# (build_registry above) — only the front end differs. Filters + the
# recompute names below are paired 1:1 with the RECOMPUTE / KPI_RECOMPUTE
# JS reducers in odrkit/templates/dashboard.html.j2 (see the comment above
# each JS reducer for which shape_* function it ports).
# ---------------------------------------------------------------------------

DASHBOARD_FILTERS = [
    FilterSpec(id="date", label="Created Date", field="created_at", kind="date_range"),
    FilterSpec(id="priority", label="Priority", field="priority", kind="multiselect", options=PRIORITY_ORDER),
    FilterSpec(id="impact", label="Impact", field="impact", kind="multiselect"),
    FilterSpec(
        id="change",
        label="Change Request",
        field="has_change",
        kind="select",
        options=["all", "true", "false"],
        option_labels={"all": "All", "true": "Change-Caused", "false": "Not Change-Caused"},
    ),
]


def _dashboard_kpis(period: str) -> list[DashboardKPI]:
    ids = ["total_incidents", "change_caused_rate", "median_resolution", "open_backlog"]
    return [DashboardKPI(id=i, label=k.label, value=k.value, sub=k.sub) for i, k in zip(ids, shape_kpis(period))]


def build_dashboard_spec(period: str) -> DashboardSpec:
    return DashboardSpec(
        title="Incidents & Change Requests — Operations Dashboard",
        eyebrow="ITSM / OpsGov",
        subtitle=f"Fiscal quarter {period} · sourced live from Postgres · filter to explore",
        id_badge=period,
        synthetic=False,
        filters=DASHBOARD_FILTERS,
        tabs=[
            TabSpec(
                id="overview",
                label="Overview",
                groups=[
                    GroupSpec(
                        id="headline_kpis",
                        kind="kpi_row",
                        kpis=_dashboard_kpis(period),
                        kpi_recompute="headline_kpis",
                    ),
                    GroupSpec(
                        id="volume_flow",
                        title="Volume & Flow",
                        columns=2,
                        panels=[
                            PanelSpec(
                                id="volume_trend",
                                chart_id="volume_trend",
                                title="Weekly Incident Volume",
                                eyebrow="Time Series",
                                subtitle="Opened vs. resolved, by week",
                                cfg={"y_title": "Incidents", "metric_name": ""},
                                recompute="volume_trend",
                            ),
                            PanelSpec(
                                id="lifecycle_funnel",
                                chart_id="lifecycle_funnel",
                                title="Incident Lifecycle Funnel",
                                eyebrow="Pipeline",
                                subtitle="Snapshot of how far incidents have progressed",
                                cfg={"value_title": "Incidents"},
                                recompute="lifecycle_funnel",
                            ),
                        ],
                    ),
                    GroupSpec(
                        id="backlog",
                        title="Backlog",
                        columns=1,
                        panels=[
                            PanelSpec(
                                id="backlog_bridge",
                                chart_id="backlog_bridge",
                                title="Backlog Bridge",
                                eyebrow="Flow",
                                subtitle="Opened → resolved/closed → ending open backlog",
                                cfg={"mode": "level", "y_title": "Incidents"},
                                recompute="backlog_bridge",
                            ),
                        ],
                    ),
                ],
            ),
            TabSpec(
                id="priority_risk",
                label="Priority & Risk",
                groups=[
                    GroupSpec(
                        id="priority_matrix",
                        title="Where Risk Concentrates",
                        columns=2,
                        panels=[
                            PanelSpec(
                                id="weekday_priority_heatmap",
                                chart_id="weekday_priority_heatmap",
                                title="Incident Volume by Weekday × Priority",
                                eyebrow="Matrix",
                                subtitle="Where critical incidents cluster during the week",
                                cfg={
                                    "row_col": "weekday", "col_col": "priority", "value_col": "value",
                                    "colorscale": "turbo", "value_title": "Incidents",
                                },
                                recompute="weekday_priority_heatmap",
                            ),
                            PanelSpec(
                                id="resolution_by_priority",
                                chart_id="resolution_by_priority",
                                title="Resolution Time by Priority",
                                eyebrow="Distribution",
                                subtitle="Hours to resolve, resolved/closed incidents only",
                                cfg={"mode": "box", "category_col": "priority", "y_title": "Hours"},
                                recompute="resolution_by_priority",
                            ),
                        ],
                    ),
                    GroupSpec(
                        id="ci_risk",
                        title="Configuration Item Risk",
                        columns=1,
                        panels=[
                            PanelSpec(
                                id="ci_risk_scatter",
                                chart_id="ci_risk_scatter",
                                title="Configuration Item Risk Map",
                                eyebrow="Scatter",
                                subtitle="Top 20 CIs by incident count in the filtered set — size = critical incidents, color = % change-caused",
                                cfg={
                                    "x_title": "Incident Count", "y_title": "Avg Resolution (hrs)",
                                    "size_title": "Critical Incidents", "color_title": "% Change-Caused",
                                },
                                recompute="ci_risk_scatter",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
