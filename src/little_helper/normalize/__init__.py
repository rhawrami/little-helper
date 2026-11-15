"""Raw -> canonical tables. Pure functions of raw: delete canonical/ and rebuild at any time.

Canonical tables are partitioned by project:
    canonical/<table>/project=<id>/part-0.parquet
Read them all at once with polars or DuckDB, e.g.
    pl.scan_parquet(f"{LH_DATA_DIR}/canonical/commits/*/*.parquet", hive_partitioning=True)
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .. import paths, store

TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def ts(col: str) -> pl.Expr:
    """ISO-8601 with offset or trailing Z -> UTC datetime (null when unparseable)."""
    return (pl.col(col).str.replace(r"Z$", "+00:00")
            .str.to_datetime(TS_FORMAT, time_zone="UTC", strict=False))


def tz_minutes(col: str) -> pl.Expr:
    """UTC offset of an ISO timestamp in minutes (+05:30 -> 330)."""
    sign = pl.when(pl.col(col).str.extract(r"([+-])\d\d:?\d\d$", 1) == "-").then(-1).otherwise(1)
    hh = pl.col(col).str.extract(r"[+-](\d\d):?\d\d$", 1).cast(pl.Int32, strict=False)
    mm = pl.col(col).str.extract(r"[+-]\d\d:?(\d\d)$", 1).cast(pl.Int32, strict=False)
    return (sign * (hh * 60 + mm)).cast(pl.Int32)


def partition_path(table: str, project: str) -> Path:
    return paths.canonical_dir(table, f"project={project}", "part-0.parquet")


def write_partition(table: str, project: str, df: pl.DataFrame | None) -> int:
    path = partition_path(table, project)
    if df is None or df.height == 0:
        if path.exists():
            path.unlink()
        return 0
    store.write_parquet_atomic(df.drop("project", strict=False), path)
    return df.height


def read_table(table: str, project: str | None = None) -> pl.DataFrame:
    if project:
        path = partition_path(table, project)
        return pl.read_parquet(path).with_columns(pl.lit(project).alias("project")) if path.exists() else pl.DataFrame()
    files = sorted(paths.canonical_dir(table).glob("project=*/part-0.parquet"))
    if not files:
        return pl.DataFrame()
    return pl.read_parquet(files, hive_partitioning=True)
