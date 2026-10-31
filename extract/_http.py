"""HTTP helpers: retrying session, cached streaming download, key-safe Census client."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Getter(Protocol):
    """Anything with a requests-style `get` (a Session, or a fake in tests)."""

    def get(self, url: str, **kwargs: Any) -> Any: ...


# urllib3 logs retried URLs (WARNING/DEBUG); Census keys travel in the query string, so silence it.
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

KEY_ERROR = "Census API rejected the key (missing or invalid CENSUS_API_KEY)"


def session() -> requests.Session:
    """Session that retries transient failures on GET."""
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def download(url: str, dest: Path, *, timeout: float = 120) -> Path:
    """Stream `url` to `dest` via a temp file and atomic rename; reuse a non-empty cached file."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with session() as s, s.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with tmp.open("wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def census_key() -> str:
    """Return CENSUS_API_KEY from the environment (a repo-root .env is loaded if present)."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is not set (put it in the environment or a .env file)")
    return key


def census_get(url: str, params: dict[str, str], *, sess: Getter | None = None) -> list[list[str]]:
    """GET a Census Data API endpoint. Error messages never include the URL query or params."""
    path = urlsplit(url).path
    s = sess or session()
    try:
        r = s.get(url, params=params, allow_redirects=False, timeout=120)
    except requests.RequestException as exc:
        # str(exc) can embed the full URL (with the key), so report only the type.
        raise RuntimeError(f"Census request failed for {path}: {type(exc).__name__}") from None
    if 300 <= r.status_code < 400 or r.headers.get("X-DataWebAPI-KeyError"):
        raise RuntimeError(KEY_ERROR)
    if r.status_code == 204:
        return []
    if r.status_code != 200:
        raise RuntimeError(f"Census API returned HTTP {r.status_code} for {path}")
    try:
        payload = r.json()
    except ValueError:
        raise RuntimeError(f"Census API returned non-JSON for {path}") from None
    if not isinstance(payload, list):
        raise RuntimeError(f"Census API returned unexpected JSON for {path}")
    return payload
