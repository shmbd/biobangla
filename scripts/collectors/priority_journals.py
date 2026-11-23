from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from scripts.collectors.base import BaseCollector
from scripts.collectors.europe_pmc import EuropePmcCollector
from scripts.collectors.oa_fulltext import enrich_with_open_access_fulltext
from scripts.models import StandardizedPaper

logger = logging.getLogger("biobangla.priority_journals")

MIN_PUBLICATION_DATE = "2026-01-01"


class PriorityJournalsCollector(BaseCollector):
    """
    Collects recent (>= 2026) peer-reviewed research and review articles from curated
    high-impact biological & microbiology journals via official Europe PMC APIs,
    and reads the full Open Access JATS XML article body whenever available.
    """

    source_key = "priority_journals"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        journals = self.config.get("journals") or []
        if not journals:
            return []

        rate = float(self.config.get("rate_limit_per_second", 2.0))
        endpoint = self.config.get(
            "endpoint", "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        )

        # Build ISSN map -> canonical journal display name & homepage
        issn_to_journal: dict[str, dict[str, Any]] = {}
        all_issns: list[str] = []
        for j in journals:
            for raw_issn in j.get("issns") or []:
                issn = str(raw_issn).strip()
                if issn:
                    all_issns.append(issn)
                    issn_to_journal[issn] = j

        if not all_issns:
            return []

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lookback_days = int(self.config.get("lookback_days", 60))
        window_start = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime(
            "%Y-%m-%d"
        )
        start_date = max(MIN_PUBLICATION_DATE, window_start)

        issn_clause = " OR ".join(f'ISSN:"{issn}"' for issn in all_issns)
        epmc_parser = EuropePmcCollector(self.http, self.config)

        collected: list[StandardizedPaper] = []

        # Pass 1: Prioritize Open Access articles in these 10 journals so we can read full article XML
        oa_query = (
            f"({issn_clause}) AND (OPEN_ACCESS:y) "
            f"AND (FIRST_PDATE:[{start_date} TO {today}]) sort_date:y"
        )
        # Pass 2: Also include latest high-impact articles/reviews across all 10 journals
        all_query = (
            f"({issn_clause}) AND (FIRST_PDATE:[{start_date} TO {today}]) sort_date:y"
        )

        seen_keys: set[str] = set()
        per_journal_counts: dict[str, int] = {}
        max_per_journal = max(2, max_items // 4)
        oa_quota = max(1, (max_items + 1) // 2)
        pass_quotas = [(oa_query, oa_quota), (all_query, max_items)]

        for query_str, target_total in pass_quotas:
            if len(collected) >= target_total:
                continue
            payload = self.http.get_json(
                endpoint,
                params={
                    "query": query_str,
                    "resultType": "core",
                    "format": "json",
                    "pageSize": max(15, max_items),
                },
                rate_limit_per_second=rate,
            )
            raw_results = payload.get("resultList", {}).get("result", [])
            raw_by_doi = {
                str(r.get("doi")).strip().lower(): r for r in raw_results if r.get("doi")
            }
            raw_by_pmid = {
                str(r.get("pmid")).strip(): r for r in raw_results if r.get("pmid")
            }
            parsed_batch = epmc_parser.parse_response(payload)

            # Match ISSN back to clean canonical journal name
            for paper in parsed_batch:
                if paper.published_date < MIN_PUBLICATION_DATE:
                    continue
                dedup_key = (paper.doi or paper.pmid or paper.title).lower()
                if dedup_key in seen_keys:
                    continue

                raw_item = (
                    (raw_by_doi.get(paper.doi.lower()) if paper.doi else None)
                    or (raw_by_pmid.get(paper.pmid) if paper.pmid else None)
                    or {}
                )
                j_info = (raw_item.get("journalInfo") or {}).get("journal") or {}
                matched_meta = (
                    issn_to_journal.get(str(j_info.get("issn") or ""))
                    or issn_to_journal.get(str(j_info.get("essn") or ""))
                )
                if matched_meta:
                    paper.journal = str(matched_meta["name"])
                    paper.provenance["journal_homepage"] = matched_meta.get("url")
                    if matched_meta.get("default_category"):
                        paper.category = str(matched_meta["default_category"])
                    if matched_meta.get("default_research_type") == "review":
                        paper.research_type = "review"

                if per_journal_counts.get(paper.journal, 0) >= max_per_journal:
                    continue

                paper.source_adapter = self.source_key
                paper.provenance["priority_journal"] = True
                per_journal_counts[paper.journal] = per_journal_counts.get(paper.journal, 0) + 1

                # Read full Open Access article XML when available!
                if paper.is_open_access or paper.pmcid:
                    enrich_with_open_access_fulltext(
                        paper, self.http, rate_limit_per_second=rate
                    )

                seen_keys.add(dedup_key)
                collected.append(paper)
                if len(collected) >= target_total:
                    break

        return collected
