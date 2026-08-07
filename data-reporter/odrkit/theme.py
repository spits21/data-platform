"""odrkit.theme - the SINGLE source of truth for the Ops Data Reporter corporate brand.

Ported verbatim from `DIIT.immi/showcase/theme.py` (COLORS, BASE_LAYOUT,
CHART_TYPE_DEFAULTS, PLOTLY_CONFIG, TURBO_BREAKPOINTS, PLOTLY_CDN) and extended
with the emitters ODR needs:

- COLORWAY       - ordered categorical trace colors (hex).
- apply_theme    - deep-merge BASE -> CHART_TYPE_DEFAULTS[type] -> existing
                   figure layout and return an already-themed go.Figure.
- to_css_vars    - a `:root { --odr-*: ... }` block for page chrome.
- to_quarto_scss - a Bootstrap/Quarto SCSS theme derived from the palette.

CSS vars, the Quarto SCSS, and the Plotly layout all read from the SAME palette
dict (COLORS) - there is no second copy of the brand anywhere. Rebranding is
a one-file hex edit here.

The ODR corporate brand is STRICT and NON-NEGOTIABLE: no non-ODR palette, sharp
corners everywhere (border-radius: 0), cyan h2 underline, system font stack only
(no external Google Fonts).

Merge order for every chart: BASE_LAYOUT -> CHART_TYPE_DEFAULTS[chart_type] ->
plot/builder overrides (existing fig.layout).
"""

from __future__ import annotations

import copy
import json
from typing import Any

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Color palette (single source of truth; CSS variable equivalents below)
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    "cyan": "#71C5E8",
    "cyan_dim": "rgba(113,197,232,0.12)",
    "cyan_mid": "rgba(113,197,232,0.25)",
    "dark_teal": "#235F73",
    "dark_teal_dim": "rgba(35,95,115,0.12)",
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#D00218",
    "purple": "#839AFF",
    "orange": "#E87C1E",
    "bg": "#FFFFFF",
    "bg_alt": "#f5f5f5",
    "bg_card": "#f5f5f5",
    "text": "#000000",
    "text_dim": "#444444",
    "text_muted": "#888888",
    "border": "#E2E2E2",
    "grid_line": "rgba(0,0,0,0.08)",
    "actual_marker": "#000000",
    "economic_muted": "#999999",
}

# Ordered categorical colorway (apply as layout.colorway or trace-by-trace).
# Brand colors first, then muted grays:
#   cyan -> dark_teal -> orange -> purple -> red -> muted grays
COLORWAY: list[str] = [
    COLORS["cyan"],       # #71C5E8
    COLORS["dark_teal"],  # #235F73
    COLORS["orange"],     # #E87C1E
    COLORS["purple"],     # #839AFF
    COLORS["red"],        # #D00218
    "#888888",
    "#bbbbbb",
    "#666666",
    "#dddddd",
]

# ---------------------------------------------------------------------------
# Plotly BASE_LAYOUT (deep-merged with per-type defaults + plot overrides)
# ---------------------------------------------------------------------------

BASE_LAYOUT: dict[str, Any] = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {
        "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "color": COLORS["text_dim"],
        "size": 13,
    },
    "margin": {"l": 55, "r": 20, "t": 30, "b": 50},
    "xaxis": {
        "gridcolor": COLORS["grid_line"],
        "zerolinecolor": COLORS["grid_line"],
        "tickfont": {"size": 11, "color": COLORS["text_muted"]},
        "title": {"font": {"size": 14}},
        "linecolor": COLORS["grid_line"],
    },
    "yaxis": {
        "gridcolor": COLORS["grid_line"],
        "zerolinecolor": COLORS["grid_line"],
        "tickfont": {"size": 11, "color": COLORS["text_muted"]},
        "title": {"font": {"size": 14}},
        "linecolor": COLORS["grid_line"],
    },
    "legend": {
        "bgcolor": "rgba(0,0,0,0)",
        "font": {"size": 11, "color": COLORS["text_dim"]},
        "orientation": "h",
        "x": 0,
        "y": 1.08,
    },
    "hoverlabel": {
        "bgcolor": COLORS["black"],
        "bordercolor": COLORS["cyan"],
        "font": {
            "family": "-apple-system, sans-serif",
            "size": 11,
            "color": "#FFFFFF",
        },
    },
}

# ---------------------------------------------------------------------------
# Plotly modebar config. NOTE: config is the 4th arg to Plotly.newPlot; it is
# NOT part of layout and is dropped by fig.to_plotly_json(). Renderers apply
# it at write_html / newPlot time, not inside apply_theme.
# ---------------------------------------------------------------------------

# Presentation decks: modebar hidden.
PLOTLY_CONFIG: dict[str, Any] = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}

# Standalone viz / docs / Quarto: interactive modebar with clutter removed.
PLOTLY_CONFIG_INTERACTIVE: dict[str, Any] = {
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "displaylogo": False,
    "responsive": True,
}

# ---------------------------------------------------------------------------
# Turbo colorscale breakpoints for percentile heat.
# <20: cool/blue, 20-50: mid/green, >50: warm/orange-red.
# ---------------------------------------------------------------------------

TURBO_BREAKPOINTS: list[list] = [
    [0.00, "#30123b"],
    [0.05, "#3e2eb8"],
    [0.10, "#4662d7"],
    [0.15, "#38a1fb"],
    [0.20, "#36aaf9"],
    [0.30, "#1ac4b6"],
    [0.40, "#42f876"],
    [0.50, "#72fe5e"],
    [0.60, "#a6f030"],
    [0.65, "#c8ef34"],
    [0.70, "#dfcd2c"],
    [0.80, "#faba39"],
    [0.85, "#f98d25"],
    [0.90, "#f66b19"],
    [1.00, "#7a0403"],
]

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"
D3_CDN = "https://cdn.jsdelivr.net/npm/d3@7"


def turbo_colorscale() -> list[list]:
    """Return a deep copy of the Turbo breakpoints for use as a colorscale."""
    return copy.deepcopy(TURBO_BREAKPOINTS)


# On-brand sequential colorscale (white -> ODR cyan -> dark teal). A single-hue
# ODR ramp for magnitude heat where the neon Turbo rainbow is off-brand or
# distorts perceived magnitude. Same stops the treemap/sunburst read as ODR.
ODR_SEQUENTIAL: list[list] = [
    [0.00, "#f5fbfe"],  # near-white (very low)
    [0.25, "#c7e8f5"],  # pale cyan
    [0.50, "#71C5E8"],  # ODR cyan
    [0.75, "#4a92ab"],  # cyan -> teal blend
    [1.00, "#235F73"],  # ODR dark teal (high)
]


def odr_sequential_colorscale() -> list[list]:
    """Return the on-brand white -> cyan -> dark-teal sequential colorscale."""
    return copy.deepcopy(ODR_SEQUENTIAL)


def percentile_to_color(pct: float) -> str:
    """Map a percentile (1-100) to a Turbo colorscale hex color.

    Breakpoints: <20 cool blue, 20-50 green, >50 warm orange.
    (Simplified 3-band form; the 15-stop TURBO_BREAKPOINTS is authoritative.)
    """
    if pct < 20:
        return "#4662d7"  # cool blue
    elif pct < 50:
        return "#72fe5e"  # green
    else:
        return "#f66b19"  # warm orange


# ---------------------------------------------------------------------------
# Chart-type Plotly layout defaults (sit between BASE_LAYOUT and overrides).
# Merge order: BASE_LAYOUT -> CHART_TYPE_DEFAULTS[type] -> plot overrides.
# This is where cross-chart visual consistency is enforced. Some entries carry
# fallback axis titles from the source project - builders override them via
# the figure layout (the highest-precedence "overrides" layer), so they are
# only defaults, not hard constraints.
# ---------------------------------------------------------------------------

CHART_TYPE_DEFAULTS: dict[str, dict] = {
    "timeseries": {
        "xaxis": {
            "type": "date",
            "dtick": "M1",
            "tickformat": "%b '%y",
            "title": {"text": "", "standoff": 10},
        },
        "yaxis": {
            "title": {"standoff": 10},
            "rangemode": "tozero",
        },
        "hovermode": "closest",
        "margin": {"l": 60, "r": 20, "t": 55, "b": 50},
    },
    "distribution": {
        "xaxis": {
            "title": {"text": "CPR (%)", "standoff": 10},
        },
        "yaxis": {
            "title": {"text": "Density", "standoff": 10},
            "rangemode": "tozero",
        },
        "bargap": 0.05,
        "hovermode": "closest",
        "margin": {"l": 55, "r": 20, "t": 30, "b": 50},
    },
    "scatter": {
        "hovermode": "closest",
        "margin": {"l": 55, "r": 20, "t": 30, "b": 50},
    },
    "bar": {
        "xaxis": {
            "title": {"standoff": 10},
        },
        "yaxis": {
            "rangemode": "tozero",
            "title": {"standoff": 10},
        },
        "bargap": 0.15,
        "hovermode": "closest",
        "margin": {"l": 55, "r": 20, "t": 30, "b": 50},
    },
    "ridgeline": {
        "xaxis": {
            "title": {"text": "CPR (%)", "standoff": 10},
        },
        "yaxis": {
            "showgrid": False,
            "zeroline": False,
        },
        "hovermode": "closest",
        "showlegend": False,
        "margin": {"l": 80, "r": 20, "t": 30, "b": 50},
    },
    "waterfall": {
        "xaxis": {
            "title": {"standoff": 10},
        },
        "yaxis": {
            "title": {"text": "CPR (%)", "standoff": 10},
        },
        "hovermode": "closest",
        "margin": {"l": 55, "r": 20, "t": 30, "b": 50},
    },
    "ladder": {
        "xaxis": {
            "title": {"text": "CPR Contribution", "standoff": 10},
            "zeroline": True,
            "zerolinewidth": 1.5,
        },
        "yaxis": {
            "autorange": "reversed",
            "showgrid": False,
        },
        "hovermode": "closest",
        "margin": {"l": 120, "r": 20, "t": 30, "b": 50},
    },
    "heatmap": {
        "hovermode": "closest",
        "margin": {"l": 80, "r": 80, "t": 55, "b": 60},
    },
    "treemap": {
        "hovermode": "closest",
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
    },
    "indicator": {
        "hovermode": "closest",
        "margin": {"l": 40, "r": 40, "t": 60, "b": 40},
    },
    "funnel": {
        "hovermode": "closest",
        "margin": {"l": 160, "r": 60, "t": 55, "b": 40},
    },
    "dual_axis": {
        "xaxis": {
            "title": {"standoff": 10},
        },
        "yaxis": {
            "title": {"standoff": 10},
            "rangemode": "tozero",
        },
        "yaxis2": {
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "gridcolor": COLORS["grid_line"],
            "zerolinecolor": COLORS["grid_line"],
            "tickfont": {"size": 11, "color": COLORS["text_muted"]},
            "title": {"font": {"size": 14}, "standoff": 10},
            "linecolor": COLORS["grid_line"],
        },
        "bargap": 0.15,
        "hovermode": "closest",
        "margin": {"l": 55, "r": 60, "t": 30, "b": 50},
    },
    "sunburst": {
        "hovermode": "closest",
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
    },
    "sankey": {
        "hovermode": "closest",
        "margin": {"l": 20, "r": 20, "t": 40, "b": 20},
        "font": {"size": 11},
    },
    "surface3d": {
        "hovermode": "closest",
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
        "scene": {
            "xaxis": {"gridcolor": COLORS["grid_line"], "backgroundcolor": "rgba(0,0,0,0)"},
            "yaxis": {"gridcolor": COLORS["grid_line"], "backgroundcolor": "rgba(0,0,0,0)"},
            "zaxis": {"gridcolor": COLORS["grid_line"], "backgroundcolor": "rgba(0,0,0,0)"},
        },
    },
    "violin": {
        "xaxis": {
            "title": {"text": "Coupon (%)", "standoff": 10},
        },
        "yaxis": {
            "title": {"text": "Error (CPR ppt)", "standoff": 10},
            "zeroline": True,
            "zerolinecolor": "rgba(0,0,0,0.3)",
            "zerolinewidth": 1.5,
        },
        "hovermode": "closest",
        "margin": {"l": 60, "r": 20, "t": 55, "b": 50},
    },
}

VALID_CHART_TYPES: tuple[str, ...] = tuple(CHART_TYPE_DEFAULTS.keys())


# ---------------------------------------------------------------------------
# Deep merge (b wins; recurse plain dicts). Mirrors the JS deepMerge in the
# deck/doc runtime so Python-side and any JS-side merges agree.
# ---------------------------------------------------------------------------

def _deep_merge(a: dict, b: dict) -> dict:
    """Return a new dict: values in ``b`` win, plain-dict values recurse."""
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def apply_theme(fig: go.Figure, chart_type: str) -> go.Figure:
    """Bake the ODR theme into fig and return it.

    Deep-merges, in precedence order (later wins):
        BASE_LAYOUT
        -> CHART_TYPE_DEFAULTS[chart_type] (falls back to BASE only if
           chart_type is unknown)
        -> the figure's EXISTING layout (the builder's overrides win)

    Then sets ``colorway``, the brand font, and transparent backgrounds.
    The builder's own layout choices always take precedence over the
    defaults; an unknown ``chart_type`` degrades to BASE_LAYOUT (no
    KeyError).

    NOTE: Plotly ``config`` (modebar) is NOT layout and is intentionally not
    applied here - renderers pass it as the 4th arg at newPlot / write_html
    time.
    """
    type_defaults = CHART_TYPE_DEFAULTS.get(chart_type, {})
    # Existing figure layout is the highest-precedence "overrides" layer.
    existing = fig.to_plotly_json().get("layout", {}) or {}

    merged = _deep_merge(BASE_LAYOUT, type_defaults)
    merged = _deep_merge(merged, existing)

    # Font, colorway, transparent backgrounds are brand-enforced (BASE already
    # sets font/bg; colorway is applied unless the figure explicitly set one).
    merged.setdefault("colorway", COLORWAY)

    fig.update_layout(merged, overwrite=True)
    return fig


# ---------------------------------------------------------------------------
# CSS variable generation (page chrome). Derived from COLORS - no second copy.
# ---------------------------------------------------------------------------

# Python palette key -> CSS custom property name. Kept in one place so CSS vars
# and the Quarto SCSS both read the identical palette.
_CSS_VAR_MAP: dict[str, str] = {
    "cyan": "--odr-cyan",
    "cyan_dim": "--odr-cyan-dim",
    "cyan_mid": "--odr-cyan-mid",
    "dark_teal": "--odr-dark-teal",
    "dark_teal_dim": "--odr-dark-teal-dim",
    "black": "--odr-black",
    "white": "--odr-white",
    "red": "--odr-red",
    "purple": "--odr-purple",
    "orange": "--odr-orange",
    "bg": "--bg",
    "bg_alt": "--bg-alt",
    "bg_card": "--bg-card",
    "text": "--text",
    "text_dim": "--text-dim",
    "text_muted": "--text-muted",
    "border": "--border",
    "grid_line": "--grid-line",
    "actual_marker": "--actual-marker",
    "economic_muted": "--economic-muted",
}

# Two distinct font stacks (do NOT unify). The CSS body stack keeps
# Helvetica/Arial; the Plotly font family (in BASE_LAYOUT) drops them.
FONT_BODY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"


def to_css_vars() -> str:
    """Return a ``:root { ... }`` block of ODR CSS custom properties.

    Includes the palette (from COLORS) plus the font stacks. Consumed by the
    deck/doc page chrome (header, nav, KPI cards, footer, controls).
    """
    lines = [":root {"]
    for py_key, css_var in _CSS_VAR_MAP.items():
        if py_key in COLORS:
            lines.append(f"  {css_var}: {COLORS[py_key]};")
    lines.append(f"  --font-body: {FONT_BODY};")
    lines.append(f"  --font-mono: {FONT_MONO};")
    lines.append("}")
    return "\n".join(lines)


def to_quarto_scss() -> str:
    """Return a Bootstrap/Quarto SCSS theme derived from the palette.

    Two blocks per the Quarto contract:
        ``/*-- scss:defaults --*/`` : Bootstrap variable overrides.
        ``/*-- scss:rules --*/``    : :root CSS vars + brand rules
            (sharp corners, cyan h2 underline, system font, disclaimer
            styling, synthetic-data marker).

    Same palette as ``to_css_vars`` and ``BASE_LAYOUT`` - one source, two
    emitters, so the Quarto target and the custom-HTML target look identical.
    """
    c = COLORS
    css_vars = "\n".join(
        f"  {css_var}: {c[py_key]};"
        for py_key, css_var in _CSS_VAR_MAP.items()
        if py_key in c
    )
    return f"""/*-- scss:defaults --*/
// Generated from odrkit.theme.COLORS - do not hand-edit; rebrand in theme.py.
$body-bg: {c["bg"]};
$body-color: {c["text"]};
$font-family-sans-serif: {FONT_BODY};
$font-family-monospace: {FONT_MONO};
$link-color: {c["dark_teal"]};       // dark_teal
$link-hover-color: {c["cyan"]};      // cyan
$border-radius: 0;                   // sharp corners everywhere
$border-radius-sm: 0;
$border-radius-lg: 0;
$border-color: {c["border"]};

/*-- scss:rules --*/
:root {{
{css_vars}
  --font-body: {FONT_BODY};
  --font-mono: {FONT_MONO};
}}

body {{
  font-family: var(--font-body);
  font-variant-numeric: tabular-nums; // tabular numerals for metrics/dates/IDs
  -webkit-font-smoothing: antialiased;
}}

// ODR cyan underline motif on h2
h2 {{
  font-weight: 700;
  color: var(--odr-black);
  text-decoration: underline;
  text-decoration-color: var(--odr-cyan);
  text-underline-offset: 8px;
  text-decoration-thickness: 4px;
}}

h3 {{ font-weight: 600; color: var(--odr-dark-teal); text-decoration: none; }}

// Sharp corners everywhere (single documented exception: Quarto TOC pill toggle)
.card, .control-group, .kpi-card, .callout, pre, code, .sourceCode,
input, select, button, .btn {{ border-radius: 0; }}

.kpi-card {{
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-top: 3px solid var(--odr-cyan);
}}

// Active TOC link: cyan left border
#TOC a.active, .sidebar nav a.active, nav[role="doc-toc"] a.active {{
  border-left: 3px solid var(--odr-cyan);
  color: var(--odr-dark-teal);
  font-weight: 600;
}}

// Letterhead (right-aligned logo, cyan bottom border)
.odr-letterhead {{
  display: flex; justify-content: space-between; align-items: flex-start;
  padding-bottom: 1.2rem; margin-bottom: 1.5rem;
  border-bottom: 3px solid var(--odr-cyan);
}}
.odr-letterhead img {{ height: 56px; width: auto; flex-shrink: 0; }}

// Legal disclaimer (h2 underline suppressed here)
.odr-disclaimer {{
  margin-top: 3rem; padding-top: 1.5rem;
  border-top: 3px solid var(--border);
}}
.odr-disclaimer h2 {{ text-decoration: none; font-size: 1.1rem; }}
.odr-disclaimer p {{ font-size: 0.72rem; color: var(--text-muted); text-align: justify; }}

// Synthetic-data marker (required on every synthetic artifact)
.synthetic-marker {{ color: var(--red); font-weight: 700; letter-spacing: 0.03rem; }}

// Confidentiality marker (matches the deck/doc "CONFIDENTIAL | ODR" footer)
.confidential {{
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04rem;
  color: var(--text-dim); text-transform: uppercase; margin-bottom: 0.4rem;
}}
"""


def template_context() -> dict:
    """Return brand values as a template-injection context.

    JSON strings are provided for the deck/doc page-glue JS, which still
    needs BASE_LAYOUT / CHART_TYPE_DEFAULTS available client-side for any
    figure not pre-themed in Python (defensive; Python-built figures already
    carry layout).
    """
    return {
        "colors": COLORS,
        "colors_json": json.dumps(COLORS),
        "colorway": COLORWAY,
        "colorway_json": json.dumps(COLORWAY),
        "base_layout_json": json.dumps(BASE_LAYOUT),
        "chart_type_defaults_json": json.dumps(CHART_TYPE_DEFAULTS),
        "plotly_config_json": json.dumps(PLOTLY_CONFIG),
        "plotly_config_interactive_json": json.dumps(PLOTLY_CONFIG_INTERACTIVE),
        "turbo_breakpoints_json": json.dumps(TURBO_BREAKPOINTS),
        "plotly_cdn": PLOTLY_CDN,
        "d3_cdn": D3_CDN,
        "css_vars": to_css_vars(),
        "font_body": FONT_BODY,
        "font_mono": FONT_MONO,
    }
