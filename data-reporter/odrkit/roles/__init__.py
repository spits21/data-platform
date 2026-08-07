"""odrkit.roles — one module per business domain.

Each role module is the single source of truth for one business area: period-
parameterized data shapers that feed the shared chart builders, plus
``build_report_spec(period)`` / ``build_registry(period)`` that
``cli.py``'s ``_ROLE_BUILDERS`` wires into ``odr build-role``.
"""
