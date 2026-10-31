"""Census County Business Patterns -> data/raw/cbp_county_naics.parquet."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from extract._http import census_get, census_key, session
from extract._write import Row, write_parquet

CBP_YEAR = 2023  # latest available vintage
URL = f"https://api.census.gov/data/{CBP_YEAR}/cbp"
NAICS_CODES: tuple[str, ...] = ("7211", "7225", "622", "311", "3121")
GET_VARS = "ESTAB,EMP,EMP_N,EMPSZES,LFO,NAICS2017_LABEL,NAME"

COLUMNS: tuple[str, ...] = (
    "state",
    "county",
    "NAICS2017",
    "NAICS2017_LABEL",
    "NAME",
    "ESTAB",
    "EMP",
    "EMP_N",
    "EMPSZES",
    "LFO",
)


def rows_from_census(payload: list[list[str]], columns: Sequence[str]) -> list[Row]:
    """Map a Census JSON array (header row first) to `columns` by header name."""
    if not payload:
        return []
    header = payload[0]
    idx = {name: i for i, name in enumerate(header)}
    pick = [idx.get(c) for c in columns]
    return [
        tuple(
            (rec[i] if rec[i] not in ("", None) else None)
            if i is not None and i < len(rec)
            else None
            for i in pick
        )
        for rec in payload[1:]
    ]


def run(out_dir: Path) -> int:
    """Fetch every NAICS code and write the parquet; return rows written."""
    key = census_key()
    rows: list[Row] = []
    with session() as sess:
        for code in NAICS_CODES:
            params = {
                "get": GET_VARS,
                "for": "county:*",
                "in": "state:*",
                "NAICS2017": code,
                "key": key,
            }
            got = rows_from_census(census_get(URL, params, sess=sess), COLUMNS)
            if not got:
                raise RuntimeError(f"CBP returned no rows for NAICS {code}")
            rows.extend(got)
    n = write_parquet(rows, COLUMNS, out_dir / "cbp_county_naics.parquet")
    print(f"cbp_county_naics.parquet: {n} rows")
    return n


def main() -> None:
    run(Path("data/raw"))


if __name__ == "__main__":
    main()
