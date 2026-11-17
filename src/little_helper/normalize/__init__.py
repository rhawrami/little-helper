"""Raw -> canonical tables. Pure functions of raw: delete canonical/ and rebuild at any time.

Canonical tables are partitioned by project:
    canonical/<table>/project=<id>/part-0.parquet
Read them all at once with polars or DuckDB, e.g.
    pl.scan_parquet(f"{LH_DATA_DIR}/canonical/commits/*/*.parquet", hive_partitioning=True)
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .. import objects, paths, store

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
    """Write (or remove) one partition; with object storage it is uploaded, then dropped locally."""
    path = partition_path(table, project)
    if df is None or df.height == 0:
        path.unlink(missing_ok=True)
        objects.delete(path)
        return 0
    store.write_parquet_atomic(df.drop("project", strict=False), path)
    objects.settle(path)
    return df.height


def read_table(table: str, project: str | None = None) -> pl.DataFrame:
    """One table for one project, or for all projects. Reads from object storage as needed."""
    if project:
        files = objects.list_files(paths.canonical_dir(table, f"project={project}"), "part-0.parquet")
    else:
        files = objects.list_files(paths.canonical_dir(table), "project=*/part-0.parquet")
    if not files:
        return pl.DataFrame()
    with objects.local_copies(files) as fs:
        if project:
            return pl.read_parquet(fs).with_columns(pl.lit(project).alias("project"))
        return pl.read_parquet(fs, hive_partitioning=True)
