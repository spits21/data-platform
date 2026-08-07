"""odrkit.data — data access for role modules: duckdb-backed parquet/CSV for
the synthetic roles, plus a duckdb-postgres-scanner path for the real-data
roles (``opsgov_incidents``, ``data_center_capacity`` — see CLAUDE.md).

Every SYNTHETIC role's datasets live at ``data/<role>/<dataset>.{parquet,csv}``
(repo root, resolved relative to this file so it works regardless of cwd).
REAL-data roles have no local file under ``data/`` — they query live via
``query_postgres`` / ``query_postgres_cached``, which attach a Postgres
database through duckdb's ``postgres`` extension (no extra Python DB driver
dependency).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _REPO_ROOT / "data"

# Load repo-root .env once at import time (never overrides an already-set
# real env var, e.g. one exported by CI). .env itself is gitignored; copy
# .env.example to .env and fill in real credentials to run real-data roles.
load_dotenv(_REPO_ROOT / ".env")


def _resolve(role: str, dataset: str) -> Path:
    role_dir = DATA_DIR / role
    for ext in ("parquet", "csv"):
        path = role_dir / f"{dataset}.{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(
        f"no dataset {dataset!r} for role {role!r} under {role_dir} "
        f"(looked for .parquet, .csv)"
    )


def list_roles() -> list[str]:
    """Return role names — subdirectories of data/ containing >=1 dataset."""
    if not DATA_DIR.exists():
        return []
    return sorted(
        p.name for p in DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")
    )


def list_datasets(role: str) -> list[str]:
    role_dir = DATA_DIR / role
    if not role_dir.exists():
        return []
    return sorted(
        {p.stem for p in role_dir.iterdir() if p.suffix in (".parquet", ".csv")}
    )


def load(role: str, dataset: str) -> pd.DataFrame:
    """Load one dataset fresh via duckdb (no caching). Safe to mutate."""
    path = _resolve(role, dataset)
    if path.suffix == ".parquet":
        query = "SELECT * FROM read_parquet(?)"
    else:
        query = "SELECT * FROM read_csv_auto(?)"
    return duckdb.sql(query, params=[str(path)]).df()


@lru_cache(maxsize=None)
def _load_cached_impl(role: str, dataset: str) -> pd.DataFrame:
    return load(role, dataset)


def load_cached(role: str, dataset: str) -> pd.DataFrame:
    """Load one dataset, cached process-wide.

    Callers MUST ``.copy()`` before mutating the returned frame — it is
    shared across every caller in the process.
    """
    return _load_cached_impl(role, dataset)


# ---------------------------------------------------------------------------
# Postgres (real-data roles). Uses duckdb's `postgres` extension (auto-
# installed on first use, then cached by duckdb — no psycopg2/sqlalchemy
# dependency needed). Credentials NEVER live in source: they come from the
# environment, populated from a gitignored `.env` file (see .env.example)
# via python-dotenv, loaded once at module import above.
# ---------------------------------------------------------------------------

class MissingCredentialsError(RuntimeError):
    """Raised when Postgres credentials are not configured (no .env, no env vars)."""


def postgres_dsn_from_env(prefix: str = "ODR_PG") -> str:
    """Build a ``postgresql://`` DSN from environment variables.

    Reads ``{prefix}_DSN`` if set (a full connection string escape hatch),
    else composes one from ``{prefix}_HOST``, ``{prefix}_PORT``,
    ``{prefix}_DATABASE``, ``{prefix}_USER``, ``{prefix}_PASSWORD``. Raises
    ``MissingCredentialsError`` — not a silent hardcoded fallback — if
    neither is fully populated. Populate these via a repo-root ``.env``
    (copy ``.env.example``) or real environment variables.
    """
    full_dsn = os.environ.get(f"{prefix}_DSN")
    if full_dsn:
        return full_dsn

    host = os.environ.get(f"{prefix}_HOST")
    port = os.environ.get(f"{prefix}_PORT", "5432")
    database = os.environ.get(f"{prefix}_DATABASE")
    user = os.environ.get(f"{prefix}_USER")
    password = os.environ.get(f"{prefix}_PASSWORD")

    missing = [
        f"{prefix}_{name}"
        for name, val in [("HOST", host), ("DATABASE", database), ("USER", user), ("PASSWORD", password)]
        if not val
    ]
    if missing:
        raise MissingCredentialsError(
            f"Postgres credentials not configured: missing {', '.join(missing)} "
            f"(or {prefix}_DSN). Copy .env.example to .env at the repo root and fill in "
            f"real values, or export the environment variables directly."
        )

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def query_postgres(dsn: str, query: str) -> pd.DataFrame:
    """Run ``query`` against a Postgres database and return the result.

    ``dsn`` is a standard ``postgresql://user:pass@host:port/db`` URI. Opens
    a fresh duckdb connection and ATTACHes Postgres READ_ONLY for this one
    query — safe to call repeatedly (see ``query_postgres_cached`` for a
    process-cached variant that avoids re-hitting the database).
    """
    con = duckdb.connect()
    con.execute("INSTALL postgres")
    con.execute("LOAD postgres")
    # ATTACH's DSN is a literal, not a prepared-statement parameter position
    # duckdb's parser accepts — escape single quotes and inline it.
    escaped_dsn = dsn.replace("'", "''")
    con.execute(f"ATTACH '{escaped_dsn}' AS pg (TYPE postgres, READ_ONLY)")
    return con.execute(query).df()


@lru_cache(maxsize=None)
def _query_postgres_cached_impl(dsn: str, query: str) -> pd.DataFrame:
    return query_postgres(dsn, query)


def query_postgres_cached(dsn: str, query: str) -> pd.DataFrame:
    """Run ``query`` against Postgres, cached process-wide by (dsn, query).

    Callers MUST ``.copy()`` before mutating the returned frame — it is
    shared across every caller in the process. Real-data roles read a live
    database, so results reflect current DB state as of process start (or
    the first call); this is expected — determinism here means "same code
    path," not "frozen data," per CLAUDE.md's real-data-role distinction.
    """
    return _query_postgres_cached_impl(dsn, query)
