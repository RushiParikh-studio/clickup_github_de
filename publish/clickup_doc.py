"""Refresh a ClickUp Doc page with docs/top20.md (ClickUp API v3, Edit a Page).

Never fails a deploy: a missing token or a non-2xx answer only emits a ::warning::.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

API = "https://api.clickup.com/api/v3/workspaces/{team}/docs/{doc}/pages/{page}"
PAGE_NAME = "DIN · PFAS top-20 counties"


def build_payload(
    markdown: str, env: dict[str, str], now: datetime | None = None
) -> dict[str, str]:
    now = now or datetime.now(UTC)
    run = "/".join(
        [
            env.get("GITHUB_SERVER_URL", "https://github.com"),
            env.get("GITHUB_REPOSITORY", "local"),
            "actions/runs",
            env.get("GITHUB_RUN_ID", "0"),
        ]
    )
    header = f"Refreshed by deploy run {run} on {now:%Y-%m-%d} (UTC)\n\n"
    return {
        "name": PAGE_NAME,
        "content": header + markdown,
        "content_format": "text/md",
        "content_edit_mode": "replace",
    }


def refresh(env: dict[str, str], src: Path = Path("docs/top20.md")) -> bool:
    """Return True on success; print a warning and return False otherwise."""
    token = env.get("CLICKUP_TOKEN", "")
    if not token:
        print("::warning::CLICKUP_TOKEN missing; ClickUp Doc refresh skipped")
        return False
    ids = {k: env.get(f"CLICKUP_{k.upper()}_ID", "") for k in ("team", "doc", "page")}
    if not all(ids.values()):
        print("::warning::CLICKUP_TEAM_ID, CLICKUP_DOC_ID or CLICKUP_PAGE_ID unset; skipped")
        return False
    if not src.is_file():
        print(f"::warning::{src} not found; ClickUp Doc refresh skipped")
        return False
    payload = build_payload(src.read_text(encoding="utf-8"), env)
    try:
        resp = requests.put(
            API.format(**ids),
            headers={"Authorization": token, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"::warning::ClickUp Doc refresh failed ({type(exc).__name__})")
        return False
    if not 200 <= resp.status_code < 300:
        print(f"::warning::ClickUp Doc refresh failed (HTTP {resp.status_code})")
        return False
    print(f"ClickUp Doc page refreshed (HTTP {resp.status_code})")
    return True


def main() -> None:
    refresh(dict(os.environ))
    sys.exit(0)


if __name__ == "__main__":
    main()
