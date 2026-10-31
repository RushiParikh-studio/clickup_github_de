from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import requests

from publish import clickup_doc

ENV = {
    "CLICKUP_TOKEN": "secret-token-value",
    "CLICKUP_TEAM_ID": "11",
    "CLICKUP_DOC_ID": "d-1",
    "CLICKUP_PAGE_ID": "p-2",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "o/r",
    "GITHUB_RUN_ID": "99",
}


def md(tmp_path: Path) -> Path:
    p = tmp_path / "top20.md"
    p.write_text("# Top\n", encoding="utf-8")
    return p


def test_put_payload(monkeypatch, tmp_path, capsys):
    put = MagicMock(return_value=MagicMock(status_code=200))
    monkeypatch.setattr(clickup_doc.requests, "put", put)
    assert clickup_doc.refresh(ENV, md(tmp_path)) is True
    assert put.call_args.args[0] == (
        "https://api.clickup.com/api/v3/workspaces/11/docs/d-1/pages/p-2"
    )
    assert put.call_args.kwargs["headers"]["Authorization"] == "secret-token-value"
    body = put.call_args.kwargs["json"]
    assert body["name"] == "DIN · PFAS top-20 counties"
    assert body["content_format"] == "text/md"
    assert body["content_edit_mode"] == "replace"
    run_url = "https://github.com/o/r/actions/runs/99"
    assert body["content"].startswith(f"Refreshed by deploy run {run_url} on ")
    assert body["content"].endswith("# Top\n")
    assert "secret-token-value" not in capsys.readouterr().out


def test_non_2xx_warns(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        clickup_doc.requests, "put", MagicMock(return_value=MagicMock(status_code=401))
    )
    assert clickup_doc.refresh(ENV, md(tmp_path)) is False
    out = capsys.readouterr().out
    assert out.startswith("::warning::") and "401" in out and "secret-token-value" not in out


def test_network_error_warns(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(clickup_doc.requests, "put", MagicMock(side_effect=requests.Timeout()))
    assert clickup_doc.refresh(ENV, md(tmp_path)) is False
    assert "::warning::" in capsys.readouterr().out


def test_missing_token_skips(monkeypatch, tmp_path, capsys):
    put = MagicMock()
    monkeypatch.setattr(clickup_doc.requests, "put", put)
    assert clickup_doc.refresh({**ENV, "CLICKUP_TOKEN": ""}, md(tmp_path)) is False
    put.assert_not_called()
    assert "::warning::" in capsys.readouterr().out
