from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import yaml

from scripts.models import GeneratedArticleDraft, ValidationReport, utc_now_iso

CATEGORY_DEFAULT_MOTIF: dict[str, str] = {
    "microbiology": "microbe",
    "biotechnology": "crispr",
    "genetics-genomics": "dna",
    "biomedical-science": "cell",
    "immunology": "antibody",
    "environment-biodiversity": "ecosystem",
    "marine-biology": "marine",
    "botany": "leaf",
    "zoology": "zoology",
    "evolution": "phylogeny",
}


def render_article_markdown(
    draft: GeneratedArticleDraft, status_override: str | None = None
) -> str:
    paper = draft.paper
    article_status = status_override or ("sample" if draft.is_sample else "published")
    motif = CATEGORY_DEFAULT_MOTIF.get(paper.category, "dna")

    frontmatter: dict[str, Any] = {
        "title": draft.title_bn,
        "description": draft.description_bn,
        "date": paper.published_date,
        "category": paper.category,
        "tags": draft.tags_bn,
        "authors": paper.authors,
        "desk": "জীববিজ্ঞান গবেষণা ডেস্ক",
        "journal": paper.journal,
        "source_url": paper.source_url,
        "research_type": paper.research_type,
        "peer_reviewed": bool(paper.peer_reviewed),
        "publication_status": paper.publication_status,
        "study_model": paper.study_model,
        "license": paper.license,
        "image_attribution": draft.image_attribution
        or "জীববিজ্ঞান মৌলিক বৈজ্ঞানিক রেখাচিত্র (CC BY-NC 4.0)",
        "illustration_motif": motif,
        "language": "bn",
        "status": article_status,
        "featured": False,
        "is_sample": bool(draft.is_sample),
    }
    if paper.doi:
        frontmatter["doi"] = paper.doi
    if draft.image and paper.allow_media_reuse:
        frontmatter["image"] = draft.image
        if draft.image_alt:
            frontmatter["image_alt"] = draft.image_alt
    if draft.key_findings_bn:
        frontmatter["key_findings"] = draft.key_findings_bn

    yaml_header = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    return f"---\n{yaml_header}\n---\n\n{draft.body_markdown_bn.strip()}\n"


class ArticlePublisher:
    """
    Enforces publication gate outcomes:
      - PASS   -> Published automatically to content/articles/<slug>.md
      - REVIEW -> Held in state/review_queue/<slug>.md for human inspection
      - FAIL   -> Rejected; never written to published content
    Logs every decision to state/logs/publication_log.jsonl.
    """

    def __init__(
        self,
        published_dir: Path,
        review_queue_dir: Path,
        log_file: Path,
        dry_run: bool = False,
    ) -> None:
        self.published_dir = published_dir
        self.review_queue_dir = review_queue_dir
        self.log_file = log_file
        self.dry_run = dry_run

    def process_validated_draft(
        self, draft: GeneratedArticleDraft, report: ValidationReport
    ) -> dict[str, Any]:
        output_path: str | None = None

        if report.outcome == "PASS":
            target = self.published_dir / f"{draft.slug}.md"
            output_path = str(target)
            if not self.dry_run:
                self.published_dir.mkdir(parents=True, exist_ok=True)
                md_text = render_article_markdown(draft)
                target.write_text(md_text, encoding="utf-8")

        elif report.outcome == "REVIEW":
            target_md = self.review_queue_dir / f"{draft.slug}.md"
            target_json = self.review_queue_dir / f"{draft.slug}.report.json"
            output_path = str(target_md)
            if not self.dry_run:
                self.review_queue_dir.mkdir(parents=True, exist_ok=True)
                md_text = render_article_markdown(draft, status_override="review")
                target_md.write_text(md_text, encoding="utf-8")
                target_json.write_text(
                    json.dumps(
                        {
                            "slug": draft.slug,
                            "paper": draft.paper.to_dict(),
                            "validation": report.to_dict(),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

        # FAIL articles are rejected and never written to content or review queue

        log_entry = {
            "timestamp": utc_now_iso(),
            "slug": draft.slug,
            "outcome": report.outcome,
            "dry_run": self.dry_run,
            "title_bn": draft.title_bn,
            "source_title": draft.paper.title,
            "doi": draft.paper.doi,
            "source_url": draft.paper.source_url,
            "journal": draft.paper.journal,
            "category": draft.paper.category,
            "research_type": draft.paper.research_type,
            "peer_reviewed": draft.paper.peer_reviewed,
            "ai_provider": draft.ai_provider,
            "ai_model": draft.ai_model,
            "reasons": report.reasons,
            "output_path": output_path,
        }
        self._append_log(log_entry)
        return log_entry

    def _append_log(self, entry: dict[str, Any]) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
