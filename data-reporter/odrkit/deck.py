"""odrkit.deck — the DECK renderer (PowerPoint-killer).

Compiles a shared ``ReportSpec`` into a single self-contained scroll-snap HTML
deck that reproduces the ODR / IMMI deck look:

- one-viewport ``100dvh`` slides, ``scroll-snap-type: y mandatory``, overflow
  hidden (the one-viewport rule — content that overflows must be split, not
  scrolled);
- black title slide, white text, cyan accents;
- per-slide header (eyebrow + slide number), h2 with cyan underline, subtitle,
  body, and a ``CONFIDENTIAL | Ops Data Reporter`` + ``N / Total``
  footer stamped on every slide;
- keyboard / wheel / nav-dot navigation;
- the FINAL slide is the verbatim legal disclaimer + the synthetic-data marker.

Plotly is loaded ONCE from the CDN in ``<head>``; each figure is embedded via
``fig.to_html(full_html=False, include_plotlyjs=False)``. Output is one
self-contained ``.html``.

Public API: ``build_deck(spec, out_path) -> Path`` where ``spec`` is a
``ReportSpec`` (preferred) or a raw list of ``SlideSpec``.
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


# ---------------------------------------------------------------------------
# SlideSpec: the deck's per-slide dataclass. A ReportSpec compiles DOWN to a
# list of these. Callers may also hand-build SlideSpec lists directly.
# ---------------------------------------------------------------------------

@dataclass
class SlideSpec:
    """One rendered slide. ``kind`` in {title, section, chart, chart_grid,
    prose, kpi_row, disclaimer}."""

    kind: str
    title: str = ""
    eyebrow: str = ""
    subtitle: str = ""
    body_html: str = ""
    figures_html: list[str] = field(default_factory=list)
    caption: str = ""
    code_html: str = ""
    css_class: str = ""
    id_badge: str = ""


# ---------------------------------------------------------------------------
# Minimal Markdown -> HTML (no hard dependency; degrade to escaped paragraphs).
# ---------------------------------------------------------------------------

def _md(text: str) -> str:
    if not text:
        return ""
    try:
        import markdown

        return markdown.markdown(text, extensions=["extra"])
    except Exception:  # noqa: BLE001 — markdown is optional
        # Degrade: split on blank lines into <p>, escape everything.
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "\n".join(f"<p>{html.escape(p)}</p>" for p in paras)


# ---------------------------------------------------------------------------
# Figure embedding (CDN Plotly loaded once in <head>; per-figure div only).
# ---------------------------------------------------------------------------

def _embed_figure(fig, *, config: dict) -> str:
    """Return an HTML fragment (a div + inline script) for one figure.

    ``include_plotlyjs=False`` — the deck loads Plotly once from the CDN.
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=config,
        default_width="100%",
        default_height="100%",
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


# ---------------------------------------------------------------------------
# Compile a ReportSpec section -> SlideSpec(s).
# ---------------------------------------------------------------------------

def _build_section_figures(
    section: SectionSpec, registry: dict, config: dict
) -> tuple[list[str], str]:
    """Build the figures + code HTML for one chart / chart_grid section.

    Returns (figures_html, code_html). Failure of one chart degrades to an
    inline error note rather than killing the deck (per-section isolation).
    """
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
            df = spec.sample()  # data.py wiring is a caller concern; sample is safe
            fig = spec.build(df, **section.cfg)
            figures_html.append(_embed_figure(fig, config=config))
            if section.show_code:
                code_parts.append(spec.source_code())
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"deck: chart {cid!r} in section {section.id!r} failed: {exc!r}",
                stacklevel=2,
            )
            figures_html.append(
                f'<div class="chart-error">[chart error: '
                f"{html.escape(str(exc))}]</div>"
            )

    return figures_html, "\n\n".join(p for p in code_parts if p)


def _section_to_slide(
    section: SectionSpec, registry: dict, config: dict
) -> SlideSpec:
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
    else:  # title, section, prose
        body_html = _md(section.body_md)

    return SlideSpec(
        kind=kind,
        title=section.title,
        eyebrow=section.eyebrow,
        subtitle=section.subtitle,
        body_html=body_html,
        figures_html=figures_html,
        caption=section.caption,
        code_html=_code_drawer(code_html),
        css_class=section.css_class or ("fill-top" if figures_html else ""),
    )


def _disclaimer_slide(synthetic: bool) -> SlideSpec:
    return SlideSpec(
        kind="disclaimer",
        title="Legal Notice & Limitations",
        eyebrow="Legal",
    )


def compile_spec(spec: ReportSpec, registry: dict, config: dict) -> list[SlideSpec]:
    """Compile a ReportSpec into an ordered list of SlideSpec."""
    slides: list[SlideSpec] = []

    # Title slide from report identity.
    slides.append(
        SlideSpec(
            kind="title",
            title=spec.title,
            eyebrow=spec.eyebrow,
            subtitle=spec.subtitle,
            id_badge=spec.id_badge,
            css_class="title-slide",
        )
    )

    has_explicit_disclaimer = any(s.kind == "disclaimer" for s in spec.sections)
    for section in spec.sections:
        if section.kind == "disclaimer":
            slides.append(_disclaimer_slide(spec.synthetic))
        else:
            slides.append(_section_to_slide(section, registry, config))

    if spec.appends_disclaimer and not has_explicit_disclaimer:
        slides.append(_disclaimer_slide(spec.synthetic))

    return slides


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_deck(
    spec: ReportSpec | list[SlideSpec],
    out_path: str | Path,
    *,
    registry: dict | None = None,
    config: dict | None = None,
    synthetic: bool | None = None,
) -> Path:
    """Render ``spec`` to a single self-contained HTML deck at ``out_path``.

    ``spec`` may be a ``ReportSpec`` (compiled to slides) or a ready list of
    ``SlideSpec``. Returns the written path.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    registry = _CHART_REGISTRY if registry is None else registry
    config = theme.PLOTLY_CONFIG if config is None else config

    if isinstance(spec, ReportSpec):
        issues = spec.validate(registry=registry)
        if issues:
            raise ValueError(
                "deck: invalid ReportSpec:\n" + "\n".join(issues)
            )
        synthetic = spec.synthetic if synthetic is None else synthetic
        slides = compile_spec(spec, registry, config)
    else:
        slides = list(spec)
        synthetic = True if synthetic is None else synthetic
        if not any(s.kind == "disclaimer" for s in slides):
            slides.append(_disclaimer_slide(synthetic))

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("deck.html.j2")

    ctx: dict[str, Any] = {
        **theme.template_context(),
        "deck_title": (
            spec.title if isinstance(spec, ReportSpec) else "ODR Deck"
        ),
        "slides": slides,
        "total_slides": len(slides),
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
