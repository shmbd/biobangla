from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.collectors.orchestrator import collect_from_all_sources
from scripts.config_loader import load_all_configs
from scripts.processors.classifier import classify_paper
from scripts.processors.deduplicator import ExistingCorpusIndex, deduplicate_papers
from scripts.processors.license_checker import evaluate_license


def main() -> int:
    parser = argparse.ArgumentParser(
        description="biobangla — Collect, deduplicate, classify, and verify open biological research metadata."
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="Optional subset of source keys (e.g., europe_pmc plos biorxiv).",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=int(os.getenv("MAX_CANDIDATES_PER_RUN", "10")),
        help="Maximum items to request per source.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "state" / "candidates" / "latest_candidates.json",
        help="Path to write standardized candidate batch JSON.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    configs = load_all_configs()
    articles_dir = REPO_ROOT / "content" / "articles"
    corpus_index = ExistingCorpusIndex.from_articles_dir(articles_dir)

    raw_papers, collection_report = collect_from_all_sources(
        sources_config=configs["sources"],
        only_sources=args.sources,
        max_per_source=args.max_per_source,
    )

    unique_papers, skipped_duplicates = deduplicate_papers(
        raw_papers, existing_index=corpus_index
    )

    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    min_pub_date = str(configs["sources"].get("min_publication_date", "2026-01-01"))
    rolling_floor = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    oldest_allowed_iso = max(min_pub_date, rolling_floor)

    ready_papers = []
    rejected_non_bio = 0
    rejected_stale_or_bogus_date = 0
    for paper in unique_papers:
        # Strict rule: never accept articles published before 2026-01-01 or in the future
        if (
            paper.published_date < min_pub_date
            or paper.published_date < oldest_allowed_iso
            or paper.published_date > today_iso
        ):
            rejected_stale_or_bogus_date += 1
            continue
        classify_paper(paper, configs["categories"])
        if not paper.is_biological:
            rejected_non_bio += 1
            continue
        evaluate_license(paper, configs["editorial_rules"])
        ready_papers.append(paper)

    # Sort newest research first, prioritizing curated priority journals, full-text OA, and peer-reviewed papers
    ready_papers.sort(
        key=lambda p: (
            p.published_date,
            1 if p.provenance.get("priority_journal") else 0,
            1 if p.article_body_excerpt else 0,
            1 if p.peer_reviewed else 0,
        ),
        reverse=True,
    )
    ready_candidates = [p.to_dict() for p in ready_papers]

    summary = {
        **collection_report,
        "deduplicated_count": len(unique_papers),
        "duplicates_skipped": len(skipped_duplicates),
        "non_biological_filtered": rejected_non_bio,
        "stale_or_invalid_date_filtered": rejected_stale_or_bogus_date,
        "ready_candidates_count": len(ready_candidates),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"summary": summary, "candidates": ready_candidates},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log_path = REPO_ROOT / "state" / "logs" / "collection_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")

    logging.info("Collection complete: %s", json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
