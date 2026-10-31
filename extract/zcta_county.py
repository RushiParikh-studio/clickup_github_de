"""Census 2020 ZCTA-to-county relationship file -> data/raw/zcta_county.parquet."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from extract._http import download
from extract._write import Row, parse_delimited, write_parquet

URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt"
CACHE_NAME = "tab20_zcta520_county20_natl.txt"

COLUMNS: tuple[str, ...] = (
    "GEOID_ZCTA5_20",
    "GEOID_COUNTY_20",
    "NAMELSAD_COUNTY_20",
    "AREALAND_ZCTA5_20",
    "AREALAND_PART",
    "AREAWATER_PART",
)


def parse_zcta(lines: Iterable[str]) -> Iterator[Row]:
    """Parse pipe-delimited lines, dropping rows with an empty GEOID_ZCTA5_20."""
    return (r for r in parse_delimited(lines, COLUMNS, "|") if r[0] is not None)


def run(out_dir: Path) -> int:
    """Download (cached) and convert; return rows written."""
    path = download(URL, out_dir / CACHE_NAME, timeout=300)
    with path.open(encoding="utf-8-sig", newline="") as fh:
        n = write_parquet(parse_zcta(fh), COLUMNS, out_dir / "zcta_county.parquet")
    print(f"zcta_county.parquet: {n} rows")
    return n


def main() -> None:
    run(Path("data/raw"))


if __name__ == "__main__":
    main()
