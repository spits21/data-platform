---
name: odr-report
description: Drive the Ops Data Reporter (ODR) engine to build a deck, custom doc, or Quarto doc for a role and period, and to interpret the resulting output. Use when the user asks for a report, deck, business review, or reads on corporate finance, sales, marketing, data-center cost/capacity, or incidents/change-requests — anything that maps to an `odr build-role` invocation. Never hand-write HTML or hand-compute a figure; always run the engine and read numbers back from its output.
---

# odr-report — drive the ODR engine

You are the flexible interface over a deterministic engine (`odrkit`). Your
job is: interpret the user's plain-English ask, pick the right role/period/
format, run the `odr` CLI, and explain the output — using ONLY numbers you
read out of the generated report or the underlying data. You never hand-write
report HTML and you never hand-compute or guess a figure. If you state a
number, you must be able to point at where in the data or the rendered
output it came from.

## 1. Figure out what's being asked

Map the request to three things:

- **role** — which business domain. Run `uv run odr list-roles` if unsure;
  as of this writing:
  - `corporate_finance` — FP&A quarterly business review (synthetic data)
  - `opsgov_incidents` — Incident & Change Request governance review
    (**real data**, live Postgres — see step 4)
- **period** — a fiscal quarter like `2026-Q1`. If the user doesn't name one,
  use the role's default (see `uv run odr list-roles`, or read
  `_ROLE_DEFAULT_PERIOD` in `odrkit/cli.py`). To see what periods actually
  have data, call the role module's `available_periods()` — e.g.:
  ```bash
  uv run python -c "from odrkit.roles import corporate_finance as r; print(r.available_periods())"
  ```
  Do NOT guess a period that isn't in that list — `build-role` will raise a
  clear `ValueError` naming the valid ones if you do.
- **format** — `deck` (scroll-snap slides, PowerPoint-style) or `doc`
  (long-scroll document, Word-style). If the role has a Quarto `.qmd` under
  `quarto/<role>/`, that's a third option for an offline, self-contained,
  narrative-heavy render. Ask the user if it's genuinely ambiguous; default
  to `deck` for "show me" requests and `doc` for "write up" / "report on"
  requests.

## 2. Run the engine

```bash
uv sync                                                              # first time / after pulling
uv run odr doctor                                                    # confirm charts + roles are healthy
uv run odr build-role --role <role> --format <deck|doc> --period <period>
```

Omit `--out` to get the default path
(`artifacts/<role>/<role>_<format>_<period-no-dash>.html`); pass `--out` only
if the user wants a specific location. The command prints the path it wrote —
that path is the deliverable. Send it to the user (e.g. via a file-send tool)
rather than pasting HTML into chat.

### Quarto path (only for roles with a `.qmd`)

Check `quarto/<role>/` for a `.qmd` file. If present:

```bash
ODR="$(pwd)"                                    # from the repo root
cd quarto/<role>
QUARTO_PYTHON="$ODR/.venv/bin/python" uv run --project "$ODR" quarto render <role>.qmd \
  -P period:<period> --output <role>_quarto_<period-no-dash>.html
```

**Do not** run `quarto render` from the repo root — `--output` will escape
the project directory and produce a broken, un-embedded, un-themed file
(dead giveaway: ~80KB instead of several MB). Always `cd` into the `.qmd`'s
own directory first, per CLAUDE.md.

## 3. Read the output back — never invent a number

After building, if you need to describe what the report says (KPIs, trends,
narrative), get the numbers from the SAME shapers the report used, not by
eyeballing the HTML or guessing:

```bash
uv run python -c "
from odrkit.roles import <role> as r
print(r.build_narrative('<period>'))       # if the role has one
for k in r.shape_kpis('<period>'):
    print(k.label, k.value, k.sub)
"
```

Every role module's shapers (`odrkit/roles/<role>.py`) are plain functions
you can call directly to inspect exactly what fed a chart or KPI card. This
is the only legitimate source for any number you report to the user — the
whole point of the engine/skill split (see CLAUDE.md) is that figures come
from tested code, never from you reading a chart and estimating.

## 4. Real-data roles need credentials

`opsgov_incidents` (and any future real-data role — see
`data/DATA_DICTIONARY.md`) reads live from Postgres via
`odrkit.data.postgres_dsn_from_env`, which requires a repo-root `.env` (copy
`.env.example`, fill in real values — never hardcode credentials in code or
in chat). If `odr doctor` or `build-role` fails with
`MissingCredentialsError`, tell the user to populate `.env` — don't try to
work around it by hardcoding a connection string.

Real-data roles also render with `ReportSpec.synthetic=False` — no
"illustrative synthetic data" marker. Don't add synthetic-data caveats to
your own summary of a real-data role's output; it would be wrong.

## 5. Sanity checks before handing back a report

- `uv run odr doctor` should be clean before you build anything for a user
  who's hit an error — it isolates whether the problem is engine-wide
  (broken chart/theme) or specific to the role/period you're building.
- If `build-role` raises inside a specific chart, the deck/doc renderers
  degrade gracefully per-section (an inline `[chart error: ...]` box) rather
  than failing the whole report — check the output for `chart-error` if the
  user says "something looks off" rather than assuming the whole file is
  broken.
- If asked for numbers across multiple periods (e.g. "compare Q1 to Q2"),
  build/inspect each period separately — there is no cross-period diffing
  built into any role today; do the comparison yourself in Python from two
  calls to the shapers, not by rendering two reports and eyeballing them.

## What NOT to do

- Don't hand-write a chart or KPI value into HTML/Markdown yourself — always
  go through `odrkit`.
- Don't invent a period, role, or dataset name — enumerate via
  `list-roles`/`available_periods()` first.
- Don't paste large HTML blobs into chat — send the file.
- Don't silently fall back to a hardcoded DB connection string if `.env` is
  missing — surface the error and point the user at `.env.example`.
