---
name: odr-new-chart
description: Add a new chart to the odrkit chart library by implementing the ChartSpec contract. Use when the user wants a new Plotly chart type available across ODR reports (a new visualization shape/family not already covered by the 16-chart library), or asks to extend/modify an existing chart's behavior.
---

# odr-new-chart — extend the ODR chart library

Every chart is one folder under `odrkit/charts/<id>/` exporting a module-level
`CHART = ChartSpec(...)`. The registry (`odrkit/charts/__init__.py`)
auto-discovers every immediate subpackage that exports `CHART` — **adding a
chart means dropping a folder; you never edit the registry.**

## Before writing anything: does this need a NEW chart, or new usage of an
## EXISTING one?

The library is domain-agnostic by design — 16 charts already cover time
series, bar (grouped/stacked), bridge/waterfall, indicator, scatter/bubble,
treemap, sunburst, heatmap, funnel, sankey, 3-D surface, capacity/threshold
lines, OHLC/box, ridgeline, violin, and an interactive controls demo (run
`uv run odr list-charts` for the live list with each one's `family` /
`chart_type` / interactions). Most "I need a chart for X" requests are
actually "I need a role module that shapes X's data into one of these" — see
the **odr-new-domain** skill for that path. Only build a genuinely new chart
if none of the 16 existing shapes fit (e.g. nothing currently does a
calendar heatmap, a network graph, or a geo map).

## The ChartSpec contract (`odrkit/charts/_base.py`)

```python
@dataclass(frozen=True)
class ChartSpec:
    id: str                                  # registry key, matches the folder name
    title: str                               # human-readable title
    family: str                              # coarse grouping for list-charts/viz-catalog
    chart_type: str                          # must be in theme.VALID_CHART_TYPES
    build: Callable[..., go.Figure]          # (df, **cfg) -> themed go.Figure
    sample: Callable[[], pd.DataFrame]       # tiny illustrative data, build(sample()) must work standalone
    interactions: str = ""                   # short description for docs/catalog
```

Load-bearing rules (violating these fails `self_test()` / `odr doctor`):

1. `build(df, **cfg)` MUST return an **already-themed** figure — the last
   line is always `return theme.apply_theme(fig, "<chart_type>")`.
2. `chart_type` must be one of `theme.VALID_CHART_TYPES`. If your chart is a
   genuinely new layout family (not just a new use of an existing one), add
   an entry to `CHART_TYPE_DEFAULTS` in `odrkit/theme.py` — this is the
   **only** part of `theme.py` you touch for a new chart; never touch
   `COLORS` or the CSS/branding emitters, that's rebranding, a separate
   concern. Reuse an existing `chart_type` if your chart is visually/
   structurally close to one (e.g. a new hierarchy chart can reuse
   `"treemap"`'s margin defaults).
3. `sample() -> pd.DataFrame` returns small illustrative data so
   `build(sample())` renders standalone with ALL of `build`'s default `cfg`
   values — this is exactly what `self_test()` calls, and it's what powers
   `viz_catalog.html`.
4. Hover labels must name the metric AND its unit explicitly (e.g.
   `"Revenue ($M)"`), never a bare unit or a bare number.
5. Column names in `df` should be genuinely generic (`x`, `y`, `category`,
   `value`, `date`, `series`...) with every mapping overridable via a `cfg`
   keyword — a chart must stay reusable across unrelated roles. Look at
   `odrkit/charts/scatter_bubble/__init__.py` or `.../waterfall/__init__.py`
   for the pattern: sensible defaults, everything else a `cfg` override.

## Steps

1. **Copy an existing chart folder as a template.** Pick the closest analog
   by shape:
   - categorical bar/box/violin-ish → `odrkit/charts/grouped_stacked_bar/`
     or `.../distribution_violin/`
   - hierarchy → `odrkit/charts/treemap/` or `.../sunburst/`
   - flow → `odrkit/charts/sankey/`
   - time series → `odrkit/charts/timeseries_multi/` or `.../capacity_lines/`
2. **Write `sample()` first.** Small (10-60 rows), obviously fake, exercises
   every column your `build()` will read.
3. **Write `build()`.** Accept `df` plus `**cfg` keyword-only params with
   defaults matching your `sample()`'s column names. End with
   `return theme.apply_theme(fig, "<chart_type>")`.
4. **Export `CHART = ChartSpec(...)`** at module scope in `__init__.py`.
5. **Self-test it directly** before running the full suite:
   ```bash
   uv run python -c "
   from odrkit.charts import REGISTRY
   REGISTRY['<your_id>'].self_test()
   print('OK')
   "
   ```
6. **Run `uv run odr doctor`** — confirms your chart didn't break anything
   else and that it's correctly auto-discovered (it'll show up in the chart
   list `doctor` prints).
7. **Regenerate the catalog** so the new chart is visible with its source:
   `uv run odr viz-catalog` → check `viz_catalog.html` for your chart, no
   `chart-error` box.
8. If a role should actually USE this chart with real data, that's a
   `odrkit/roles/<role>.py` change (per-report registry binding via
   `dataclasses.replace(CHART, id=<section_id>, sample=lambda: shaped_df)`)
   — see the **odr-new-domain** skill, not this one.

## Common mistakes

- Forgetting `theme.apply_theme(...)` at the end of `build()` — `self_test()`
  asserts `paper_bgcolor == "rgba(0,0,0,0)"` and `"colorway" in layout`
  specifically to catch this.
- Hardcoding a `chart_type` not in `theme.VALID_CHART_TYPES` — raises
  immediately in `ChartSpec.__post_init__`, not silently.
- A `sample()` that only works with non-default `cfg` — `self_test()` always
  calls `build(sample())` with zero overrides.
- Baking role-specific column names or business logic into a chart —
  charts are domain-agnostic; put business logic in the role module's
  shaper functions instead.
