"""odrkit.doc — the DOC renderer (Word-killer).

Compiles a shared ``ReportSpec`` into a single self-contained long-scroll
HTML document (the same spec that ``odrkit.deck.build_deck`` renders as a
slide deck):

- a sticky left TOC (cyan active-link left border) built from section titles;
- cyan-underlined ``h2`` headings, inline interactive charts, KPI cards;
- an ``odr-letterhead``-style header and a footer carrying the disclaimer +
  synthetic-data marker.

Plotly is loaded ONCE from the CDN in ``<head>``; each figure is embedded via
``fig.to_html(full_html=False, include_plotlyjs=False)``. Output is one
self-contained ``.html``.

Public API: ``build_doc(spec, out_path) -> Path`` where ``spec`` is a
``ReportSpec``.
"""

from __future__ import annotations

import html
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import theme
from .charts import REGISTRY as _CHART_REGISTRY
from .content import (
    COPYRIGHT_LINE,
    PROVENANCE_LINE,
    disclaimer_paragraphs,
    synthetic_notice,
)
from .report_spec import ReportSpec, SectionSpec

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class DocSectionSpec:
    """One rendered scroll-section. ``kind`` in {title, section, chart,
    chart_grid, prose, kpi_row, disclaimer}."""

    kind: str
    anchor: str = ""
    title: str = ""
    eyebrow: str = ""
    subtitle: str = ""
    body_html: str = ""
    figures_html: list[str] = field(default_factory=list)
    caption: str = ""
    code_html: str = ""
    css_class: str = ""
    in_toc: bool = True


def _md(text: str) -> str:
    if not text:
        return ""
    try:
        import markdown

        return markdown.markdown(text, extensions=["extra"])
    except Exception:  # noqa: BLE001 — markdown is optional
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "\n".join(f"<p>{html.escape(p)}</p>" for p in paras)


def _embed_figure(fig, *, config: dict) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=config,
        default_width="100%",
        default_height="480px",
    )


def _render_kpis(kpis) -> str:
    cards = []
    for k in kpis:
        sub = f'<div class="kpi-sub">{html.escape(k.sub)}</div>' if k.sub else ""
        cards.append(
            '<div class="kpi">'
            f'<div class="label">{html.escape(k.label)}</div>'
            f'<div class="value">{html.escape(k.value)}</div>'
            f"{sub}"
            "</div>"
        )
    return '<div class="kpi-strip">' + "".join(cards) + "</div>"


def _code_drawer(code: str) -> str:
    if not code:
        return ""
    return (
        '<details class="code-drawer"><summary>View code</summary>'
        f"<pre><code>{html.escape(code)}</code></pre></details>"
    )


def _slugify(text: str, fallback: str) -> str:
    text = (text or fallback).strip().lower()
    out = []
    prev_dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or fallback


def _build_section_figures(
    section: SectionSpec, registry: dict, config: dict
) -> tuple[list[str], str]:
    figures_html: list[str] = []
    code_parts: list[str] = []

    for cid in section.chart_id_list():
        spec = registry.get(cid)
        if spec is None:
            figures_html.append(
                f'<div class="chart-error">Unknown chart id: '
                f"{html.escape(cid)}</div>"
            )
            continue
        try:
            df = spec.sample()
            fig = spec.build(df, **section.cfg)
            figures_html.append(_embed_figure(fig, config=config))
            if section.show_code:
                code_parts.append(spec.source_code())
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"doc: chart {cid!r} in section {section.id!r} failed: {exc!r}",
                stacklevel=2,
            )
            figures_html.append(
                f'<div class="chart-error">[chart error: '
                f"{html.escape(str(exc))}]</div>"
            )

    return figures_html, "\n\n".join(p for p in code_parts if p)


def _section_to_doc_section(
    section: SectionSpec, registry: dict, config: dict, index: int
) -> DocSectionSpec:
    kind = section.kind
    body_html = ""
    figures_html: list[str] = []
    code_html = ""

    if kind in ("chart", "chart_grid"):
        figures_html, code_html = _build_section_figures(section, registry, config)
        if section.body_md:
            body_html = _md(section.body_md)
    elif kind == "kpi_row":
        body_html = _render_kpis(section.kpis)
        if section.body_md:
            body_html += _md(section.body_md)
    else:
        body_html = _md(section.body_md)

    anchor = _slugify(section.id or section.title, f"section-{index}")

    return DocSectionSpec(
        kind=kind,
        anchor=anchor,
        title=section.title,
        eyebrow=section.eyebrow,
        subtitle=section.subtitle,
        body_html=body_html,
        figures_html=figures_html,
        caption=section.caption,
        code_html=_code_drawer(code_html),
        css_class=section.css_class,
        in_toc=bool(section.title) and kind != "title",
    )


def _disclaimer_section() -> DocSectionSpec:
    return DocSectionSpec(
        kind="disclaimer",
        anchor="legal-notice",
        title="Legal Notice & Limitations",
        eyebrow="Legal",
        in_toc=True,
    )


def compile_spec(spec: ReportSpec, registry: dict, config: dict) -> list[DocSectionSpec]:
    """Compile a ReportSpec into an ordered list of DocSectionSpec."""
    sections: list[DocSectionSpec] = [
        DocSectionSpec(
            kind="title",
            anchor="top",
            title=spec.title,
            eyebrow=spec.eyebrow,
            subtitle=spec.subtitle,
            css_class="title-block",
            in_toc=False,
        )
    ]

    has_explicit_disclaimer = any(s.kind == "disclaimer" for s in spec.sections)
    for i, section in enumerate(spec.sections):
        if section.kind == "disclaimer":
            sections.append(_disclaimer_section())
        else:
            sections.append(_section_to_doc_section(section, registry, config, i))

    if spec.appends_disclaimer and not has_explicit_disclaimer:
        sections.append(_disclaimer_section())

    return sections


def build_doc(
    spec: ReportSpec,
    out_path: str | Path,
    *,
    registry: dict | None = None,
    config: dict | None = None,
    synthetic: bool | None = None,
) -> Path:
    """Render ``spec`` to a single self-contained HTML doc at ``out_path``."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    registry = _CHART_REGISTRY if registry is None else registry
    config = theme.PLOTLY_CONFIG_INTERACTIVE if config is None else config

    issues = spec.validate(registry=registry)
    if issues:
        raise ValueError("doc: invalid ReportSpec:\n" + "\n".join(issues))
    synthetic = spec.synthetic if synthetic is None else synthetic

    sections = compile_spec(spec, registry, config)
    toc_sections = [s for s in sections if s.in_toc]

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("doc.html.j2")

    ctx: dict[str, Any] = {
        **theme.template_context(),
        "doc_title": spec.title,
        "eyebrow": spec.eyebrow,
        "subtitle": spec.subtitle,
        "id_badge": spec.id_badge,
        "sections": sections,
        "toc_sections": toc_sections,
        "synthetic": synthetic,
        "synthetic_notice": synthetic_notice(),
        "disclaimer_paragraphs": disclaimer_paragraphs(),
        "copyright_line": COPYRIGHT_LINE,
        "provenance_line": PROVENANCE_LINE,
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template.render(**ctx), encoding="utf-8")
    return out_path
