"""Write the deterministic, fully synthetic CI fixtures to tests/fixtures/ (stdlib only).

Everything here is invented: PWSIDs, county names and numbers. Run from the repo root:
    uv run python scripts/make_fixtures.py
Output is byte-identical on every run (seeded RNG, fixed row order).

Design notes (the dbt tests and the hand-verification rely on these):
- ZCTA sample covers TX (county FIPS 48xxx) and NC (37xxx) only. The CA systems' ZIPs are
  deliberately absent from zcta_county.csv, so CA systems drop out of the exposure model, just
  like PO-box ZIPs with no ZCTA do. CA counties still appear in cbp/acs.
- ZCTAs 75003, 75004, 27004 span two counties with unequal land (larger wins); 75005 and 27006
  are exact ties (smallest county_fips wins). One row has an empty ZCTA (dropped by staging).
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

UCMR_COLS = [
    "PWSID", "Size", "FacilityID", "SamplePointID", "SamplePointType", "CollectionDate",
    "SampleID", "Contaminant", "MRL", "Units", "AnalyticalResultsSign",
    "AnalyticalResultValue", "State",
]  # fmt: skip
MRL = {"PFOA": "0.004", "PFOS": "0.004", "PFHxS": "0.003", "lithium": "9"}

# value None -> non-detect ('<', empty value); otherwise the literal text of the result.
Results = dict[str, list[str | None]]
SYSTEMS: list[tuple[str, str, str, Results]] = [
    # (pwsid, state, size, {contaminant: [values per sampling event]})
    (
        "TX9000001",
        "TX",
        "L",
        {"PFOA": ["0.004", None], "PFOS": ["0.0021", "0.0033"]},
    ),  # 0.004 counts
    ("TX9000002", "TX", "L", {"PFOA": [None, "0.0015"], "PFOS": ["0.02", "0.018"]}),
    ("TX9000003", "TX", "S", {"PFOA": ["0.0039", None], "PFOS": [None, None]}),  # 0.0039: no
    (
        "TX9000004",
        "TX",
        "S",
        {"PFOA": [None, None], "PFHxS": ["0.02", "0.012"]},
    ),  # wrong analyte
    ("TX9000005", "TX", "S", {"PFOS": ["0.0041", None], "lithium": ["14", "11"]}),
    ("TX9000006", "TX", "S", {"lithium": ["22", "18", None]}),  # lithium only: not tested
    ("NC9000001", "NC", "L", {"PFOA": ["0.005", "0.0046"], "PFOS": ["0.0072", None]}),
    ("NC9000002", "NC", "S", {"PFOA": [None, None], "PFOS": [None, None]}),
    ("NC9000003", "NC", "L", {"PFOA": ["0.0123", "0.0111"], "PFHxS": ["0.0042", None]}),
    ("NC9000004", "NC", "S", {"PFOA": ["0.0039", None], "PFOS": [None, "0.0012"]}),
    ("NC9000005", "NC", "S", {"PFOS": ["0.004", "0.0045"], "lithium": ["9.5", None]}),
    ("NC9000006", "NC", "L", {"PFOA": [None, None], "PFOS": ["0.0018", None]}),
    ("CA9000001", "CA", "L", {"PFOA": ["0.011", "0.009"], "PFOS": ["0.0066", None]}),
    ("CA9000002", "CA", "S", {"PFOA": [None, None], "PFOS": [None, "0.0021"]}),
    ("CA9000003", "CA", "L", {"PFOA": ["0.0055", None], "PFHxS": [None, "0.0031"]}),
]

ZIPS = [  # PWSID, ZIP
    ("TX9000001", "75001"), ("TX9000001", "75002"),  # two ZIPs, same county (48001)
    ("TX9000002", "75003"), ("TX9000002", "75004"),  # two counties (48002, 48003)
    ("TX9000003", "75005"),
    ("TX9000004", "75006"), ("TX9000004", "99999"),  # 99999: PO-box style, no ZCTA
    ("TX9000005", "75001"),
    ("TX9000006", "75004"),
    ("NC9000001", "27001"), ("NC9000001", "27002"),
    ("NC9000002", "27003"),
    ("NC9000003", "27004"),
    ("NC9000004", "27005"),
    ("NC9000005", "27006"),
    ("NC9000006", "27003"), ("NC9000006", "27005"),  # two counties (37002, 37003)
    ("CA9000001", "90001"), ("CA9000002", "90002"), ("CA9000003", "90003"),
]  # fmt: skip

ZCTA_COLS = [
    "GEOID_ZCTA5_20", "GEOID_COUNTY_20", "NAMELSAD_COUNTY_20",
    "AREALAND_ZCTA5_20", "AREALAND_PART", "AREAWATER_PART",
]  # fmt: skip
CN = {
    "48001": "Alder County", "48002": "Birch County", "48003": "Cedar County",
    "48004": "Dune County", "37001": "Elm County", "37002": "Fir County",
    "37003": "Gum County",
}  # fmt: skip
# (zcta, county, zcta_land, part_land); deliberately not sorted so ordering cannot help
ZCTA = [
    ("75001", "48001", 1000, 1000), ("75002", "48001", 800, 800),
    ("75003", "48003", 1000, 400), ("75003", "48002", 1000, 600),  # 48002 larger wins
    ("75004", "48002", 1000, 300), ("75004", "48003", 1000, 700),  # 48003 larger wins
    ("75005", "48004", 1000, 500), ("75005", "48002", 1000, 500),  # tie -> 48002
    ("75006", "48004", 900, 900),
    ("27001", "37001", 1000, 1000), ("27002", "37001", 800, 800),
    ("27003", "37002", 1000, 1000),
    ("27004", "37003", 1000, 450), ("27004", "37002", 1000, 550),  # 37002 larger wins
    ("27005", "37003", 700, 700),
    ("27006", "37003", 800, 400), ("27006", "37002", 800, 400),  # tie -> 37002
]  # fmt: skip

STATE_NAME = {"48": "Texas", "37": "North Carolina", "06": "California"}
COUNTIES = [*CN, "06001", "06002"]
CN["06001"] = "Hazel County"
CN["06002"] = "Ivy County"
NAICS = [
    ("7211", "Traveler accommodation"), ("7225", "Restaurants and other eating places"),
    ("622", "Hospitals"), ("311", "Food manufacturing"), ("3121", "Beverage manufacturing"),
]  # fmt: skip
MISSING = {("48004", "622"), ("37003", "3121"), ("37001", "311"), ("48002", "7211")}


def write(name: str, header: list[str], rows: list[list[str]]) -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    with (FIXTURES / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def ucmr_rows(rng: random.Random) -> list[list[str]]:
    rows: list[list[str]] = []
    start = date(2023, 3, 1)
    for n, (pwsid, state, size, results) in enumerate(SYSTEMS, start=1):
        events = 3  # values cycle across three sampling events
        for ev in range(events):
            d = start + timedelta(days=rng.randrange(0, 700))
            fac = f"{n:03d}{ev + 1}"
            sp = f"EP{ev + 1}"
            for cont, vals in results.items():
                v = vals[ev % len(vals)]
                rows.append([
                    pwsid, size, fac, sp, "EP", f"{d.month}/{d.day}/{d.year}",
                    f"S{n:03d}{ev + 1}{len(rows):03d}", cont, MRL[cont], "µg/L",
                    "<" if v is None else "=", "" if v is None else v, state,
                ])  # fmt: skip
    return rows


def cbp_rows(rng: random.Random) -> list[list[str]]:
    rows: list[list[str]] = []
    for fips in COUNTIES:
        st, co = fips[:2], fips[2:]
        name = f"{CN[fips]}, {STATE_NAME[st]}"
        for code, label in NAICS:
            if (fips, code) in MISSING:
                continue
            estab = rng.randrange(1, 60)
            emp, emp_n = str(estab * rng.randrange(5, 30)), "A"
            if (fips, code) == ("48003", "622"):
                emp, emp_n = "0", "D"  # suppressed employment
            rows.append([st, co, code, label, name, str(estab), emp, emp_n, "001", "001"])
        # extra size-class row: staging must ignore everything except EMPSZES=001
        rows.append([st, co, "7225", NAICS[1][1], name, "7", "40", "A", "210", "001"])
    return rows


def main() -> None:
    rng = random.Random(204)
    counts = {
        "ucmr5_all.csv": write("ucmr5_all.csv", UCMR_COLS, ucmr_rows(rng)),
        "ucmr5_zipcodes.csv": write(
            "ucmr5_zipcodes.csv", ["PWSID", "ZIPCODE"], [list(z) for z in ZIPS]
        ),
    }
    zrows = [[z, c, CN[c], str(lz), str(lp), "0"] for z, c, lz, lp in ZCTA]
    zrows.append(["", "48001", CN["48001"], "0", "250", "0"])  # empty ZCTA: dropped in staging
    counts["zcta_county.csv"] = write("zcta_county.csv", ZCTA_COLS, zrows)
    counts["cbp_county_naics.csv"] = write(
        "cbp_county_naics.csv",
        ["state", "county", "NAICS2017", "NAICS2017_LABEL", "NAME", "ESTAB", "EMP", "EMP_N",
         "EMPSZES", "LFO"],
        cbp_rows(rng),
    )  # fmt: skip
    acs = [
        [f[:2], f[2:], f"{CN[f]}, {STATE_NAME[f[:2]]}", str(rng.randrange(20000, 900000))]
        for f in COUNTIES
    ]
    counts["acs_population.csv"] = write(
        "acs_population.csv", ["state", "county", "NAME", "B01003_001E"], acs
    )
    for name, n in counts.items():
        print(f"{name}: {n} rows")


if __name__ == "__main__":
    main()
