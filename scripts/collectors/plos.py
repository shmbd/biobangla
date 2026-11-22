from __future__ import annotations

from typing import Any

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import ResearchType, StandardizedPaper


class PlosCollector(BaseCollector):
    """Official PLOS Search API collector (CC BY 4.0 Open Access)."""

    source_key = "plos"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        endpoint = self.config.get("endpoint", "https://api.plos.org/search")
        query = self.config.get("default_query", 'journal:"PLOS Biology"')
        rate = float(self.config.get("rate_limit_per_second", 1.0))
        rows = min(max_items, int(self.config.get("rows", 15)))

        payload = self.http.get_json(
            endpoint,
            params={
                "q": query,
                "fl": "id,journal,publication_date,article_type,author_display,title_display,abstract",
                "wt": "json",
                "rows": rows,
                "sort": "publication_date desc",
            },
            rate_limit_per_second=rate,
        )
        return self.parse_response(payload)

    def parse_response(self, payload: dict[str, Any]) -> list[StandardizedPaper]:
        docs = payload.get("response", {}).get("docs", [])
        papers: list[StandardizedPaper] = []

        for doc in docs:
            doi = normalize_doi(doc.get("id"))
            title = strip_markup(doc.get("title_display"))
            raw_abs = doc.get("abstract")
            if isinstance(raw_abs, list):
                abstract = strip_markup(" ".join(str(x) for x in raw_abs))
            else:
                abstract = strip_markup(str(raw_abs or ""))

            if not doi or not title or not abstract:
                continue

            article_type = str(doc.get("article_type", "")).lower()
            if "review" in article_type or "essay" in article_type:
                research_type: ResearchType = "review"
            elif "editorial" in article_type or "perspective" in article_type:
                research_type = "editorial"
            else:
                research_type = "original-research"

            authors = [
                str(a).strip() for a in (doc.get("author_display") or []) if str(a).strip()
            ] or ["PLOS Authors"]
            journal = strip_markup(doc.get("journal")) or "PLOS Biology"
            default_license = str(self.config.get("default_license", "CC BY 4.0"))

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    published_date=normalize_iso_date(doc.get("publication_date")),
                    source_url=f"https://doi.org/{doi}",
                    source_adapter=self.source_key,
                    doi=doi,
                    research_type=research_type,
                    peer_reviewed=True,
                    publication_status=(
                        "editorial-summary" if research_type == "editorial" else "peer-reviewed"
                    ),
                    license=default_license,
                    is_open_access=True,
                    provenance={"source": "PLOS API", "article_type": doc.get("article_type")},
                )
            )
        return papers
