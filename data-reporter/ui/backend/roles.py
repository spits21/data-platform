"""ui.backend.roles — role/period/format quick-pick data for the sidebar.

In-process only (no subprocess): imports odrkit.cli's own wiring dicts
directly, the same source of truth `build-role`/`list-roles` use, so this
can never drift from what the CLI actually supports.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from odrkit import cli as odr_cli
from odrkit import data as data_mod


@dataclass
class RoleInfo:
    role: str
    formats: list[str]
    default_period: str
    available_periods: list[str]
    data_kind: str  # "live" | "synthetic"
    error: str = ""  # set if available_periods() failed (e.g. a live-data role whose DB is unreachable)


def _module_for(fn) -> object:
    return sys.modules[fn.__module__]


def list_roles() -> list[RoleInfo]:
    all_roles = sorted(set(odr_cli._ROLE_BUILDERS) | set(odr_cli._ROLE_DASHBOARD_BUILDERS))
    out: list[RoleInfo] = []

    for role in all_roles:
        formats: list[str] = []
        spec_fn = None
        if role in odr_cli._ROLE_BUILDERS:
            formats.extend(["deck", "doc"])
            spec_fn = odr_cli._ROLE_BUILDERS[role][0]
        if role in odr_cli._ROLE_DASHBOARD_BUILDERS:
            formats.append("dashboard")
            if spec_fn is None:
                spec_fn = odr_cli._ROLE_DASHBOARD_BUILDERS[role][0]

        role_module = _module_for(spec_fn)
        datasets = data_mod.list_datasets(role)
        default_period = odr_cli._ROLE_DEFAULT_PERIOD[role]

        # A live-data role's available_periods() hits its database directly
        # (see opsgov_incidents.available_periods) — one role's outage
        # shouldn't take down the whole quick-pick list for every role.
        try:
            periods = role_module.available_periods()
            error = ""
        except Exception as exc:  # noqa: BLE001
            periods = [default_period]
            error = str(exc)[:300]

        out.append(
            RoleInfo(
                role=role,
                formats=formats,
                default_period=default_period,
                available_periods=periods,
                data_kind="synthetic" if datasets else "live",
                error=error,
            )
        )

    return out
