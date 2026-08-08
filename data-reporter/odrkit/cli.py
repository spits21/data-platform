"""odrkit.cli — the ``odr`` command-line entry point.

Commands: ``doctor``, ``list-charts``, ``list-roles``, ``build-role``,
``viz-catalog``. ``_ROLE_BUILDERS`` is the wiring point for new roles: add an
entry here (plus ``_ROLE_DEFAULT_PERIOD``) to register a role module with
``build-role``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import click

from . import dashboard as dashboard_mod
from . import data as data_mod
from . import deck as deck_mod
from . import doc as doc_mod
from . import theme
from .charts import REGISTRY as CHART_REGISTRY
from .report_spec import ReportSpec, SectionSpec
from .roles import corporate_finance, opsgov_incidents

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACTS_DIR = _REPO_ROOT / "artifacts"

# role name -> (build_report_spec(period), build_registry(period)) — deck/doc
_ROLE_BUILDERS: dict[str, tuple] = {
    "corporate_finance": (
        corporate_finance.build_report_spec,
        corporate_finance.build_registry,
    ),
    "opsgov_incidents": (
        opsgov_incidents.build_report_spec,
        opsgov_incidents.build_registry,
    ),
}

# role name -> (build_dashboard_spec(period), build_registry(period), shape_dashboard_rows(period))
_ROLE_DASHBOARD_BUILDERS: dict[str, tuple] = {
    "opsgov_incidents": (
        opsgov_incidents.build_dashboard_spec,
        opsgov_incidents.build_registry,
        opsgov_incidents.shape_dashboard_rows,
    ),
}

_ROLE_DEFAULT_PERIOD: dict[str, str] = {
    "corporate_finance": corporate_finance.DEFAULT_PERIOD,
    "opsgov_incidents": opsgov_incidents.DEFAULT_PERIOD,
}


@click.group()
def main() -> None:
    """odr — the Ops Data Reporter CLI (deterministic report engine)."""


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@dataclass
class DoctorCheck:
    """One doctor check result. ``detail`` is a free-text note: on PASS it's
    shown parenthetically (e.g. period/dataset info); on FAIL it's the
    exception repr. Shared by the ``doctor`` Click command and the UI's
    ``GET /api/doctor`` endpoint so the check logic lives in exactly one
    place."""

    name: str
    passed: bool
    detail: str = ""


def run_doctor_checks() -> list[DoctorCheck]:
    """Run every doctor check and return the results (no printing/exit).

    Theme sanity, chart self-tests, then role + dashboard wiring checks.
    Synthetic roles have local files under ``data/<role>/``; real-data roles
    (see CLAUDE.md) have none and are checked by actually building the spec,
    which exercises the live connection (e.g. Postgres) they read from.
    """
    checks: list[DoctorCheck] = []

    try:
        import plotly.graph_objects as go

        fig = theme.apply_theme(go.Figure(go.Bar(x=[1], y=[1])), "bar")
        layout = fig.to_plotly_json()["layout"]
        assert layout.get("paper_bgcolor") == "rgba(0,0,0,0)"
        assert "colorway" in layout
        checks.append(DoctorCheck("theme.apply_theme", True))
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck("theme.apply_theme", False, repr(exc)))

    if not CHART_REGISTRY:
        checks.append(DoctorCheck("no charts registered under odrkit/charts/", False))
    for cid, spec in CHART_REGISTRY.items():
        try:
            spec.self_test()
            checks.append(DoctorCheck(f"chart: {cid}", True))
        except Exception as exc:  # noqa: BLE001
            checks.append(DoctorCheck(f"chart: {cid}", False, repr(exc)))

    for role, (spec_fn, registry_fn) in _ROLE_BUILDERS.items():
        period = _ROLE_DEFAULT_PERIOD.get(role)
        try:
            datasets = data_mod.list_datasets(role)
            source_note = f"datasets={datasets}" if datasets else "real-data (live query)"
            spec = spec_fn(period)
            registry = registry_fn(period)
            issues = spec.validate(registry=registry)
            assert not issues, issues
            checks.append(DoctorCheck(f"role: {role}", True, f"period={period}, {source_note}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(DoctorCheck(f"role: {role}", False, repr(exc)))

    for role, (dash_spec_fn, dash_registry_fn, rows_fn) in _ROLE_DASHBOARD_BUILDERS.items():
        period = _ROLE_DEFAULT_PERIOD.get(role)
        try:
            dash_spec = dash_spec_fn(period)
            dash_registry = dash_registry_fn(period)
            issues = dash_spec.validate(registry=dash_registry)
            assert not issues, issues
            rows = rows_fn(period)
            assert not rows.empty, "shape_dashboard_rows() returned an empty DataFrame"
            checks.append(DoctorCheck(f"dashboard: {role}", True, f"period={period}, rows={len(rows)}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(DoctorCheck(f"dashboard: {role}", False, repr(exc)))

    return checks


@main.command()
def doctor() -> None:
    """Run environment, theme, chart self-test, and data checks."""
    click.echo("== odrkit doctor ==")

    checks = run_doctor_checks()
    for c in checks:
        style = click.style("PASS", fg="green") if c.passed else click.style("FAIL", fg="red")
        if c.detail:
            click.echo(f"{style}  {c.name}" + (f" ({c.detail})" if c.passed else f": {c.detail}"))
        else:
            click.echo(f"{style}  {c.name}")

    click.echo("====================")
    if all(c.passed for c in checks):
        click.echo(click.style("doctor: all checks passed", fg="green", bold=True))
    else:
        click.echo(click.style("doctor: FAILURES ABOVE", fg="red", bold=True))
        sys.exit(1)


# ---------------------------------------------------------------------------
# list-charts / list-roles
# ---------------------------------------------------------------------------

@main.command("list-charts")
def list_charts() -> None:
    """List the registered chart library."""
    click.echo(f"{len(CHART_REGISTRY)} registered charts:\n")
    for cid, spec in CHART_REGISTRY.items():
        click.echo(f"  {cid:<22} {spec.family:<12} type={spec.chart_type:<12} {spec.interactions}")


@main.command("list-roles")
def list_roles() -> None:
    """List data roles: file-based roles under data/, plus any real-data
    role wired into build-role that has no local files (see CLAUDE.md)."""
    roles = sorted(set(data_mod.list_roles()) | set(_ROLE_BUILDERS))
    if not roles:
        click.echo("no roles found")
        return
    for role in roles:
        datasets = data_mod.list_datasets(role)
        formats = []
        if role in _ROLE_BUILDERS:
            formats.append("deck/doc")
        if role in _ROLE_DASHBOARD_BUILDERS:
            formats.append("dashboard")
        wired = f"wired ({', '.join(formats)})" if formats else "data only, not wired"
        source = f"[{wired}]" if datasets else f"[{wired}, real-data / live query]"
        click.echo(f"  {role:<20} {source}")
        for ds in datasets:
            click.echo(f"      - {ds}")


# ---------------------------------------------------------------------------
# build-role
# ---------------------------------------------------------------------------

@main.command("build-role")
@click.option("--role", required=True, type=click.Choice(sorted(set(_ROLE_BUILDERS) | set(_ROLE_DASHBOARD_BUILDERS))))
@click.option("--format", "fmt", required=True, type=click.Choice(["deck", "doc", "dashboard"]))
@click.option("--period", default=None, help="Defaults to the role's default period.")
@click.option("--out", "out_path", default=None, type=click.Path(), help="Output HTML path.")
def build_role(role: str, fmt: str, period: str | None, out_path: str | None) -> None:
    """Build a deck, doc, or dashboard for ROLE at PERIOD (default: the role's default period)."""
    period = period or _ROLE_DEFAULT_PERIOD[role]

    if out_path is None:
        out_path = _ARTIFACTS_DIR / role / f"{role}_{fmt}_{period.replace('-', '')}.html"

    if fmt == "dashboard":
        if role not in _ROLE_DASHBOARD_BUILDERS:
            raise click.ClickException(
                f"role {role!r} has no dashboard builder wired in _ROLE_DASHBOARD_BUILDERS"
            )
        dash_spec_fn, dash_registry_fn, rows_fn = _ROLE_DASHBOARD_BUILDERS[role]
        written = dashboard_mod.build_dashboard(
            dash_spec_fn(period), rows_fn(period), out_path, registry=dash_registry_fn(period)
        )
    else:
        if role not in _ROLE_BUILDERS:
            raise click.ClickException(f"role {role!r} has no deck/doc builder wired in _ROLE_BUILDERS")
        spec_fn, registry_fn = _ROLE_BUILDERS[role]
        spec = spec_fn(period)
        registry = registry_fn(period)
        if fmt == "deck":
            written = deck_mod.build_deck(spec, out_path, registry=registry)
        else:
            written = doc_mod.build_doc(spec, out_path, registry=registry)

    click.echo(f"wrote {written}")


# ---------------------------------------------------------------------------
# viz-catalog
# ---------------------------------------------------------------------------

@main.command("viz-catalog")
@click.option("--out", "out_path", default=None, type=click.Path())
def viz_catalog(out_path: str | None) -> None:
    """Render every registered chart (from its own sample()) + its source
    into one self-contained catalog page."""
    sections = []
    for cid, spec in CHART_REGISTRY.items():
        sections.append(
            SectionSpec(
                kind="chart",
                id=cid,
                chart_id=cid,
                title=spec.title,
                eyebrow=spec.family,
                subtitle=f"chart_type={spec.chart_type} · {spec.interactions}",
                show_code=True,
            )
        )

    report = ReportSpec(
        title="ODR Visualization Catalog",
        eyebrow="odrkit",
        subtitle=f"Every registered chart ({len(CHART_REGISTRY)}), rendered from its own sample() data, with source.",
        synthetic=True,
        appends_disclaimer=False,
        sections=sections,
    )

    out_path = Path(out_path) if out_path else _REPO_ROOT / "viz_catalog.html"
    written = doc_mod.build_doc(report, out_path)
    click.echo(f"wrote {written}")


# ---------------------------------------------------------------------------
# ui — local chat UI for business users (requires the "ui" extra)
# ---------------------------------------------------------------------------

@main.command("ui")
@click.option("--port", default=8110, show_default=True, type=int, help="Port to serve on.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host. Only change this if you understand the security implications — see ui/README.md.")
@click.option("--no-browser", is_flag=True, help="Don't automatically open a browser tab.")
def ui(port: int, host: str, no_browser: bool) -> None:
    """Start the local ODR chat UI (business-user front end for Claude Code).

    Requires the "ui" extra: `uv sync --extra ui`. Also requires the
    `claude` CLI to be installed and on PATH.
    """
    import os
    import shutil

    if shutil.which("claude") is None:
        raise click.ClickException(
            "The 'claude' CLI was not found on PATH. The ODR chat UI shells "
            "out to Claude Code — install it and make sure `claude` runs "
            "from a terminal, then try `odr ui` again."
        )

    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException(
            "The 'ui' extra isn't installed. Run `uv sync --extra ui` first."
        ) from exc

    ui_dir = _REPO_ROOT / "ui"
    if not ui_dir.exists():
        raise click.ClickException(f"UI directory not found at {ui_dir}")

    os.environ["ODR_UI_OPEN_BROWSER"] = "" if no_browser else "1"
    os.environ["ODR_UI_HOST"] = host
    os.environ["ODR_UI_PORT"] = str(port)

    click.echo(f"Starting ODR chat UI on http://{host}:{port} ...")
    uvicorn.run("backend.app:app", app_dir=str(ui_dir), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
