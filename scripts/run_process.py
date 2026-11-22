from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.provider import create_ai_provider_from_env
from scripts.ai.validator import ArticleQualityValidator
from scripts.ai.writer import BanglaScienceWriter
from scripts.config_loader import load_all_configs
from scripts.models import StandardizedPaper, utc_now_iso
from scripts.processors.deduplicator import ExistingCorpusIndex
from scripts.publishing.markdown_generator import ArticlePublisher


def main() -> int:
    parser = argparse.ArgumentParser(
        description="biobangla — Generate Bangla science journalism, run QC gates, and publish PASS articles."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=REPO_ROOT / "state" / "candidates" / "latest_candidates.json",
        help="Path to candidate batch JSON produced by run_collect.py.",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=int(os.getenv("MAX_ARTICLES_TO_PUBLISH", "5")),
        help="Maximum candidate papers to process in a single run.",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=REPO_ROOT / "state",
        help="Directory for review queue and audit logs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("PIPELINE_DRY_RUN", "false").lower() == "true",
        help="Validate and log outcomes without writing Markdown files.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.input.exists():
        logging.info("No candidate batch file found at %s; nothing to process.", args.input)
        return 0

    batch = json.loads(args.input.read_text(encoding="utf-8"))
    raw_candidates = batch.get("candidates") or []
    if not raw_candidates:
        logging.info("Candidate batch is empty; exiting cleanly.")
        return 0

    configs = load_all_configs()
    articles_dir = REPO_ROOT / "content" / "articles"
    review_dir = args.state_dir / "review_queue"
    pub_log = args.state_dir / "logs" / "publication_log.jsonl"

    corpus = ExistingCorpusIndex.from_articles_dir(articles_dir)
    provider = create_ai_provider_from_env()
    writer = BanglaScienceWriter(
        provider=provider,
        glossary_config=configs["glossary"],
        editorial_rules=configs["editorial_rules"],
    )
    validator = ArticleQualityValidator(
        editorial_rules=configs["editorial_rules"],
        existing_corpus=corpus,
    )
    publisher = ArticlePublisher(
        published_dir=articles_dir,
        review_queue_dir=review_dir,
        log_file=pub_log,
        dry_run=args.dry_run,
    )

    counts = {"PASS": 0, "REVIEW": 0, "FAIL": 0, "ERROR": 0}

    for item in raw_candidates[: args.max_articles]:
        paper = StandardizedPaper.from_dict(item)
        try:
            draft = writer.write_article(paper)
            report = validator.validate(draft)
            publisher.process_validated_draft(draft, report)
            counts[report.outcome] += 1
            logging.info(
                "Processed '%s' -> %s (%s)",
                paper.title[:60],
                report.outcome,
                "; ".join(report.reasons) if report.reasons else "all checks passed",
            )
        except Exception as exc:
            counts["ERROR"] += 1
            logging.error("Failed processing candidate '%s': %s", paper.title[:60], exc)

    report_path = args.state_dir / "logs" / "last_process_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "processed_at": utc_now_iso(),
                "ai_provider": provider.provider_name,
                "ai_model": provider.model_name,
                "dry_run": args.dry_run,
                "outcomes": counts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logging.info("Processing summary: %s", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
