"""Load raw Parquet (prod) or CSV fixtures (ci) into the `raw` schema of a DuckDB file."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

RAW_TABLES: tuple[str, ...] = (
    "ucmr5_all",
    "ucmr5_zipcodes",
    "zcta_county",
    "cbp_county_naics",
    "acs_population",
)


def _reader(path: Path) -> str:
    p = str(path).replace("'", "''")
    if path.suffix == ".parquet":
        return f"read_parquet('{p}')"
    return f"read_csv('{p}', header=true, delim=',', all_varchar=true, nullstr='')"


def load_raw(src: Path, db: Path, tables: tuple[str, ...] = RAW_TABLES) -> dict[str, int]:
    """Create or replace raw.<table> for each table; return row counts."""
    db.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(db)) as con:
        con.execute("create schema if not exists raw")
        for name in tables:
            candidates = [src / f"{name}.parquet", src / f"{name}.csv"]
            path = next((c for c in candidates if c.exists()), None)
            if path is None:
                raise FileNotFoundError(f"no {name}.parquet or {name}.csv in {src}")
            con.execute(f"create or replace table raw.{name} as select * from {_reader(path)}")
            row = con.execute(f"select count(*) from raw.{name}").fetchone()
            counts[name] = int(row[0]) if row else 0
    return counts


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True, help="directory with <table>.parquet|csv")
    ap.add_argument("--db", type=Path, required=True, help="DuckDB file to load into")
    args = ap.parse_args(argv)
    for name, n in load_raw(args.src, args.db).items():
        print(f"raw.{name}: {n} rows")


if __name__ == "__main__":
    main()
