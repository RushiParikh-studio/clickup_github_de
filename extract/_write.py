"""Shared helpers: header-by-name delimited parsing and batched all-VARCHAR parquet writing."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator, Sequence
from itertools import islice
from pathlib import Path

import duckdb
import pandas as pd

Row = tuple[str | None, ...]


def parse_delimited(
    lines: Iterable[str], columns: Sequence[str], delimiter: str, *, skip_blank: bool = True
) -> Iterator[Row]:
    """Yield rows holding `columns` (in that order), located by header name.

    Empty strings become None. Raises ValueError if the header lacks a required column.
    """
    reader = csv.reader(lines, delimiter=delimiter, quoting=csv.QUOTE_NONE)
    header = next(reader, None)
    if header is None:
        raise ValueError("empty input: no header row")
    names = [h.strip().lstrip("\ufeff") for h in header]
    missing = [c for c in columns if c not in names]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")
    idx = [names.index(c) for c in columns]
    for rec in reader:
        if skip_blank and not any(rec):
            continue
        n = len(rec)
        yield tuple((rec[i] or None) if i < n else None for i in idx)


def write_parquet(
    rows: Iterable[Row], columns: Sequence[str], dest: Path, *, batch: int = 200_000
) -> int:
    """Write rows as an all-VARCHAR parquet file in bounded batches; return the row count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    cols = ", ".join(f'"{c}" VARCHAR' for c in columns)
    it = iter(rows)
    total = 0
    try:
        with duckdb.connect() as con:
            con.execute(f"CREATE TABLE t ({cols})")
            while chunk := list(islice(it, batch)):
                df = pd.DataFrame(chunk, columns=list(columns), dtype=object)
                con.register("chunk_df", df)
                con.execute("INSERT INTO t SELECT * FROM chunk_df")
                con.unregister("chunk_df")
                total += len(chunk)
            p = str(tmp).replace("'", "''")
            con.execute(f"COPY t TO '{p}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return total
