"""Check the macro and stg_zcta_county SQL with plain jinja2 + in-memory DuckDB (no dbt run)."""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
import jinja2
import pytest

DBT = Path(__file__).resolve().parent.parent / "dbt"


def _render(template: str) -> str:
    """Render with the dbt functions stubbed: source/ref/config."""
    return (
        jinja2.Environment()
        .from_string(template)
        .render(
            source=lambda src, name: f"{src}.{name}",
            ref=lambda name: name,
            config=lambda **_: "",
        )
    )


def _score_sql(share: str, estab: str) -> str:
    macro = (DBT / "macros" / "opportunity_score.sql").read_text()
    return _render(macro + f"select {{{{ opportunity_score('{share}', '{estab}') }}}}")


def test_opportunity_score_matches_python() -> None:
    con = duckdb.connect()
    for share, estab in [(0.5, 99), (1.0, 3), (0.25, 0), (0.0, 50), (1.0, 123456)]:
        sql = _score_sql(str(share), str(estab))
        got = con.execute(sql).fetchone()
        assert got is not None
        assert got[0] == pytest.approx(share * math.log1p(estab))


def test_opportunity_score_null_handling() -> None:
    con = duckdb.connect()
    # null establishment count is treated as 0 -> score 0 when share is present
    assert con.execute(_score_sql("0.5", "null")).fetchone() == (0.0,)
    # null share gives a null score, not a fake 0
    assert con.execute(_score_sql("null", "10")).fetchone() == (None,)


def _stg_zcta(rows: list[tuple[str | None, str, str, str, str]]) -> list[tuple]:
    sql = _render((DBT / "models" / "staging" / "stg_zcta_county.sql").read_text())
    con = duckdb.connect()
    con.execute("create schema raw")
    con.execute(
        "create table raw.zcta_county (geoid_zcta5_20 varchar, geoid_county_20 varchar,"
        " namelsad_county_20 varchar, arealand_zcta5_20 varchar, arealand_part varchar)"
    )
    con.executemany("insert into raw.zcta_county values (?, ?, ?, ?, ?)", rows)
    return con.execute(f"select * from ({sql}) order by zcta5").fetchall()


def test_stg_zcta_county_selection() -> None:
    rows = _stg_zcta(
        [
            ("A", "48003", "Cedar County", "1000", "400"),
            ("A", "48002", "Birch County", "1000", "600"),  # larger part wins
            ("B", "48004", "Dune County", "1000", "500"),
            ("B", "48002", "Birch County", "1000", "500"),  # tie -> smallest county_fips
            ("C", "48001", "Alder County", "0", "10"),  # zero land: share is null
            (None, "48001", "Alder County", "1", "1"),  # NULL ZCTA excluded
            ("", "48001", "Alder County", "1", "1"),  # empty ZCTA excluded
        ]
    )
    assert [r[0] for r in rows] == ["A", "B", "C"]  # one row per ZCTA
    assert rows[0][1] == "48002" and rows[0][3] == pytest.approx(0.6)
    assert rows[1][1] == "48002" and rows[1][3] == pytest.approx(0.5)
    assert rows[2][1] == "48001" and rows[2][3] is None
