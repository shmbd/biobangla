from __future__ import annotations

import logging
import os
from typing import Any

from scripts.collectors.base import BaseCollector
from scripts.collectors.biorxiv import BioRxivCollector
from scripts.collectors.crossref import CrossrefCollector
from scripts.collectors.europe_pmc import EuropePmcCollector
from scripts.collectors.plos import PlosCollector
from scripts.collectors.pubmed import PubMedCollector
from scripts.collectors.rss import RssFeedCollector
from scripts.http_client import PoliteHttpClient
from scripts.models import StandardizedPaper, utc_now_iso

logger = logging.getLogger("biobangla.collectors")

COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "europe_pmc": EuropePmcCollector,
    "pubmed": PubMedCollector,
    "crossref": CrossrefCollector,
    "biorxiv": BioRxivCollector,
    "plos": PlosCollector,
    "rss_feeds": RssFeedCollector,
}


def build_http_client(sources_config: dict[str, Any]) -> PoliteHttpClient:
    politeness = sources_config.get("politeness") or {}
    contact_email = os.getenv("PIPELINE_CONTACT_EMAIL", "").strip()
    timeout = int(
        os.getenv(
            "REQUEST_TIMEOUT_SECONDS",
            str(politeness.get("default_timeout_seconds", 25)),
        )
    )
    return PoliteHttpClient(
        user_agent=str(
            politeness.get(
                "user_agent",
                "biobangla-research-collector/1.0 (+https://biobangla.org/editorial-policy)",
            )
        ),
        contact_email=contact_email,
        timeout_seconds=timeout,
        max_retries=int(politeness.get("max_retries", 3)),
        backoff_base_seconds=float(politeness.get("backoff_base_seconds", 2.0)),
        respect_robots_txt=bool(politeness.get("respect_robots_txt", True)),
    )


def collect_from_all_sources(
    sources_config: dict[str, Any],
    only_sources: list[str] | None = None,
    max_per_source: int = 10,
) -> tuple[list[StandardizedPaper], dict[str, Any]]:
    http_client = build_http_client(sources_config)
    configured_sources = sources_config.get("sources") or {}

    all_papers: list[StandardizedPaper] = []
    source_stats: dict[str, Any] = {}

    for key, collector_cls in COLLECTOR_REGISTRY.items():
        if only_sources and key not in only_sources:
            continue
        cfg = configured_sources.get(key) or {}
        if not cfg.get("enabled", True):
            source_stats[key] = {"status": "skipped", "count": 0}
            continue

        collector = collector_cls(http_client=http_client, config=cfg)
        try:
            items = collector.collect(max_items=max_per_source)
            all_papers.extend(items)
            source_stats[key] = {"status": "ok", "count": len(items)}
            logger.info("Collected %d records from %s", len(items), key)
        except Exception as exc:
            # Resilient isolation: one API outage does not crash other collectors
            logger.error("Collector %s failed: %s", key, exc)
            source_stats[key] = {
                "status": "error",
                "count": 0,
                "error": str(exc),
            }

    report = {
        "collected_at": utc_now_iso(),
        "total_raw_records": len(all_papers),
        "sources": source_stats,
    }
    return all_papers, report
