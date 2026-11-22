from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import html
import re
from typing import Any

from scripts.http_client import PoliteHttpClient
from scripts.models import StandardizedPaper

DOI_PREFIX_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)
DOI_EXTRACT_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")
TAG_STRIP_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_doi(raw_doi: str | None) -> str | None:
    if not raw_doi:
        return None
    cleaned = DOI_PREFIX_RE.sub("", raw_doi.strip()).rstrip(".,;)")
    if cleaned.lower().startswith("doi:"):
        cleaned = cleaned[4:].strip()
    match = DOI_EXTRACT_RE.search(cleaned)
    return match.group(1).lower() if match else None


def strip_markup(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    unescaped = html.unescape(raw_text)
    without_tags = TAG_STRIP_RE.sub(" ", unescaped)
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def normalize_iso_date(raw_date: str | None) -> str:
    if not raw_date:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    candidate = raw_date.strip()
    # Try common ISO / RFC / YYYY-MM-DD formats
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m",
        "%Y",
    ):
        try:
            dt = datetime.strptime(candidate[:25] if "T" in candidate and "+" not in candidate else candidate, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    if re.match(r"^\d{4}-\d{2}-\d{2}", candidate):
        return candidate[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class BaseCollector(ABC):
    """Base interface for all research metadata source collectors."""

    source_key: str = "base"

    def __init__(self, http_client: PoliteHttpClient, config: dict[str, Any]) -> None:
        self.http = http_client
        self.config = config

    @abstractmethod
    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        """Collect standardized paper records from this source."""
        raise NotImplementedError
