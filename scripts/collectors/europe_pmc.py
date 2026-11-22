from __future__ import annotations

from typing import Any

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import PublicationStatus, ResearchType, StandardizedPaper


class EuropePmcCollector(BaseCollector):
    """Official Europe PMC REST API collector."""

    source_key = "europe_pmc"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        endpoint = self.config.get(
            "endpoint", "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        )
        query = self.config.get("default_query", "(OPEN_ACCESS:y) AND (SRC:MED)")
        rate = float(self.config.get("rate_limit_per_second", 2.0))
        page_size = min(max_items, int(self.config.get("page_size", 15)))

        payload = self.http.get_json(
            endpoint,
            params={
                "query": query,
                "resultType": "core",
                "format": "json",
                "pageSize": page_size,
            },
            rate_limit_per_second=rate,
        )
        return self.parse_response(payload)

    def parse_response(self, payload: dict[str, Any]) -> list[StandardizedPaper]:
        results = payload.get("resultList", {}).get("result", [])
        papers: list[StandardizedPaper] = []

        for item in results:
            title = strip_markup(item.get("title"))
            abstract = strip_markup(item.get("abstractText"))
            if not title or not abstract:
                continue

            doi = normalize_doi(item.get("doi"))
            pmid = str(item.get("pmid")).strip() if item.get("pmid") else None
            pmcid = str(item.get("pmcid")).strip() if item.get("pmcid") else None

            raw_source = str(item.get("source", "")).upper()
            pub_types_raw = item.get("pubTypeList", {}).get("pubType", [])
            if isinstance(pub_types_raw, str):
                pub_types = [pub_types_raw.lower()]
            else:
                pub_types = [str(pt).lower() for pt in pub_types_raw]

            is_preprint = raw_source == "PPR" or any("preprint" in pt for pt in pub_types)
            is_review = any("review" in pt for pt in pub_types)

            if is_preprint:
                research_type: ResearchType = "preprint"
                peer_reviewed = False
                pub_status: PublicationStatus = "preprint"
            elif is_review:
                research_type = "review"
                peer_reviewed = True
                pub_status = "peer-reviewed"
            else:
                research_type = "original-research"
                peer_reviewed = True
                pub_status = "peer-reviewed"

            author_str = item.get("authorString", "")
            authors = [a.strip() for a in author_str.split(",") if a.strip()] or [
                "Europe PMC Indexed Authors"
            ]

            journal = (
                strip_markup(item.get("journalTitle"))
                or strip_markup(item.get("bookOrReportDetails", {}).get("publisher"))
                or ("Preprint Server" if is_preprint else "Europe PMC Indexed Journal")
            )

            if doi:
                source_url = f"https://doi.org/{doi}"
            elif pmcid:
                source_url = f"https://europepmc.org/article/PMC/{pmcid}"
            elif pmid:
                source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            else:
                continue

            license_val = str(item.get("license") or "").strip() or (
                "Open Access (Europe PMC)" if item.get("isOpenAccess") == "Y" else "Unknown"
            )

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    published_date=normalize_iso_date(item.get("firstPublicationDate")),
                    source_url=source_url,
                    source_adapter=self.source_key,
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    research_type=research_type,
                    peer_reviewed=peer_reviewed,
                    publication_status=pub_status,
                    license=license_val,
                    is_open_access=(item.get("isOpenAccess") == "Y"),
                    provenance={"source": "Europe PMC", "id": item.get("id")},
                )
            )
        return papers
