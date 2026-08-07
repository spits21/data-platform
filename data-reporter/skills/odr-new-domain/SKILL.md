---
name: odr-new-domain
description: Onboard a new business area/role into ODR end-to-end — data, a role module (shapers, report spec, per-report chart registry), CLI registration, and a built deck/doc (optionally Quarto). Use when the user wants a new kind of report (a new domain, team, or dataset) rather than a new chart type or a one-off build of an existing role.
---

# odr-new-domain — onboard a new business area

A role is the single source of truth for one business domain: period-
parameterized data shapers that feed the shared chart library, plus
`build_report_spec(period)` / `build_registry(period)` that drive the deck,
the custom doc, and (optionally) a Quarto doc — all three from the SAME
shapers, so they can't drift. No metric is ever hand-typed into a template;
every KPI and every narrative sentence is computed from data.

Read `odrkit/roles/corporate_finance.py` (synthetic data) and
`odrkit/roles/opsgov_incidents.py` (real/live data) in full before starting —
they are the two reference implementations this skill describes.

## 0. Decide: synthetic data, or a real/live source?

- **Synthetic** (the common case for a demo/illustrative role): you generate
  seeded data once, check it into `data/<role>/*.parquet`. Reports carry the
  "illustrative synthetic data" marker (`ReportSpec.synthetic=True`, the
  default).
- **Real/live** (rare — only when the user explicitly has a live system to
  report on, e.g. a database): no local file; query live in the shapers.
  Reports must NOT carry the synthetic marker (`ReportSpec.synthetic=False`).
  Document this distinction in `data/DATA_DICTIONARY.md`.

## 1a. Synthetic data path

1. Write `data/generate_<role>.py`: a standalone script, fixed seed (the
   convention in this repo is `20260709` — reuse it unless the user wants a
   different one), that builds one or more pandas DataFrames and writes them
   to `data/<role>/<dataset>.parquet`.
2. **Enforce a consistency spine and assert it before writing.** e.g.
   `corporate_finance`'s `gross_profit = revenue - cogs`,
   `ebitda = gross_profit - opex_total`, and every breakdown table (segment
   revenue, opex by category) sums EXACTLY to its parent total. Round the
   independent inputs first, then derive dependent columns from the rounded
   values — rounding after computing derived columns introduces sub-cent
   drift that fails an exact-equality assertion. Copy the assertion pattern
   at the bottom of `data/generate_corporate_finance.py`.
3. Run it: `uv run python data/generate_<role>.py`.
4. Document every column in `data/DATA_DICTIONARY.md` (new `## <role>/`
   section) — types, allowed values, and the spine equations.

## 1b. Real/live data path

1. Add role-scoped query helpers in `odrkit/roles/<role>.py` using
   `odrkit.data.query_postgres` / `query_postgres_cached` (duckdb's
   `postgres` extension — no new DB driver dependency). Get the DSN via
   `data.postgres_dsn_from_env("ODR_PG")` (or a role-specific prefix if you
   need a **different** database than the shared `.env` — most roles should
   share the one `.env`). NEVER hardcode a connection string or credentials
   in source, in a skill, or in chat.
2. If new environment variables are needed beyond what's already in
   `.env.example`, add them there with placeholder values (never real
   creds) and note it in your summary to the user — they must populate the
   real `.env` themselves (gitignored).
3. Cache the raw query once per shaper-call chain (see `_raw()` in
   `opsgov_incidents.py`) — `query_postgres_cached` is memoized by
   `(dsn, query)`, so calling it from every shaper with the *same* query
   string is cheap and correct; don't re-fetch per shaper with different
   post-filtering SQL, filter in pandas after one shared load instead.
4. Set `ReportSpec.synthetic=False` in `build_report_spec`.
5. Document the source table/columns in `data/DATA_DICTIONARY.md` under a
   `## <role> (real data — ...)` heading, and call out any schema
   limitations that constrain what a chart can honestly show (see
   `opsgov_incidents`'s note about having no state-change history — it
   shaped a funnel from a *current-state snapshot* rather than pretending it
   had historical stage-conversion data).
6. Add `odr doctor`'s role check will call your `build_report_spec` for
   real, which exercises the live connection — that's the health check for
   this path (there's no local dataset list to assert against).

## 2. Write the role module (`odrkit/roles/<role>.py`)

Structure, in order:

1. Module docstring stating: what the role reports on, whether it's
   synthetic or real, and the "no invented metrics" rule.
2. `ROLE = "<role>"`, `DEFAULT_PERIOD = "..."`.
3. **Data shapers** — one function per chart, named `shape_<thing>`, each
   returning a DataFrame **already in the exact column shape the target
   LIBRARY chart's `build()` expects** (check the chart's `__init__.py` for
   its default column names — e.g. `timeseries_multi` wants
   `date, series, value`). Prefer matching the chart's default column names
   over renaming via `cfg` where convenient, but `cfg` overrides work fine
   too (see `opsgov_incidents`'s `path_cols=('priority','state')` usage on
   `sunburst`).
4. `shape_kpis(period) -> list[KPI]` for the headline `kpi_row`.
5. `build_narrative(period) -> str` — a short paragraph computed ENTIRELY
   from data (every number and category name interpolated from a shaper
   call, nothing typed literally). This is what makes the executive-summary
   text trustworthy.
6. `build_registry(period) -> dict[str, ChartSpec]` — for each chart
   section, `dataclasses.replace(LIBRARY_CHART, id=<section_id>,
   sample=lambda: shape_fn(period))`. **Key by section id, not chart id** —
   the same library chart (e.g. `waterfall`) may be reused twice in one
   report for different purposes and would collide if keyed by chart id.
   The library's `build()` is reused completely unmodified; only `sample`
   (and `id`, for lookup) is rebound.
7. `build_report_spec(period) -> ReportSpec` — title/eyebrow/subtitle, then
   an ordered list of `SectionSpec`s: usually `section` (exec summary) →
   `kpi_row` → several `chart` sections → `SectionSpec(kind="disclaimer")`
   (auto-appended anyway via `appends_disclaimer=True` if you omit it, but
   being explicit is fine). Each chart `SectionSpec.cfg` supplies the
   library chart's keyword overrides (titles, mode, column-name overrides).

## 3. Pick charts deliberately, don't force all of them in

Run `uv run odr list-charts` and choose the ones that honestly fit your
data — reusing a chart is exactly what it's for (`corporate_finance` uses
`waterfall` once, `opsgov_incidents` uses it differently again). It's fine,
and often correct, to skip charts that don't have a real fit for this
domain's data (e.g. a 3-D surface rarely fits categorical ops data — don't
force one in just to "use more of the library").

## 4. Register the role

In `odrkit/cli.py`:

```python
from .roles import corporate_finance, opsgov_incidents, <your_role>

_ROLE_BUILDERS["<role>"] = (<your_role>.build_report_spec, <your_role>.build_registry)
_ROLE_DEFAULT_PERIOD["<role>"] = <your_role>.DEFAULT_PERIOD
```

If your role has NO local `data/<role>/` files (the real-data path), `odr
list-roles` still needs to show it — it already unions `data.list_roles()`
with `_ROLE_BUILDERS`, so registering here is sufficient; no further change
needed there.

## 5. Verify

```bash
uv run odr doctor                                              # role + all charts
uv run odr build-role --role <role> --format deck
uv run odr build-role --role <role> --format doc
```

Check the output HTML for `chart-error` (grep for it — the only expected
hit is the CSS rule itself, `.chart-error { ... }`; an actual error renders
as `[chart error: ...]` inline). Also sanity-check the report spec validates
cleanly and inspect a couple of shapers directly:

```bash
uv run python -c "
from odrkit.roles import <role> as r
spec = r.build_report_spec(r.DEFAULT_PERIOD)
registry = r.build_registry(r.DEFAULT_PERIOD)
print(spec.validate(registry=registry))   # must be []
print(r.build_narrative(r.DEFAULT_PERIOD))
"
```

## 6. Optional: Quarto

Only worth doing if the user wants an offline, self-contained, narrative-
authored version. Copy `quarto/corporate_finance/corporate_finance.qmd` as a
template:

- YAML front matter needs a `params: { period: "..." }` block AND a
  `#| tags: ["parameters"]` cell defining `period = "..."` as the FIRST code
  cell — without that tagged cell, papermill has nothing to inject `-P`
  overrides into and `period` is simply undefined at render time (this bit
  everyone the first time; don't skip it).
- `sys.path.insert(0, str(REPO_ROOT))` then import your role module and
  `from odrkit.charts import REGISTRY`; build figures the same way the role
  registry does (`REGISTRY["<chart_id>"].build(df, **cfg)`), letting the
  bare figure be the last expression in a cell to render it.
- Add a `quarto/_quarto.yml` project entry only if one doesn't already cover
  the new subdirectory (the existing project's `output-dir: ../artifacts`
  already mirrors subdirectory structure — a new `quarto/<role>/*.qmd` needs
  no new project config, just the `.qmd` itself).
- Render from INSIDE `quarto/<role>/`, never the repo root, with
  `QUARTO_PYTHON` pointed at `.venv` — see CLAUDE.md's Quarto section for
  the exact invocation and why running from the repo root silently produces
  a broken, un-embedded file.
