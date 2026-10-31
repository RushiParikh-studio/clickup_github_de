"""Publish the top counties from fct_pfas_commercial_opportunity as static files."""

from __future__ import annotations

import argparse
import html
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import plotly.io as pio

TABLE = "main.fct_pfas_commercial_opportunity"
TITLE = "Top 20 counties: PFAS × commercial opportunity"
CHART_TITLE = "Top 20 counties by PFAS × commercial opportunity"
METHOD = (
    "score = share of tested systems over 4 ppt × ln(1 + target establishments); "
    "establishments from the latest available County Business Patterns vintage; "
    "PFOA or PFOS result at or above 4 ppt"
)
CAVEATS = (
    "A system is counted in every county its ZIP codes reach.",
    "ZIP-to-county uses the county with the largest land-area share of the ZCTA.",
    "Only counties with at least 3 tested systems are ranked (dbt var min_systems_tested).",
    "Connecticut counties (2020 legacy counties) have no population or establishment match.",
    "This is a market-sizing signal, not a compliance measure.",
)
Row = dict[str, object]


def _clean(v: object) -> object:
    return None if isinstance(v, float) and not math.isfinite(v) else v


def fetch_top(db: Path, limit: int = 20) -> list[Row]:
    """Return the top ranked rows (rank_national not null); SystemExit if missing or none ranked."""
    con = duckdb.connect(str(db), read_only=True)
    try:
        try:
            cur = con.execute(
                f"select * from {TABLE} where rank_national is not null "
                "order by rank_national limit ?",
                [limit],
            )
        except duckdb.CatalogException as exc:
            raise SystemExit(f"error: table {TABLE} not found in {db}") from exc
        cols = [d[0] for d in cur.description]
        rows = [{c: _clean(v) for c, v in zip(cols, r, strict=True)} for r in cur.fetchall()]
    finally:
        con.close()
    if not rows:
        raise SystemExit(f"error: {TABLE} in {db} has no ranked counties")
    return rows


def _num(v: object) -> float:
    return float(v) if isinstance(v, int | float) else 0.0


def _int(v: object) -> str:
    return f"{int(_num(v)):,}" if v is not None else "n/a"


def _cells(r: Row) -> list[str]:
    return [
        str(r["rank_national"]),
        str(r["county_name"]),
        str(r["state"]),
        f"{_num(r['share_systems_over_4ppt']) * 100:.1f}%",
        f"{_int(r['systems_over_4ppt'])} / {_int(r['systems_tested'])}",
        _int(r["target_estab_total"]),
        _int(r["pop_county"]),
        f"{_num(r['opportunity_score']):.3f}",
        str(r["rank_state"]),
    ]


HEAD = [
    "National rank",
    "County",
    "State",
    "Share over 4 ppt",
    "Systems over / tested",
    "Target establishments",
    "Population",
    "Score",
    "State rank",
]


def render_markdown(rows: list[Row], generated_at: str) -> str:
    lines = [f"# {TITLE}", "", f"Generated {generated_at}.", "", f"Method: {METHOD}.", ""]
    lines.append("| " + " | ".join(HEAD) + " |")
    lines.append("|" + "|".join(["---"] * len(HEAD)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in _cells(r)) + " |")
    lines += ["", "## Caveats", ""] + [f"- {c}" for c in CAVEATS]
    return "\n".join(lines) + "\n"


def render_json(rows: list[Row], generated_at: str) -> str:
    doc = {"generated_at": generated_at, "method": METHOD, "rows": rows}
    return json.dumps(doc, indent=2, allow_nan=False) + "\n"


def render_dashboard(rows: list[Row], generated_at: str) -> str:
    labels = [f"{r['county_name']}, {r['state']}" for r in rows]
    hover = [
        f"<b>{html.escape(lab)}</b><br>Score {_num(r['opportunity_score']):.3f}"
        f"<br>Share over 4 ppt {_num(r['share_systems_over_4ppt']) * 100:.1f}%"
        f"<br>Target establishments {_int(r['target_estab_total'])}"
        f"<br>State rank {r['rank_state']}"
        for lab, r in zip(labels, rows, strict=True)
    ]
    fig = go.Figure(
        go.Bar(
            x=[_num(r["opportunity_score"]) for r in rows],
            y=labels,
            orientation="h",
            marker={"color": "#2a78d6"},
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        title=None,
        height=max(420, 26 * len(rows) + 120),
        margin={"l": 10, "r": 20, "t": 10, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#52514e", "size": 13},
        xaxis={"title": "Opportunity score", "gridcolor": "rgba(128,128,128,0.25)"},
        yaxis={"autorange": "reversed", "automargin": True},
        bargap=0.3,
        showlegend=False,
    )
    chart = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=True,
        div_id="chart",
        config={"displayModeBar": False, "responsive": True},
    )
    head = "".join(f'<th scope="col">{html.escape(h)}</th>' for h in HEAD)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in _cells(r)) + "</tr>" for r in rows
    )
    method = html.escape(METHOD)
    caveats = "".join(f"<li>{html.escape(c)}</li>" for c in CAVEATS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(CHART_TITLE)}</title>
<style>
:root{{color-scheme:light dark;--bg:#fcfcfb;--fg:#0b0b0b;--mut:#52514e;--line:#d9d8d3}}
@media (prefers-color-scheme:dark){{
:root{{--bg:#1a1a19;--fg:#f0efec;--mut:#c3c2b7;--line:#383835}}}}
body{{margin:0 auto;max-width:960px;padding:24px;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,sans-serif}}
h1{{font-size:1.4rem;margin:0 0 4px}} p,li{{color:var(--mut)}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:16px}}
th,td{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:right}}
th:nth-child(2),td:nth-child(2),th:nth-child(3),td:nth-child(3){{text-align:left}}
</style></head><body>
<h1>{html.escape(CHART_TITLE)}</h1>
<p>{method}. Generated {html.escape(generated_at)}.</p>
<figure role="img" aria-label="Horizontal bar chart of the top 20 counties by opportunity score; \
the table below lists the same values." style="margin:0">{chart}</figure>
<table><caption style="text-align:left;color:var(--mut)">Same data as the chart</caption>
<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<h2 style="font-size:1rem">Caveats</h2><ul>{caveats}</ul>
<script>
(function(){{var m=matchMedia("(prefers-color-scheme: dark)");
function f(){{Plotly.relayout("chart",{{"font.color":m.matches?"#c3c2b7":"#52514e"}});
Plotly.restyle("chart",{{"marker.color":m.matches?"#3987e5":"#2a78d6"}});}}
f();m.addEventListener("change",f);}})();
</script>
</body></html>
"""


def write_all(rows: list[Row], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    files = {
        "top20.md": render_markdown(rows, ts),
        "top20.json": render_json(rows, ts),
        "dashboard.html": render_dashboard(rows, ts),
    }
    paths = []
    for name, text in files.items():
        p = out_dir / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("docs"))
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    for p in write_all(fetch_top(a.db, a.limit), a.out):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
