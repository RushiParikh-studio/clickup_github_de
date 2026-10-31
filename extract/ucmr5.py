"""EPA UCMR 5 occurrence data -> data/raw/ucmr5_all.parquet and ucmr5_zipcodes.parquet."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from extract._http import download
from extract._write import Row, parse_delimited, write_parquet

URL = "https://www.epa.gov/system/files/other-files/2023-08/ucmr5-occurrence-data.zip"
ZIP_NAME = "ucmr5-occurrence-data.zip"

RESULT_COLUMNS: tuple[str, ...] = (
    "PWSID",
    "Size",
    "FacilityID",
    "SamplePointID",
    "SamplePointType",
    "CollectionDate",
    "SampleID",
    "Contaminant",
    "MRL",
    "Units",
    "AnalyticalResultsSign",
    "AnalyticalResultValue",
    "State",
)
ZIP_COLUMNS: tuple[str, ...] = ("PWSID", "ZIPCODE")


def parse_results(lines: Iterable[str]) -> Iterator[Row]:
    """Parse UCMR5_All.txt text lines (tab-delimited, header row) into contract rows."""
    return parse_delimited(lines, RESULT_COLUMNS, "\t")


def parse_zipcodes(lines: Iterable[str]) -> Iterator[Row]:
    """Parse UCMR5_ZIPCodes.txt text lines; ZIPCODE stays a string (leading zeros kept)."""
    return parse_delimited(lines, ZIP_COLUMNS, "\t")


def run(out_dir: Path) -> int:
    """Download (cached) and convert both files; return total rows written."""
    zpath = download(URL, out_dir / ZIP_NAME, timeout=600)
    total = 0
    jobs = (
        ("UCMR5_All.txt", parse_results, RESULT_COLUMNS, "ucmr5_all.parquet"),
        ("UCMR5_ZIPCodes.txt", parse_zipcodes, ZIP_COLUMNS, "ucmr5_zipcodes.parquet"),
    )
    with zipfile.ZipFile(zpath) as zf:
        for member, parser, cols, outname in jobs:
            with zf.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                n = write_parquet(parser(text), cols, out_dir / outname)
            print(f"{outname}: {n} rows")
            total += n
    return total


def main() -> None:
    run(Path("data/raw"))


if __name__ == "__main__":
    main()
