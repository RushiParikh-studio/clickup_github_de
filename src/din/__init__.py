"""Helpers for the Agua US data ingestion demo."""

import re

_DIN = re.compile(r"DIN-\d+")


def parse_din_id(text: str | None) -> str | None:
    """Return the first DIN-n id found in text, else None."""
    if not text:
        return None
    match = _DIN.search(text)
    return match.group(0) if match else None
