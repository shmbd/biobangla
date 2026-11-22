from __future__ import annotations

import os
from typing import Any
import xml.etree.ElementTree as ET

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import PublicationStatus, ResearchType, StandardizedPaper


class PubMedCollector(BaseCollector):
    """Official NCBI E-utilities (PubMed) collector."""

    source_key = "pubmed"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        esearch = self.config.get(
            "esearch_endpoint",
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        )
        efetch = self.config.get(
            "efetch_endpoint",
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        )
        query = self.config.get("default_query", "biology[Title/Abstract]")
        api_key = os.getenv("NCBI_API_KEY", "").strip()
        rate = 8.0 if api_key else float(self.config.get("rate_limit_per_second", 3.0))
        retmax = min(max_items, int(self.config.get("max_results", 15)))

        common_params: dict[str, Any] = {
            "db": "pubmed",
            "tool": "biobangla",
            "email": self.http.contact_email or None,
            "api_key": api_key or None,
        }

        search_json = self.http.get_json(
            esearch,
            params={
                **common_params,
                "term": query,
                "retmode": "json",
                "sort": "pub_date",
                "retmax": retmax,
            },
            rate_limit_per_second=rate,
        )
        id_list = search_json.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        xml_payload = self.http.get_text(
            efetch,
            params={
                **common_params,
                "id": ",".join(id_list),
                "retmode": "xml",
            },
            rate_limit_per_second=rate,
        )
        return self.parse_efetch_xml(xml_payload)

    def parse_efetch_xml(self, xml_text: str) -> list[StandardizedPaper]:
        root = ET.fromstring(xml_text)
        papers: list[StandardizedPaper] = []

        for article_elem in root.findall(".//PubmedArticle"):
            pmid_elem = article_elem.find(".//MedlineCitation/PMID")
            pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else None

            title_elem = article_elem.find(".//Article/ArticleTitle")
            title = strip_markup("".join(title_elem.itertext())) if title_elem is not None else ""

            abstract_parts: list[str] = []
            for ab_elem in article_elem.findall(".//Article/Abstract/AbstractText"):
                text_part = strip_markup("".join(ab_elem.itertext()))
                if text_part:
                    abstract_parts.append(text_part)
            abstract = " ".join(abstract_parts).strip()

            if not title or not abstract or not pmid:
                continue

            journal_elem = article_elem.find(".//Article/Journal/Title")
            journal = (
                strip_markup(journal_elem.text)
                if journal_elem is not None and journal_elem.text
                else "PubMed Indexed Journal"
            )

            authors: list[str] = []
            for auth in article_elem.findall(".//Article/AuthorList/Author"):
                fore = auth.findtext("ForeName", "").strip()
                last = auth.findtext("LastName", "").strip()
                collective = auth.findtext("CollectiveName", "").strip()
                full = f"{fore} {last}".strip() or collective
                if full:
                    authors.append(full)
            if not authors:
                authors = ["PubMed Indexed Authors"]

            doi: str | None = None
            pmcid: str | None = None
            for aid in article_elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
                id_type = aid.attrib.get("IdType", "").lower()
                if id_type == "doi" and aid.text:
                    doi = normalize_doi(aid.text)
                elif id_type == "pmc" and aid.text:
                    pmcid = aid.text.strip()

            pub_types = [
                (pt.text or "").strip().lower()
                for pt in article_elem.findall(".//Article/PublicationTypeList/PublicationType")
            ]

            if any("preprint" in pt for pt in pub_types):
                research_type: ResearchType = "preprint"
                peer_reviewed = False
                pub_status: PublicationStatus = "preprint"
            elif any("review" in pt for pt in pub_types):
                research_type = "review"
                peer_reviewed = True
                pub_status = "peer-reviewed"
            elif any("editorial" in pt for pt in pub_types):
                research_type = "editorial"
                peer_reviewed = True
                pub_status = "editorial-summary"
            else:
                research_type = "original-research"
                peer_reviewed = True
                pub_status = "peer-reviewed"

            year = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Year") or "2026"
            month = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Month") or "01"
            day = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Day") or "01"
            month_map = {
                "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                "may": "05", "jun": "06", "jul": "07", "aug": "08",
                "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            }
            m_clean = month_map.get(month[:3].lower(), month.zfill(2) if month.isdigit() else "01")
            d_clean = day.zfill(2) if day.isdigit() else "01"
            iso_date = normalize_iso_date(f"{year}-{m_clean}-{d_clean}")

            source_url = (
                f"https://doi.org/{doi}"
                if doi
                else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    journal=journal,
                    published_date=iso_date,
                    source_url=source_url,
                    source_adapter=self.source_key,
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    research_type=research_type,
                    peer_reviewed=peer_reviewed,
                    publication_status=pub_status,
                    license="Metadata & Abstract via NCBI PubMed",
                    is_open_access=bool(pmcid),
                    provenance={"source": "PubMed", "pmid": pmid},
                )
            )
        return papers
