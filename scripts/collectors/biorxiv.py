from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import StandardizedPaper


class BioRxivCollector(BaseCollector):
    """
    Official bioRxiv Preprint API collector.
    STRICT RULE: Every bioRxiv record MUST be marked peer_reviewed=False and publication_status='preprint'.
    """

    source_key = "biorxiv"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        base_endpoint = self.config.get(
            "endpoint", "https://api.biorxiv.org/details/biorxiv"
        ).rstrip("/")
        lookback_days = int(self.config.get("lookback_days", 7))
        rate = float(self.config.get("rate_limit_per_second", 1.0))

        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=lookback_days)
        interval_url = (
            f"{base_endpoint}/{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}/0"
        )

        payload = self.http.get_json(interval_url, rate_limit_per_second=rate)
        records = self.parse_response(payload)
        return records[:max_items]

    def parse_response(self, payload: dict[str, Any]) -> list[StandardizedPaper]:
        collection = payload.get("collection") or []
        papers: list[StandardizedPaper] = []

        for item in collection:
            title = strip_markup(item.get("title"))
            abstract = strip_markup(item.get("abstract"))
            doi = normalize_doi(item.get("doi"))
            if not title or not abstract or not doi:
                continue

            raw_authors = str(item.get("authors", ""))
            authors = [a.strip() for a in raw_authors.split(";") if a.strip()] or [
                "bioRxiv Preprint Authors"
            ]
            version = str(item.get("version", "1")).strip()
            license_val = str(item.get("license") or "bioRxiv Preprint License").strip()
            source_url = f"https://www.biorxiv.org/content/{doi}v{version}"

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal="bioRxiv (Preprint Server)",
                    published_date=normalize_iso_date(item.get("date")),
                    source_url=source_url,
                    source_adapter=self.source_key,
                    doi=doi,
                    research_type="preprint",
                    peer_reviewed=False,
                    publication_status="preprint",
                    license=license_val,
                    is_open_access="cc_by" in license_val.lower() or "cc0" in license_val.lower(),
                    provenance={
                        "source": "bioRxiv",
                        "biorxiv_category": item.get("category"),
                        "version": version,
                    },
                )
            )
        return papers
