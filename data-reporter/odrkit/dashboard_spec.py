"""odrkit.dashboard_spec — the declarative DASHBOARD format.

Mirrors the ``ReportSpec`` split (data, not code) but for a grouped/tabbed
dashboard with user-selectable filters instead of a linear slide/scroll
sequence:

- ``DashboardSpec`` -> ordered ``TabSpec`` -> ordered ``GroupSpec`` (a
  ``kpi_row`` or a ``grid`` of ``PanelSpec``), plus a list of ``FilterSpec``
  describing the filter controls rendered above the tabs.
- Every panel/KPI is first rendered SERVER-SIDE from the role's registry
  (same ``ChartSpec.build`` contract as deck/doc — no separate code path for
  the initial figures). ``PanelSpec.recompute`` / ``GroupSpec.kpi_recompute``
  optionally name a client-side JS reducer (defined once in
  ``dashboard.html.j2``) that re-derives that panel's figure from the SAME
  row-level dataset the server used, using the same grouping logic as the
  paired Python shaper — so a filter interaction never invents a number, it
  only re-slices data that was already computed by tested code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_FILTER_KINDS: tuple[str, ...] = ("date_range", "multiselect", "select")
VALID_GROUP_KINDS: tuple[str, ...] = ("grid", "kpi_row")


@dataclass
class FilterSpec:
    """One user-selectable filter control, bound to a field on the
    dashboard's row-level dataset.

    ``options`` is used for ``multiselect``/``select`` (empty = derive
    sorted unique values from the data at render time). ``extent`` is
    populated (min/max) for ``date_range`` only. ``option_labels`` overrides
    the display label for a raw option value (e.g. ``"true"`` ->
    ``"Change-Caused"``).
    """

    id: str
    label: str
    field: str
    kind: str = "multiselect"
    options: list[str] = field(default_factory=list)
    option_labels: dict[str, str] = field(default_factory=dict)


@dataclass
class PanelSpec:
    """One chart panel. ``chart_id`` looks up the initial server-rendered
    figure in the report's chart registry (same contract as
    ``SectionSpec.chart_id``). ``recompute`` names the client-side JS
    reducer (in ``RECOMPUTE`` in the template) that re-renders this panel's
    traces from filtered rows; empty = the panel does not respond to
    filters (its server-rendered figure is static)."""

    id: str
    chart_id: str
    title: str
    eyebrow: str = ""
    subtitle: str = ""
    cfg: dict = field(default_factory=dict)
    recompute: str = ""
    span: int = 1


@dataclass
class GroupSpec:
    """One visual grouping within a tab: either a row of KPI cards
    (``kind="kpi_row"``) or a grid of chart panels (``kind="grid"``)."""

    id: str
    title: str = ""
    kind: str = "grid"
    columns: int = 2
    panels: list[PanelSpec] = field(default_factory=list)
    kpis: list = field(default_factory=list)  # list[DashboardKPI], kpi_row only
    kpi_recompute: str = ""  # kpi_row only: JS reducer name in KPI_RECOMPUTE


@dataclass
class DashboardKPI:
    """One KPI card with a stable ``id`` so client-side filtering can target
    its value/sub-caption DOM nodes directly (unlike report_spec.KPI, which
    has no id since deck/doc KPIs never update in place)."""

    id: str
    label: str
    value: str
    sub: str = ""


@dataclass
class TabSpec:
    id: str
    label: str
    groups: list[GroupSpec] = field(default_factory=list)


@dataclass
class DashboardSpec:
    """A dashboard: report-level identity + a list of filters + an ordered
    list of tabs. ``synthetic`` / ``appends_disclaimer`` mirror
    ``ReportSpec``."""

    title: str
    eyebrow: str = ""
    subtitle: str = ""
    id_badge: str = ""
    synthetic: bool = True
    appends_disclaimer: bool = True
    filters: list[FilterSpec] = field(default_factory=list)
    tabs: list[TabSpec] = field(default_factory=list)

    def validate(self, registry: dict | None = None) -> list[str]:
        """Return a list of human-readable validation issues (empty = OK).

        Fail-fast and exhaustive, mirroring ``ReportSpec.validate``: unknown
        filter/group kinds, duplicate tab/panel ids, empty tabs, kpi_row
        groups with no KPIs, and (if ``registry`` given) chart ids not
        present in it.
        """
        issues: list[str] = []

        if not self.tabs:
            issues.append("DashboardSpec has no tabs")

        seen_tab_ids: dict[str, int] = {}
        seen_panel_ids: dict[str, int] = {}

        for f in self.filters:
            if f.kind not in VALID_FILTER_KINDS:
                issues.append(
                    f"filter {f.id!r}: unknown kind {f.kind!r} "
                    f"(expected one of {VALID_FILTER_KINDS})"
                )

        for t in self.tabs:
            seen_tab_ids[t.id] = seen_tab_ids.get(t.id, 0) + 1
            if not t.groups:
                issues.append(f"tab {t.id!r}: has no groups")
            for g in t.groups:
                if g.kind not in VALID_GROUP_KINDS:
                    issues.append(
                        f"group {g.id!r}: unknown kind {g.kind!r} "
                        f"(expected one of {VALID_GROUP_KINDS})"
                    )
                    continue
                if g.kind == "kpi_row" and not g.kpis:
                    issues.append(f"group {g.id!r}: kpi_row has no kpis")
                if g.kind == "grid":
                    if not g.panels:
                        issues.append(f"group {g.id!r}: grid has no panels")
                    for p in g.panels:
                        seen_panel_ids[p.id] = seen_panel_ids.get(p.id, 0) + 1
                        if not p.chart_id:
                            issues.append(f"panel {p.id!r}: empty chart_id")
                        elif registry is not None and p.chart_id not in registry:
                            issues.append(
                                f"panel {p.id!r}: unknown chart_id "
                                f"{p.chart_id!r} (not in registry)"
                            )

        for tid, count in seen_tab_ids.items():
            if count > 1:
                issues.append(f"duplicate tab id {tid!r} used {count} times")
        for pid, count in seen_panel_ids.items():
            if count > 1:
                issues.append(f"duplicate panel id {pid!r} used {count} times")

        return issues

    def validated(self, registry: dict | None = None) -> "DashboardSpec":
        """Return ``self`` if valid, else raise ``ValueError`` with the issues."""
        issues = self.validate(registry=registry)
        if issues:
            raise ValueError(
                "DashboardSpec is invalid:\n" + "\n".join(f"  - {i}" for i in issues)
            )
        return self
