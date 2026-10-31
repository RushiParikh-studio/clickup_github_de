"""Offline tests for the extract parsers and the key-safe Census client."""

from __future__ import annotations

import io
from typing import Any

import pytest

from extract import _http
from extract._http import KEY_ERROR, census_get
from extract.cbp import COLUMNS as CBP_COLUMNS
from extract.cbp import rows_from_census
from extract.ucmr5 import RESULT_COLUMNS, parse_results, parse_zipcodes
from extract.zcta_county import COLUMNS as ZCTA_COLUMNS
from extract.zcta_county import parse_zcta

FAKE_KEY = "not-a-real-value"


def _ucmr_text(rows: list[str], header: str | None = None) -> str:
    head = header or "\t".join(
        ["PWSID", "PWSName", "Size", "FacilityID", "SamplePointID", "SamplePointType",
         "CollectionDate", "SampleID", "Contaminant", "MRL", "Units",
         "AnalyticalResultsSign", "AnalyticalResultValue", "State"]
    )  # fmt: skip
    return "\r\n".join([head, *rows]) + "\r\n"


def test_ucmr_keeps_contract_columns_in_order_and_none_for_empty() -> None:
    row = "\t".join(
        ["ZZ0000001", "Invented Water", "S", "00001", "TP1", "EP", "9/27/2023",
         "S-1", "PFOA", "0.004", "\xb5g/L", "<", "", "TX"]
    )  # fmt: skip
    got = list(parse_results(io.StringIO(_ucmr_text([row]), newline="")))
    assert got == [
        ("ZZ0000001", "S", "00001", "TP1", "EP", "9/27/2023", "S-1", "PFOA", "0.004",
         "\xb5g/L", "<", None, "TX")
    ]  # fmt: skip
    assert len(got[0]) == len(RESULT_COLUMNS)


def test_ucmr_latin1_micro_sign_decoded() -> None:
    row = "\t".join(
        ["ZZ0000001", "n", "L", "1", "1", "EP", "1/2/2024", "s", "PFOS", "0.004", "\xb5g/L", "=",
         "0.01", "TX"]
    )  # fmt: skip
    data = _ucmr_text([row]).encode("latin-1")
    assert b"\xb5g/L" in data
    text = io.TextIOWrapper(io.BytesIO(data), encoding="latin-1", newline="")
    assert next(parse_results(text))[9] == "\xb5g/L"


def test_ucmr_missing_column_raises() -> None:
    with pytest.raises(ValueError, match="Contaminant"):
        list(parse_results(["PWSID\tSize\r\n", "ZZ0000001\tS\r\n"]))


def test_ucmr_columns_found_by_name_not_position() -> None:
    head = "State\tPWSID\tSize\tFacilityID\tSamplePointID\tSamplePointType\tCollectionDate\t"
    head += "SampleID\tContaminant\tMRL\tUnits\tAnalyticalResultsSign\tAnalyticalResultValue"
    row = "TX\tZZ0000002\tL\t1\t1\tEP\t1/2/2024\ts\tPFOA\t0.004\tu\t=\t0.01"
    got = list(parse_results([head, row]))
    assert got[0][0] == "ZZ0000002" and got[0][-1] == "TX"


def test_zip_keeps_leading_zeros() -> None:
    got = list(parse_zipcodes(["PWSID\tZIPCODE\r\n", "ZZ0000001\t06338\r\n"]))
    assert got == [("ZZ0000001", "06338")]


def test_zcta_strips_bom_and_drops_empty_zcta() -> None:
    cols = "OID|GEOID_ZCTA5_20|AREALAND_ZCTA5_20|GEOID_COUNTY_20|NAMELSAD_COUNTY_20|"
    cols += "AREALAND_PART|AREAWATER_PART"
    text = "\ufeff" + "\n".join(
        [cols, "1|00601|100|72001|Invented County|60|5", "2||0|01003|Other County|9|1"]
    )
    got = list(parse_zcta(text.split("\n")))
    assert got == [("00601", "72001", "Invented County", "100", "60", "5")]
    assert len(got[0]) == len(ZCTA_COLUMNS)


def test_rows_from_census_maps_by_header_and_fills_missing() -> None:
    payload = [
        ["NAME", "ESTAB", "NAICS2017", "state", "county"],
        ["Invented County, XX", "12", "622", "01", "003"],
    ]
    (row,) = rows_from_census(payload, CBP_COLUMNS)
    d = dict(zip(CBP_COLUMNS, row, strict=True))
    assert d["ESTAB"] == "12" and d["state"] == "01" and d["county"] == "003"
    assert d["EMP"] is None and d["LFO"] is None


def test_rows_from_census_empty_payload() -> None:
    assert rows_from_census([], CBP_COLUMNS) == []
    assert rows_from_census([["state", "county"]], CBP_COLUMNS) == []


class _Resp:
    def __init__(self, status: int, headers: dict[str, str] | None = None, body: Any = None):
        self.status_code = status
        self.headers = headers or {}
        self._body = body

    def json(self) -> Any:
        return self._body


class _Sess:
    def __init__(self, resp: _Resp) -> None:
        self.resp = resp
        self.kwargs: dict[str, Any] = {}

    def get(self, url: str, **kwargs: Any) -> _Resp:
        self.kwargs = kwargs
        return self.resp


URL = "https://api.census.gov/data/2023/cbp"
PARAMS = {"get": "ESTAB", "key": FAKE_KEY}


def test_census_get_redirect_raises_key_error() -> None:
    sess = _Sess(_Resp(302, {"Location": f"https://x/?key={FAKE_KEY}"}))
    with pytest.raises(RuntimeError) as ei:
        census_get(URL, PARAMS, sess=sess)
    assert str(ei.value) == KEY_ERROR
    assert sess.kwargs["allow_redirects"] is False


def test_census_get_key_header_raises_key_error() -> None:
    sess = _Sess(_Resp(200, {"X-DataWebAPI-KeyError": "bad"}, [["a"]]))
    with pytest.raises(RuntimeError, match="rejected the key"):
        census_get(URL, PARAMS, sess=sess)


def test_census_get_204_and_200() -> None:
    assert census_get(URL, PARAMS, sess=_Sess(_Resp(204))) == []
    ok = _Sess(_Resp(200, body=[["a"], ["1"]]))
    assert census_get(URL, PARAMS, sess=ok) == [["a"], ["1"]]


def test_census_get_errors_never_leak_key() -> None:
    for status in (400, 404, 500):
        with pytest.raises(RuntimeError) as ei:
            census_get(URL, PARAMS, sess=_Sess(_Resp(status)))
        msg = str(ei.value)
        assert FAKE_KEY not in msg and "key=" not in msg and str(status) in msg


def test_census_key_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _http.census_key()
