"""ui.backend.doctor — re-exports odrkit.cli's doctor check logic.

No duplicated check logic: `GET /api/doctor` and `odr doctor` both call
`run_doctor_checks()` in odrkit/cli.py.
"""

from __future__ import annotations

from odrkit.cli import DoctorCheck, run_doctor_checks

__all__ = ["DoctorCheck", "run_doctor_checks"]
