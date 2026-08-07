# Ops Data Reporter (ODR) — interactive ODR-branded reports, generated on command

A self-contained, **general-purpose** starter kit for the kind of reporting an
analytics team ships every day: polished, interactive, strictly on-brand HTML —
built by a deterministic Python engine and driven, in plain English, by Claude
*skills*. It is deliberately **not** specific to any one business area: swap the
data and write a small role module, and the same machinery reports on corporate
finance, sales, marketing, operations, data-center cost, or whatever you track.

> **The PowerPoint-killer, the Word-killer, and the BI-tool-killer, from one
> source of truth.** One declarative report spec renders as a scroll-snap
> **slide deck** *and* a long-scroll interactive **document**; a parallel
> declarative spec renders a tabbed, filterable **dashboard**. A **16-chart**
> Plotly library, **two** document engines (a custom Python engine *and*
> Quarto), and **3** skills — all in one emailable folder, every chart
> headless-verified to render with zero console errors.

This package is a working **template you can steal**: run it offline, rebrand it
in one file, point it at your own data, and have your own agents extend it.

> **Legal:** the governing ODR Data disclaimer is loaded verbatim from
> `odrkit/content/disclaimer.txt` and rendered into every artifact. **All bundled
> data is synthetic and illustrative — not real ODR figures** (see the
> synthetic-data marker on every output and `data/DATA_DICTIONARY.md`).

## Contents

- [The big idea](#the-big-idea-a-deterministic-engine-a-skill-glue)
- [Quickstart](#quickstart)
- [What's in the box](#whats-in-the-box)
- [The demo roles](#the-demo-roles)
- [The chart library](#the-chart-library)
- [Three front ends: decks, docs, and dashboards](#three-front-ends-decks-docs-and-dashboards)
- [Quarto parameterized reporting](#quarto-parameterized-reporting)
- [The three skills](#the-three-skills)
- [Make it yours](#make-it-yours)
- [The ODR brand](#the-odr-brand)
- [Design notes & honesty](#design-notes--honesty)

---

## The big idea: a deterministic engine, a skill glue

```
                    you ask, in plain English
                              |
                              ▼
  ┌──────────────────────────────────────────┐   interpret the request · choose the
  │ Claude + skill  —  the GLUE               │   role, period, deck/doc/dashboard ·
  │ (flexible, fuzzy, conversational)         │   read the result and explain it
  └──────────────────────────────────────────┘
                              |  calls deterministic verbs
                              ▼
  ┌──────────────────────────────────────────┐   query data · build themed Plotly ·
  │ ODR / odrkit  —  the CORE                 │   compose one ReportSpec · embed the
  │ (deterministic · tested · repeatable)     │   brand and the legal disclaimer
  └──────────────────────────────────────────┘
                              |
                              ▼
     one self-contained, interactive, ODR-branded .html  (deck · doc · Quarto)
```

The split is the point. **The engine is deterministic**: same role + period +
format → the same report, every time, and the figures are trustworthy because a
tested program computed them — not a language model. **The skill is the flexible
interface**: it interprets a vague ask, picks the parameters, runs the engine,
and explains the output — it never hand-writes HTML or hand-computes a figure.
That is how you get flexibility *and* correctness at once, and why it is safe to
let an assistant *extend* the system.

One more principle runs through everything: **one source of truth, many
targets.** A single role module drives the deck, the custom doc, *and* the
Quarto doc from the same period-parameterized data shapers and the same chart
builders — so the three can never drift, and every narrative number is computed
from the data.

---

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/) and (for Quarto docs)
[Quarto](https://quarto.org/) ≥ 1.9.

```bash
cd ops-data-reporter                              # or whatever you cloned/renamed this folder to
uv sync                                            # create .venv + install odrkit and deps
uv run odr doctor                                  # env + data + chart self-tests
uv run odr list-charts                             # the 16-chart library
uv run odr list-roles                              # data roles + datasets

uv run odr build-role --role corporate_finance --format deck        # → a deck
uv run odr build-role --role opsgov_incidents  --format doc         # → a doc (real, live data)
uv run odr build-role --role opsgov_incidents  --format dashboard   # → a filterable dashboard
uv run odr viz-catalog                                               # → one of every chart + code

open artifacts/*/*.html viz_catalog.html           # macOS
```

Everything resolves relative to this folder. Zip it (minus `.venv`), email it,
unzip, `uv sync` — it reproduces. Charts load Plotly/D3 from CDN, so an internet
connection is needed to draw them (Quarto docs inline everything and work
offline). Rendered artifacts live under `artifacts/<role>/`.

---

## What's in the box

```
ops-data-reporter/
├── README.md                    this file
├── pyproject.toml · uv.lock     uv-managed deps + locked versions (reproducible)
├── odrkit/                      the deterministic core
│   ├── theme.py                 ★ single source of truth for the ODR brand
│   ├── charts/                  one folder per chart plugin (16, auto-discovered)
│   ├── report_spec.py           ReportSpec / SectionSpec (declarative reports)
│   ├── deck.py + templates/deck.html.j2    scroll-snap deck renderer (PowerPoint-killer)
│   ├── doc.py + templates/doc.html.j2      long-scroll doc renderer (Word-killer)
│   ├── dashboard_spec.py + dashboard.py + templates/dashboard.html.j2   tabbed, filterable dashboard renderer (BI-tool-killer)
│   ├── roles/                   one module per business area (the 2 demo roles)
│   ├── data.py                  parquet/CSV loaders for data/<role>/
│   ├── content/                 verbatim disclaimer + synthetic notice
│   └── cli.py                   the `odr` command-line tool
├── data/                        synthetic datasets per role + DATA_DICTIONARY.md
├── quarto/                      Quarto project: _quarto.yml, _brand.scss, <role>/*.qmd
├── skills/                      the 3 Claude skills (the "glue" layer)
├── artifacts/                   the rendered outputs (deck · doc · Quarto), per role
└── viz_catalog.html             one of every chart, with its source
```

---

## The demo roles

Every role ships a slide deck **and** a document, from one role module; some
also ship a filterable dashboard. Each role's data + columns are documented
in `data/DATA_DICTIONARY.md`.

| Role | The story | Signature charts | Deck | Doc engine | Dashboard | Data |
|---|---|---|---|---|---|---|
| **corporate_finance** | FP&A quarterly business review for the CFO | KPI cards · revenue/opex time series · segment treemap · budget-vs-actual **variance bridge** | ✅ | **custom + Quarto** (flagship, both ways) | — | synthetic |
| **opsgov_incidents** | Incident & Change Request governance review | lifecycle **funnel** · resolution-time distributions · weekday×priority **heatmap** · priority→outcome **sankey** | ✅ | custom | ✅ tabbed, filterable | **real** (live Postgres) |

**corporate_finance** is the reference role, built **both** doc ways side by
side so you can compare the engines directly; its Quarto doc is the
parameterization demo (multiple fiscal periods → multiple self-contained
reports). **opsgov_incidents** is the real-data reference: it reads live from
Postgres (requires a populated `.env`, see `.env.example`) and renders with
`ReportSpec.synthetic=False` — no illustrative-data marker. It is also the
dashboard reference: two tabs (Overview; Priority & Risk), a date-range +
priority/impact/change-request filter bar that re-slices every panel and KPI
client-side — see [Three front ends](#three-front-ends-decks-docs-and-dashboards).

More roles are straightforward to add — see [Make it yours](#make-it-yours)
and the `odr-new-domain` skill.

---

## The chart library

Sixteen domain-agnostic Plotly builders, each a folder under `odrkit/charts/`,
auto-discovered by the registry. Each returns an already-themed `go.Figure`, is
self-testing via a `sample()`, and takes a column-mapping `cfg` so any role can
reuse it. The set is chosen to cover the full range of Plotly chart shapes *and*
interaction modalities:

| Chart (`id`) | Family | Interactions demonstrated |
|---|---|---|
| `timeseries_multi` | time series | rangeslider, 1Y/3Y/All range buttons, legend isolate, unified hover |
| `grouped_stacked_bar` | bar | grouped/stacked, hover, legend toggle |
| `waterfall` | bridge | level bridge *and* zero-based variance bridge (favorable/unfavorable colors) |
| `kpi_indicators` | indicator | number + delta cards / gauges |
| `scatter_bubble` | scatter | size + continuous colorbar, rich hover, optional y=x reference line |
| `treemap` | hierarchy | native click-to-zoom drill, colorbar |
| `sunburst` | hierarchy | radial click-drill, depth cap |
| `heatmap` | matrix | Turbo *or* on-brand ODR colorscale, colorbar |
| `funnel` | funnel | stage conversion, percent-of-initial |
| `sankey` | flow | node drag, flow hover |
| `surface3d` | 3-D | orbit / rotate / zoom, colorbar |
| `capacity_lines` | time series | breach/threshold line + shaded region + annotation |
| `ohlc_box` | range | OHLC / box range reading |
| `ridgeline` | distribution | layered density read |
| `distribution_violin` | distribution | violin + box + points |
| `controls_demo` | interactive | native `updatemenus` dropdown, cross-filter + animation play/pause slider |

Browse them rendered, each with its source, in **`viz_catalog.html`**
(`uv run odr viz-catalog`).

---

## Three front ends: decks, docs, and dashboards

A report is **declarative data**, not code: a `ReportSpec` is an ordered list of
`SectionSpec`s (`title`, `section`, `chart`, `chart_grid`, `prose`, `kpi_row`,
`disclaimer`). The *same* spec drives both linear renderers:

- **`odrkit.deck.build_deck`** — scroll-snap slides, one viewport each: black
  title slide, chart slides, KPI rows, a `CONFIDENTIAL | Ops Data Reporter` + slide-number footer, and a final verbatim-disclaimer slide.
- **`odrkit.doc.build_doc`** — a long-scroll responsive document with a sticky
  TOC (cyan active border), cyan-underlined headings, inline interactive charts,
  KPI cards, and the disclaimer + synthetic marker in the footer.

Both are a single self-contained HTML file (data embedded, Plotly from CDN).

### The third front end: a filterable dashboard

**`odrkit.dashboard.build_dashboard`** renders a parallel declarative spec —
`DashboardSpec` (`TabSpec -> GroupSpec` of either a `kpi_row` or a `grid` of
`PanelSpec`, plus a list of `FilterSpec`) — into a single-page dashboard: tabs
of grouped chart panels and KPI cards, with a sticky filter bar (date range +
categorical multiselects/dropdowns) above them.

Every panel's *initial* figure is built the normal way (the same
`ChartSpec.build` call deck/doc use). Filtering then happens **entirely in
the browser**: the dashboard embeds a row-level dataset (one row per record)
as JSON, and each filterable panel/KPI row names a small JS reducer that
re-derives its figure from the currently-filtered rows — a direct client-side
port of the same Python shaper's grouping logic, so a filter interaction
re-slices data the engine already computed rather than inventing a number.
Because every filter starts "wide open," the first client-side pass on page
load reproduces the server-rendered baseline exactly. No backend, no
round-trip — open the HTML file and it works offline (once Plotly's CDN
script has loaded once).

See `opsgov_incidents.build_dashboard_spec` for the reference implementation:
two tabs (Overview: headline KPIs, weekly volume, lifecycle funnel, backlog
bridge; Priority & Risk: weekday×priority heatmap, resolution-time box plot,
CI risk scatter), filtered by created-date range, priority, impact, and
change-request linkage.

### Two doc engines, side by side — tradeoffs

The custom doc and the Quarto doc render the SAME figures from the SAME
builders. When to reach for which:

| Dimension | Custom doc (`odrkit.doc`, Jinja2) | Quarto doc (`.qmd`) |
|---|---|---|
| Layout control | Total — hand-authored template + CSS | Bootstrap/Pandoc conventions; less bespoke |
| Self-containment | One HTML; Plotly from CDN (needs network) | One HTML; `embed-resources` inlines everything (offline) |
| Parameterization | Python: `build_report_spec(period)` | Native `params:` + `-P` at render |
| Authoring surface | Python `ReportSpec` (no prose in template) | Markdown + Python cells (prose lives in the doc) |
| Toolchain | Pure Python (jinja2) | Quarto CLI + jupyter kernel + papermill |
| "View code" drawer | Opt-in per section (`show_code`) | Native `code-fold` |
| Best for | Programmatic, templated, network-OK reports | Analyst-authored, offline, narrative-heavy docs |

Same brand, same charts, same data — different front ends. The custom engine
wins on layout precision and a zero-toolchain build; Quarto wins on offline
self-containment, native params, and letting an analyst write prose inline.

---

## Quarto parameterized reporting

The headline Quarto pattern: **one `.qmd`, one `period` param, three reports.**
The `.qmd` imports the role's shaping functions and the same library builders,
declares `params: { period: ... }`, and filters its content by the param.

```bash
ODR="$(pwd)"                                       # run this line from the repo root
cd quarto/corporate_finance
for p in 2025-Q3 2025-Q4 2026-Q1; do
  QUARTO_PYTHON="$ODR/.venv/bin/python" \
    uv run --project "$ODR" quarto render corporate_finance.qmd \
      -P period:$p --output "corporate_finance_quarto_${p/-/}.html"
done
# -> artifacts/corporate_finance/corporate_finance_quarto_{2025Q3,2025Q4,2026Q1}.html
```

**CRITICAL:** set `QUARTO_PYTHON` to the project venv (else Quarto uses system
Python and fails), and run from INSIDE the `.qmd`'s directory (running from the
repo root makes `--output` escape the project and emit a broken UN-EMBEDDED,
UN-THEMED file). `embed-resources: true` + `theme: _brand.scss` (in
`quarto/_quarto.yml`, generated from `odrkit.theme`) guarantee each render is
ONE self-contained HTML with Plotly and the ODR brand inlined — no sidecar
`*_files/` dir. The `-P period:` override uses `papermill` (a pinned
dependency).

The Quarto theme comes from the **same** `theme.py`: `theme.to_quarto_scss()`
emits `quarto/_brand.scss`, so decks, custom docs, and Quarto all share one ODR
palette. Rebrand once, everything follows.

---

## The three skills

Copy a folder into `~/.claude/skills/` (global) or a project's
`.claude/skills/`. They show the pattern in both directions — operate the
engine, and safely extend it:

- **`odr-report`** — *drive* the engine. Turns "build me the Q3
  corporate-finance deck" into the right command, picks parameters from the
  data, renders, and interprets the output (reading numbers from data, never
  inventing).
- **`odr-new-chart`** — *extend the library*. Teaches the `ChartSpec` contract
  so an agent can add a new themed Plotly chart by dropping in one folder — no
  engine edit.
- **`odr-new-domain`** — *onboard a new business area* end-to-end: drop in
  data, author a role module (shapers → registry → report spec), register it,
  and build its deck + doc (+ optional Quarto). The zero-to-hero path for your
  subject.

---

## Make it yours

- **Rebrand:** edit the palette/fonts in `odrkit/theme.py` — the single source
  of truth. It emits the CSS variables (chrome), the Plotly `BASE_LAYOUT`
  (charts), *and* the Quarto SCSS. Regenerate any report and it adopts the new
  identity.
- **Point at your own data:** drop parquet/CSV under `data/<role>/`; the loader
  discovers it (`odr list-roles`). Document it in `DATA_DICTIONARY.md`.
- **Add a chart:** use **odr-new-chart**, or copy `odrkit/charts/treemap/`.
- **Add a domain/role:** use **odr-new-domain**, or copy
  `odrkit/roles/corporate_finance.py` (the reference) and register it in
  `cli.py`.
- **Add a dashboard to a role:** copy `opsgov_incidents.build_dashboard_spec`
  (the reference) + its `shape_dashboard_rows`, and register it in `cli.py`'s
  `_ROLE_DASHBOARD_BUILDERS`.

---

## The ODR brand

Strictly enforced, all from `odrkit/theme.py`:

| Token | Value |
|---|---|
| ODR cyan | `#71C5E8` |
| Dark teal | `#235F73` |
| Black / white | `#000000` / `#ffffff` |
| Alert red | `#D0021B` |
| Card / alt bg | `#f5f5f5` |
| Border | `#E2E2E2` |
| Text / dim / muted | `#000000` / `#444444` / `#888888` |

Geometry: **sharp corners everywhere** (`border-radius: 0`); `h2` carries a
cyan underline; cards use a `2px` border and KPI cards a `3px` cyan top border;
active nav/TOC gets a cyan left border; deck title slides are black with cyan
accents. Type is the system font stack with tabular numerals. Plotly is
`2.35.2` with transparent backgrounds and the ordered ODR colorway.
**Forbidden:** emoji as UI icons, rounded/pill controls, gradient or neon
effects, external web fonts, and any non-ODR palette.

---

## Design notes & honesty

- **All data is synthetic.** Every dataset is generated (seed `20260709`) with
  an enforced consistency spine and a loud "illustrative synthetic data — not
  real ODR figures" marker on every artifact. Figures are for demonstration
  only.
- **No fabricated numbers.** Every value in every report is computed by the
  engine from the data; the skills are instructed never to state a metric they
  did not compute.
- **The disclaimer is verbatim.** Loaded from a protected text file and
  rendered into every artifact; never edited or paraphrased.
- **CDN vs offline.** Decks and custom docs load Plotly/D3 from a CDN (small,
  needs network). Quarto docs inline everything (offline, larger). Choose per
  the tradeoff table above.
- **Every chart is verified.** Charts self-test (`odr doctor`) and the rendered
  artifacts were checked in a headless browser: all render, on real synthetic
  data, with zero JavaScript console errors.

---

Built as a general, reusable pattern for ODR teams. The deterministic core
keeps the numbers honest; the skills make it effortless. See
`odrkit/content/disclaimer.txt` for the governing legal terms.
