"""Load the committed synthetic fixtures into the ci DuckDB file (run from the repo root)."""

from pathlib import Path

from extract.load import load_raw

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    for name, n in load_raw(
        ROOT / "tests" / "fixtures", ROOT / "dbt" / "target" / "ci.duckdb"
    ).items():
        print(f"raw.{name}: {n} rows")
