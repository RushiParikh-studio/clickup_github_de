"""CLI: uv run python -m extract [--only ucmr5,zcta,cbp,acs] [--out data/raw] [--skip-census]."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

import duckdb

from extract import acs, cbp, ucmr5, zcta_county
from extract._http import census_key

SOURCES: dict[str, Callable[[Path], int]] = {
    "ucmr5": ucmr5.run,
    "zcta": zcta_county.run,
    "cbp": cbp.run,
    "acs": acs.run,
}
CENSUS = ("cbp", "acs")
# Sanity floors (full national files are far larger); a truncated source must not reach prod.
MIN_ROWS: dict[str, dict[str, int]] = {
    "ucmr5": {"ucmr5_all": 1_000_000, "ucmr5_zipcodes": 20_000},
    "zcta": {"zcta_county": 30_000},
    "cbp": {"cbp_county_naics": 5_000},
    "acs": {"acs_population": 3_000},
}


def check_min_rows(out: Path, source: str) -> list[str]:
    """Return problems for outputs of `source` below their row floor."""
    problems: list[str] = []
    with duckdb.connect() as con:
        for table, floor in MIN_ROWS[source].items():
            path = str(out / f"{table}.parquet").replace("'", "''")
            row = con.execute(f"select count(*) from read_parquet('{path}')").fetchone()
            n = int(row[0]) if row else 0
            if n < floor:
                problems.append(f"{table}: {n} rows < floor {floor}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="extract", description=__doc__)
    ap.add_argument("--only", default=",".join(SOURCES), help="comma list of sources")
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    ap.add_argument("--skip-census", action="store_true", help="skip cbp and acs (no key)")
    ap.add_argument("--no-guards", action="store_true", help="skip minimum row-count checks")
    args = ap.parse_args(argv)

    chosen = [s.strip() for s in args.only.split(",") if s.strip()]
    unknown = [s for s in chosen if s not in SOURCES]
    if unknown:
        ap.error(f"unknown source(s): {', '.join(unknown)}; choose from {', '.join(SOURCES)}")
    if args.skip_census:
        chosen = [s for s in chosen if s not in CENSUS]
    if any(s in CENSUS for s in chosen):
        try:
            census_key()
        except RuntimeError as exc:
            print(f"error: {exc}; set it or pass --skip-census", file=sys.stderr)
            return 2
    for name in chosen:
        t0 = time.monotonic()
        n = SOURCES[name](args.out)
        print(f"[{name}] {n} rows in {time.monotonic() - t0:.1f}s")
        if not args.no_guards and (problems := check_min_rows(args.out, name)):
            print("error: " + "; ".join(problems), file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
