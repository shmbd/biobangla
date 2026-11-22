from __future__ import annotations

from typing import Any

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import PublicationStatus, ResearchType, StandardizedPaper


class CrossrefCollector(BaseCollector):
    """Official Crossref REST API collector using the polite pool."""

    source_key = "crossref"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        endpoint = self.config.get("endpoint", "https://api.crossref.org/works")
        rate = float(self.config.get("rate_limit_per_second", 2.0))
        rows = min(max_items, int(self.config.get("rows", 15)))

        params: dict[str, Any] = {
            "query": self.config.get("query", "biology genomics microbiology"),
            "filter": self.config.get("filter", "has-abstract:true,type:journal-article"),
            "rows": rows,
            "sort": "published",
            "order": "desc",
            "mailto": self.http.contact_email or None,
        }

        payload = self.http.get_json(endpoint, params=params, rate_limit_per_second=rate)
        return self.parse_response(payload)

    def parse_response(self, payload: dict[str, Any]) -> list[StandardizedPaper]:
        items = payload.get("message", {}).get("items", [])
        papers: list[StandardizedPaper] = []

        for item in items:
            titles = item.get("title") or []
            title = strip_markup(titles[0]) if titles else ""
            abstract = strip_markup(item.get("abstract"))
            doi = normalize_doi(item.get("DOI"))
            if not title or not abstract or not doi:
                continue

            item_type = str(item.get("type", "")).lower()
            subtype = str(item.get("subtype", "")).lower()
            is_preprint = item_type == "posted-content" or subtype == "preprint"

            if is_preprint:
                research_type: ResearchType = "preprint"
                peer_reviewed = False
                pub_status: PublicationStatus = "preprint"
            else:
                research_type = "original-research"
                peer_reviewed = True
                pub_status = "peer-reviewed"

            authors: list[str] = []
            for author in item.get("author") or []:
                given = str(author.get("given", "")).strip()
                family = str(author.get("family", "")).strip()
                org = str(author.get("name", "")).strip()
                full = f"{given} {family}".strip() or org
                if full:
                    authors.append(full)
            if not authors:
                authors = ["Crossref Indexed Authors"]

            containers = item.get("container-title") or []
            journal = (
                strip_markup(containers[0])
                if containers
                else strip_markup(item.get("publisher")) or "Scientific Publication"
            )

            # Extract date parts
            date_parts = (
                item.get("published-online", {}).get("date-parts")
                or item.get("published-print", {}).get("date-parts")
                or item.get("created", {}).get("date-parts")
                or []
            )
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                parts = date_parts[0]
                yr = int(parts[0])
                mo = int(parts[1]) if len(parts) > 1 else 1
                dy = int(parts[2]) if len(parts) > 2 else 1
                iso_date = normalize_iso_date(f"{yr:04d}-{mo:02d}-{dy:02d}")
            else:
                iso_date = normalize_iso_date(None)

            licenses = item.get("license") or []
            license_url = str(licenses[0].get("URL", "")) if licenses else ""
            if "creativecommons.org/licenses/by/" in license_url:
                license_str = "CC BY"
                is_oa = True
            elif "creativecommons.org/publicdomain/zero" in license_url:
                license_str = "CC0"
                is_oa = True
            elif "creativecommons.org/licenses/by-sa" in license_url:
                license_str = "CC BY-SA"
                is_oa = True
            else:
                license_str = license_url or "Publisher Copyright"
                is_oa = False

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    published_date=iso_date,
                    source_url=f"https://doi.org/{doi}",
                    source_adapter=self.source_key,
                    doi=doi,
                    research_type=research_type,
                    peer_reviewed=peer_reviewed,
                    publication_status=pub_status,
                    license=license_str,
                    is_open_access=is_oa,
                    provenance={"source": "Crossref", "license_url": license_url},
                )
            )
        return papers
