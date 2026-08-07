"""odrkit.dashboard — the DASHBOARD renderer (BI-tool-killer).

Compiles a ``DashboardSpec`` + a row-level ``pd.DataFrame`` into a single
self-contained HTML dashboard: tabs of grouped chart panels and KPI cards,
plus a filter bar (date range + categorical) that re-slices every panel and
KPI CLIENT-SIDE against the same row-level dataset the server used for the
initial render.

Every panel's INITIAL figure is built the normal ``ChartSpec`` way (same
``registry[chart_id].build(spec.sample(), **cfg)`` as deck/doc — no
parallel rendering path). Filtering afterward is handled in the browser by
JS reducers in ``dashboard.html.j2`` (see ``RECOMPUTE`` / ``KPI_RECOMPUTE``
there), each one a direct client-side port of the matching Python shaper's
grouping logic — so a filter interaction re-derives a number from the same
rows already shipped in the page, never invents one.

Public API: ``build_dashboard(spec, rows, out_path) -> Path``.
"""

from __future__ import annotations

import html
import json
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from . import theme
from .charts import REGISTRY as _CHART_REGISTRY
from .content import (
    COPYRIGHT_LINE,
    PROVENANCE_LINE,
    disclaimer_paragraphs,
    synthetic_notice,
)
from .dashboard_spec import DashboardSpec, FilterSpec, GroupSpec, PanelSpec

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _embed_figure(fig, *, config: dict, div_id: str) -> str:
    """Same embedding contract as deck/doc (Plotly loaded once from the CDN
    in ``<head>``), plus an explicit ``div_id`` so the filter JS can find
    this panel's ``<div>`` by id and call ``Plotly.restyle`` on it."""
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=config,
        default_width="100%",
        default_height="420px",
        div_id=div_id,
    )


def _render_panel(panel: PanelSpec, registry: dict, config: dict) -> str:
    spec = registry.get(panel.chart_id)
    if spec is None:
        return (
            f'<div class="chart-error">Unknown chart id: '
            f"{html.escape(panel.chart_id)}</div>"
        )
    try:
        df = spec.sample()
        fig = spec.build(df, **panel.cfg)
        return _embed_figure(fig, config=config, div_id=f"panel-{panel.id}")
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"dashboard: panel {panel.id!r} failed: {exc!r}", stacklevel=2
        )
        return f'<div class="chart-error">[chart error: {html.escape(str(exc))}]</div>'


def _resolve_filter(f: FilterSpec, rows: pd.DataFrame) -> dict[str, Any]:
    """Resolve a FilterSpec's rendered options/extent against the actual
    row-level data — never a hand-typed guess at what values exist."""
    if f.kind == "date_range":
        col = rows[f.field].dropna() if f.field in rows.columns else pd.Series([], dtype=object)
        extent = [str(col.min()), str(col.max())] if not col.empty else ["", ""]
        return {
            "id": f.id, "label": f.label, "field": f.field, "kind": f.kind,
            "options": [], "option_labels": {}, "extent": extent,
        }
    options = (
        list(f.options)
        if f.options
        else sorted(rows[f.field].dropna().unique().tolist())
        if f.field in rows.columns
        else []
    )
    return {
        "id": f.id, "label": f.label, "field": f.field, "kind": f.kind,
        "options": options, "option_labels": f.option_labels, "extent": [],
    }


def _json_for_script(obj: Any) -> str:
    """JSON-encode for embedding inside a ``<script>`` block: escape
    ``</`` so no data value (e.g. a free-text field) can prematurely close
    the tag."""
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")


def build_dashboard(
    spec: DashboardSpec,
    rows: pd.DataFrame,
    out_path: str | Path,
    *,
    registry: dict | None = None,
    config: dict | None = None,
    synthetic: bool | None = None,
) -> Path:
    """Render ``spec`` + ``rows`` to a single self-contained HTML dashboard
    at ``out_path``. Returns the written path.

    ``rows`` is the row-level dataset embedded for client-side filtering —
    a role's ``shape_dashboard_rows(period)`` (or equivalent), NOT the
    pre-aggregated per-chart shapes used by the registry.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    registry = _CHART_REGISTRY if registry is None else registry
    config = theme.PLOTLY_CONFIG_INTERACTIVE if config is None else config

    issues = spec.validate(registry=registry)
    if issues:
        raise ValueError("dashboard: invalid DashboardSpec:\n" + "\n".join(issues))
    synthetic = spec.synthetic if synthetic is None else synthetic

    panel_meta: dict[str, str] = {}
    kpi_meta: dict[str, dict] = {}

    tabs_ctx = []
    for t in spec.tabs:
        groups_ctx = []
        for g in t.groups:
            if g.kind == "kpi_row":
                if g.kpi_recompute:
                    kpi_meta[g.id] = {
                        "recompute": g.kpi_recompute,
                        "kpiIds": [k.id for k in g.kpis],
                    }
                groups_ctx.append(
                    {"kind": "kpi_row", "id": g.id, "title": g.title, "kpis": g.kpis}
                )
            else:
                panels_ctx = []
                for p in g.panels:
                    if p.recompute:
                        panel_meta[p.id] = p.recompute
                    panels_ctx.append(
                        {
                            "id": p.id,
                            "title": p.title,
                            "eyebrow": p.eyebrow,
                            "subtitle": p.subtitle,
                            "span": p.span,
                            "figure_html": _render_panel(p, registry, config),
                        }
                    )
                groups_ctx.append(
                    {
                        "kind": "grid",
                        "id": g.id,
                        "title": g.title,
                        "columns": g.columns,
                        "panels": panels_ctx,
                    }
                )
        tabs_ctx.append({"id": t.id, "label": t.label, "groups": groups_ctx})

    filters_ctx = [_resolve_filter(f, rows) for f in spec.filters]

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("dashboard.html.j2")

    ctx: dict[str, Any] = {
        **theme.template_context(),
        "dashboard_title": spec.title,
        "eyebrow": spec.eyebrow,
        "subtitle": spec.subtitle,
        "id_badge": spec.id_badge,
        "tabs": tabs_ctx,
        "filters": filters_ctx,
        "rows_json": _json_for_script(json.loads(rows.to_json(orient="records"))),
        "filters_json": _json_for_script(filters_ctx),
        "panel_meta_json": _json_for_script(panel_meta),
        "kpi_meta_json": _json_for_script(kpi_meta),
        "synthetic": synthetic,
        "synthetic_notice": synthetic_notice(),
        "disclaimer_paragraphs": disclaimer_paragraphs(),
        "copyright_line": COPYRIGHT_LINE,
        "provenance_line": PROVENANCE_LINE,
        "appends_disclaimer": spec.appends_disclaimer,
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template.render(**ctx), encoding="utf-8")
    return out_path
