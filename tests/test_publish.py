from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pytest

from publish.top20 import fetch_top, render_dashboard, render_json, render_markdown, write_all

DDL = """create table main.fct_pfas_commercial_opportunity (
county_fips varchar, county_name varchar, state varchar, share_systems_over_4ppt double,
systems_tested bigint, systems_over_4ppt bigint, pop_county bigint, target_estab_total bigint,
opportunity_score double, rank_national bigint, rank_state bigint)"""


def make_db(path: Path, n: int = 25) -> Path:
    con = duckdb.connect(str(path))
    con.execute(DDL)
    for i in range(1, n + 1):
        name = "A&B <Test> County" if i == 3 else f"County {i}"
        pop = None if i == 5 else 10000 * i
        con.execute(
            "insert into main.fct_pfas_commercial_opportunity values (?,?,?,?,?,?,?,?,?,?,?)",
            [f"{i:05d}", name, "TX", 0.5, 10, 5, pop, 100 + i, 30.0 - i, i, i],
        )
    con.close()
    return path


@pytest.fixture
def rows(tmp_path: Path) -> list[dict[str, object]]:
    return fetch_top(make_db(tmp_path / "t.duckdb"))


def test_fetch_top_ordered(rows: list[dict[str, object]]) -> None:
    assert [r["rank_national"] for r in rows] == list(range(1, 21))


def test_fetch_top_missing_or_empty(tmp_path: Path) -> None:
    con = duckdb.connect(str(tmp_path / "e.duckdb"))
    con.close()
    with pytest.raises(SystemExit):
        fetch_top(tmp_path / "e.duckdb")
    with pytest.raises(SystemExit):
        fetch_top(make_db(tmp_path / "z.duckdb", n=0))


def test_markdown(rows: list[dict[str, object]]) -> None:
    md = render_markdown(rows, "now")
    assert "# Top 20 counties: PFAS × commercial opportunity" in md
    assert sum(1 for ln in md.splitlines() if ln.startswith("| ") and "County" in ln) == 20 + 1
    assert "2024" not in md


def test_json_roundtrip(rows: list[dict[str, object]]) -> None:
    doc = json.loads(render_json(rows, "now"))
    assert len(doc["rows"]) == 20
    assert isinstance(doc["rows"][0]["opportunity_score"], float)
    assert isinstance(doc["rows"][0]["rank_national"], int)
    assert doc["rows"][4]["pop_county"] is None


def test_html_static_and_escaped(rows: list[dict[str, object]]) -> None:
    page = render_dashboard(rows, "now")
    assert "<script src=" not in page
    assert "<link" not in page
    # plotly.js itself holds unused CDN strings (map tiles/icons); check everything else
    outside = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    assert "http" not in outside
    assert "A&amp;B &lt;Test&gt; County" in page
    assert "A&B <Test>" not in page


def test_write_all(rows: list[dict[str, object]], tmp_path: Path) -> None:
    out = tmp_path / "docs"
    paths = write_all(rows, out)
    assert sorted(p.name for p in out.iterdir()) == ["dashboard.html", "top20.json", "top20.md"]
    assert len(paths) == 3
