"""ACS 5-year county population -> data/raw/acs_population.parquet."""

from __future__ import annotations

from pathlib import Path

from extract._http import census_get, census_key, session
from extract._write import write_parquet
from extract.cbp import rows_from_census

ACS_YEAR = 2023
URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
COLUMNS: tuple[str, ...] = ("state", "county", "NAME", "B01003_001E")


def run(out_dir: Path) -> int:
    """Fetch county population and write the parquet; return rows written."""
    params = {
        "get": "NAME,B01003_001E",
        "for": "county:*",
        "in": "state:*",
        "key": census_key(),
    }
    with session() as sess:
        rows = rows_from_census(census_get(URL, params, sess=sess), COLUMNS)
    n = write_parquet(rows, COLUMNS, out_dir / "acs_population.parquet")
    print(f"acs_population.parquet: {n} rows")
    return n


def main() -> None:
    run(Path("data/raw"))


if __name__ == "__main__":
    main()
