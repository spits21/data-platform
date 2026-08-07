# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Ops Data Reporter (ODR) is a general-purpose, ODR-branded reporting toolkit: a
deterministic Python engine (`odrkit`) that builds interactive HTML
decks/docs/Quarto reports from synthetic data, glued together by three Claude
*skills* under `skills/`.

**The core split (read this before changing anything):** the engine (`odrkit`)
is deterministic — same role + period + format always produces the same
report, computed by tested code, never by an LLM. The skills are the flexible
interface — they interpret a request, pick parameters, run the CLI, and
interpret output, but never hand-write HTML or hand-compute a figure. When
extending the system, preserve this split: put logic in `odrkit`, put
interpretation/glue in skills.

**One source of truth, many targets:** each role module
(`odrkit/roles/<role>.py`) has period-parameterized data-shaping functions
that feed the same chart builders to drive the deck, the custom doc, and (for
some roles) the Quarto `.qmd` — all three must stay derivable from the same
shapers so they can't drift.

## Commands

```bash
uv sync                                                            # install deps into .venv
uv run odr doctor                                                  # env + theme + chart self-tests + data check — run after any change
uv run odr list-charts                                             # list the 16 registered charts
uv run odr list-roles                                              # list data roles + datasets under data/
uv run odr build-role --role corporate_finance --format deck       # build a deck (--format doc for the long-scroll doc)
uv run odr build-role --role opsgov_incidents --format doc --period 2026-Q1
uv run odr viz-catalog                                             # render every chart + its source into viz_catalog.html
```

Authored roles (have a report builder wired in `odrkit/cli.py`):
`corporate_finance` (synthetic data) and `opsgov_incidents` (real data — see
below).

There is no test suite / pytest. Correctness is verified by:
- `ChartSpec.self_test()` (each chart builds from its own `sample()` and
  asserts the figure is themed) — run via `odr doctor`.
- `ReportSpec.validate()` / `.validated()` — fail-fast checks for duplicate
  section ids, unknown `chart_id`s, unknown `kind`s, run before rendering.

Always run `uv run odr doctor` after touching `odrkit/theme.py`, any chart, or
`odrkit/content/`.

### Quarto rendering (parameterized reports)

Quarto docs (currently just `corporate_finance`) MUST be rendered from
**inside** the `.qmd`'s own project directory, with `QUARTO_PYTHON` pointed at
this repo's venv — otherwise Quarto uses system Python (fails) or `--output`
escapes the project and produces a broken, un-embedded, un-themed file (small,
~80 KB, vs. the correct ~5-6 MB self-contained output):

```bash
ODR="$(pwd)"                                    # from the repo root
cd quarto/corporate_finance
QUARTO_PYTHON="$ODR/.venv/bin/python" uv run --project "$ODR" quarto render corporate_finance.qmd \
  -P period:2026-Q1 --output corporate_finance_quarto_2026Q1.html
```

`embed-resources: true` + `theme: _brand.scss` in `quarto/_quarto.yml` (SCSS
generated from `odrkit/theme.py`) are what make the render self-contained and
on-brand.

## Architecture

```
odrkit/
├── theme.py            single source of truth for the ODR brand — CSS vars, Plotly BASE_LAYOUT, Quarto SCSS
├── charts/<id>/         one folder per chart, auto-discovered; __init__.py exports CHART = ChartSpec(...)
├── charts/_base.py       the ChartSpec contract (see below)
├── report_spec.py       ReportSpec / SectionSpec — the declarative report format shared by deck + doc
├── deck.py + templates/deck.html.j2    scroll-snap slide renderer
├── doc.py + templates/doc.html.j2      long-scroll doc renderer
├── roles/<role>.py      one module per business domain: data shapers + build_report_spec() + build_registry()
├── data.py               duckdb-backed parquet/CSV loader for data/<role>/
├── content/               verbatim legal disclaimer + synthetic-data notice (never edit/paraphrase)
└── cli.py                 the `odr` console entry point; _ROLE_BUILDERS wires each role in
```

### The ChartSpec contract (`odrkit/charts/_base.py`)

Every chart is a package under `odrkit/charts/<id>/` exporting `CHART =
ChartSpec(...)`. The registry in `odrkit/charts/__init__.py` auto-discovers
it — **adding a chart means dropping a folder, no registry edit.**
Load-bearing rules for `build(df, **cfg) -> go.Figure`:
- Must return an **already-themed** figure — last line is `return
  theme.apply_theme(fig, chart_type)`.
- `chart_type` must be one of `theme.VALID_CHART_TYPES` (selects Plotly layout
  defaults merged by `apply_theme`).
- `sample() -> pd.DataFrame` returns tiny illustrative data so
  `build(sample())` renders standalone (this is what `self_test()` calls).
- Hover labels must name metric AND unit explicitly (e.g. "Revenue ($M)"),
  never a bare unit.

### ReportSpec / SectionSpec (`odrkit/report_spec.py`)

A report is **declarative data, not code**: `ReportSpec` is an ordered list of
`SectionSpec`s (kinds: `title`, `section`, `chart`, `chart_grid`, `prose`,
`kpi_row`, `disclaimer`). The same spec drives both `odrkit.deck.build_deck`
and `odrkit.doc.build_doc`. `ReportSpec.validate(registry)` catches duplicate
ids / unknown `chart_id` / unknown `kind` before any rendering happens.

### Role modules (`odrkit/roles/<role>.py`)

Each role module is the single source of truth for one business domain,
driving its deck, custom doc, and (for some roles) Quarto `.qmd` — all from
the same period-parameterized shapers. Key pattern: the deck/doc renderers
normally call a chart's own `sample()` for demo data, but a role needs
**real** period-filtered data through the **same unmodified chart `build()`
functions**. This is solved with a **per-report registry keyed by section id**
(not chart id — the same chart, e.g. `waterfall`, may be used twice in one
report for different purposes and would collide if keyed by chart id) whose
`ChartSpec`s reuse the library `build` but bind a period-specific `sample()`.
Each role exposes `build_report_spec(period)` and `build_registry(period)`;
`cli.py`'s `_ROLE_BUILDERS` wires these into `build-role`.

No metric is ever invented — every KPI and every narrative number is computed
from the role's data shapers, never hand-typed into a template or by an LLM.

### Data (`odrkit/data.py`, `data/<role>/`)

Datasets live at `data/<role>/<dataset>.{parquet,csv}`, loaded via duckdb into
pandas (`data.load(role, dataset)`, or `data.load_cached` — callers must
`.copy()` before mutating). All data is **synthetic** (seed `20260709`),
documented in `data/DATA_DICTIONARY.md`; every generated artifact carries a
loud "illustrative synthetic data" marker — **except `opsgov_incidents`, the
one real-data role (see below), which reads live from Postgres and renders
with `ReportSpec.synthetic=False`.** A role's data
has an enforced internal consistency spine (e.g. in `corporate_finance`:
`gross_profit = revenue - cogs`, `ebitda = gross_profit - opex_total`) so
derived charts like waterfalls tie out by construction.

### Brand (`odrkit/theme.py`)

Single source of truth for ODR brand identity: emits CSS variables (chrome),
the Plotly `BASE_LAYOUT`/colorway (charts), and Quarto SCSS
(`theme.to_quarto_scss()` → `quarto/_brand.scss`) — rebrand once here and
every artifact (deck, doc, Quarto) follows. Sharp corners everywhere
(`border-radius: 0`), no gradients/rounded controls/emoji-as-icons/external
web fonts/non-ODR palette. The legal disclaimer
(`odrkit/content/disclaimer.txt`) must always be rendered verbatim, never
edited or summarized.

## Extending the system

- **New chart:** copy an existing folder under `odrkit/charts/`, follow the
  `ChartSpec` contract above; use the `odr-new-chart` skill for the guided
  version.
- **New role/domain:** drop data under `data/<role>/`, document it in
  `data/DATA_DICTIONARY.md`, author a role module (shapers →
  `build_report_spec`/`build_registry`), register it in `odrkit/cli.py`'s
  `_ROLE_BUILDERS` (+ `_ROLE_DEFAULT_PERIOD`); use the `odr-new-domain`
  skill for the guided version.
- **Rebrand:** edit `odrkit/theme.py` only; every renderer picks it up
  automatically.

## Skills (`skills/`)

Three Claude skills act as the "glue" layer over the deterministic engine —
copy into `~/.claude/skills/` or a project's `.claude/skills/`:
- `odr-report` — drives the engine, turns a plain-English ask into the right
  `odr build-role`/Quarto invocation, then interprets output numbers *from
  the data*, never invented.
- `odr-new-chart` — extends the chart library per the `ChartSpec` contract.
- `odr-new-domain` — onboards a new business area end-to-end (data → role
  module → registration → build).
