"""odrkit.report_spec — the declarative report format shared by deck + doc.

A report is DATA, not code: a ``ReportSpec`` is an ordered list of
``SectionSpec``. The same spec drives both ``odrkit.deck.build_deck`` and
``odrkit.doc.build_doc`` — nothing in this module knows how to render HTML;
it only describes *what* a report contains and validates that the
description is internally consistent (no duplicate ids, no unknown chart
ids, no unknown kinds) before any rendering is attempted.

Valid ``SectionSpec.kind`` values: ``title``, ``section``, ``chart``,
``chart_grid``, ``prose``, ``kpi_row``, ``disclaimer``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_KINDS: tuple[str, ...] = (
    "title",
    "section",
    "chart",
    "chart_grid",
    "prose",
    "kpi_row",
    "disclaimer",
)


@dataclass
class KPI:
    """One KPI card: a label, a formatted value, and an optional sub-caption
    (e.g. a delta like "+4.2% QoQ"). Values are pre-formatted strings —
    formatting is a role-module concern, not this module's."""

    label: str
    value: str
    sub: str = ""


@dataclass
class SectionSpec:
    """One section of a report. Compiles to one slide (deck) or one
    scroll-section (doc), except ``chart_grid`` which may render as several
    figures inside one section.

    ``id`` must be unique within a ``ReportSpec`` — it is the registry key a
    role's per-report chart registry is keyed by (NOT ``chart_id``, since the
    same chart, e.g. ``waterfall``, may be reused twice in one report for two
    different purposes).
    """

    kind: str
    id: str = ""
    title: str = ""
    eyebrow: str = ""
    subtitle: str = ""
    body_md: str = ""
    chart_id: str = ""
    chart_ids: list[str] = field(default_factory=list)
    cfg: dict = field(default_factory=dict)
    show_code: bool = False
    kpis: list[KPI] = field(default_factory=list)
    caption: str = ""
    css_class: str = ""

    def chart_id_list(self) -> list[str]:
        """Return the ordered list of chart/section ids this section renders.

        A ``chart`` section renders one id (``chart_id``, defaulting to
        ``id`` if unset); a ``chart_grid`` renders ``chart_ids`` (each
        defaulting to a positional fallback if empty is never valid — callers
        must set them explicitly).
        """
        if self.kind == "chart":
            return [self.chart_id or self.id]
        if self.kind == "chart_grid":
            return list(self.chart_ids)
        return []


@dataclass
class ReportSpec:
    """An ordered list of ``SectionSpec`` plus report-level identity/metadata.

    ``synthetic`` toggles the "illustrative synthetic data" marker in footers.
    ``appends_disclaimer`` auto-appends a disclaimer slide/section at the end
    unless the caller already included an explicit ``kind="disclaimer"``
    section.
    """

    title: str
    eyebrow: str = ""
    subtitle: str = ""
    id_badge: str = ""
    synthetic: bool = True
    appends_disclaimer: bool = True
    sections: list[SectionSpec] = field(default_factory=list)

    def validate(self, registry: dict | None = None) -> list[str]:
        """Return a list of human-readable validation issues (empty = OK).

        Checks, fail-fast and exhaustive (does not stop at the first issue):
        - duplicate ``SectionSpec.id`` values (ids are the per-report
          registry key; a collision means one chart silently shadows another)
        - unknown ``kind`` values
        - for ``chart``/``chart_grid`` sections, chart ids not present in
          ``registry`` (skipped if ``registry`` is None)
        """
        issues: list[str] = []

        seen_ids: dict[str, int] = {}
        for i, section in enumerate(self.sections):
            if section.kind not in VALID_KINDS:
                issues.append(
                    f"section[{i}]: unknown kind {section.kind!r} "
                    f"(expected one of {VALID_KINDS})"
                )
                continue

            if section.id:
                seen_ids[section.id] = seen_ids.get(section.id, 0) + 1

            if section.kind in ("chart", "chart_grid") and registry is not None:
                for cid in section.chart_id_list():
                    if not cid:
                        issues.append(
                            f"section[{i}] (id={section.id!r}): empty chart id "
                            f"in a {section.kind!r} section"
                        )
                    elif cid not in registry:
                        issues.append(
                            f"section[{i}] (id={section.id!r}): unknown "
                            f"chart_id {cid!r} (not in registry)"
                        )

        for sid, count in seen_ids.items():
            if count > 1:
                issues.append(f"duplicate section id {sid!r} used {count} times")

        return issues

    def validated(self, registry: dict | None = None) -> "ReportSpec":
        """Return ``self`` if valid, else raise ``ValueError`` with the issues."""
        issues = self.validate(registry=registry)
        if issues:
            raise ValueError(
                "ReportSpec is invalid:\n" + "\n".join(f"  - {i}" for i in issues)
            )
        return self
