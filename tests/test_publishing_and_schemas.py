from __future__ import annotations

import json
from pathlib import Path
import re
import yaml

from scripts.config_loader import load_yaml_config
from scripts.models import CheckResult, GeneratedArticleDraft, StandardizedPaper, ValidationReport
from scripts.publishing.markdown_generator import ArticlePublisher
from tests.test_license_and_validator import _sample_paper, _valid_bangla_body

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def test_publisher_routes_pass_review_and_fail_correctly(tmp_path: Path) -> None:
    pub_dir = tmp_path / "content" / "articles"
    rev_dir = tmp_path / "state" / "review_queue"
    log_file = tmp_path / "state" / "logs" / "publication_log.jsonl"

    publisher = ArticlePublisher(
        published_dir=pub_dir,
        review_queue_dir=rev_dir,
        log_file=log_file,
    )

    paper = _sample_paper()
    draft_pass = GeneratedArticleDraft(
        slug="pass-article",
        title_bn="সামুদ্রিক ব্যাকটেরিয়ায় ভাইরাস-প্রতিরোধী জিনগত কৌশলের নতুন তথ্য",
        description_bn="সামুদ্রিক ব্যাকটেরিয়ার প্রতিরক্ষা ব্যবস্থার আণবিক বিশ্লেষণ।",
        body_markdown_bn=_valid_bangla_body(),
        tags_bn=["অণুজীববিজ্ঞান"],
        key_findings_bn=["প্রধান ফলাফল ১"],
        paper=paper,
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
    )
    publisher.process_validated_draft(
        draft_pass,
        ValidationReport("PASS", [CheckResult("all", "PASS", "ok")], []),
    )
    assert (pub_dir / "pass-article.md").exists()

    draft_review = GeneratedArticleDraft(
        slug="review-article",
        title_bn="পর্যালোচনার জন্য সংরক্ষিত খসড়া নিবন্ধ",
        description_bn="মানব সম্পাদকের যাচাইয়ের জন্য অপেক্ষমাণ খসড়া নিবন্ধ।",
        body_markdown_bn=_valid_bangla_body(),
        tags_bn=["অণুজীববিজ্ঞান"],
        key_findings_bn=[],
        paper=paper,
        ai_provider="mock",
        ai_model="offline",
    )
    publisher.process_validated_draft(
        draft_review,
        ValidationReport("REVIEW", [CheckResult("mock", "REVIEW", "hold")], ["hold"]),
    )
    assert not (pub_dir / "review-article.md").exists()
    assert (rev_dir / "review-article.md").exists()
    assert (rev_dir / "review-article.report.json").exists()

    draft_fail = GeneratedArticleDraft(
        slug="fail-article",
        title_bn="বাতিলকৃত নিবন্ধ",
        description_bn="ত্রুটিপূর্ণ মেটাডেটার কারণে বাতিলকৃত নিবন্ধ।",
        body_markdown_bn="অসম্পূর্ণ",
        tags_bn=["অণুজীববিজ্ঞান"],
        key_findings_bn=[],
        paper=paper,
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
    )
    publisher.process_validated_draft(
        draft_fail,
        ValidationReport("FAIL", [CheckResult("err", "FAIL", "bad")], ["bad"]),
    )
    assert not (pub_dir / "fail-article.md").exists()
    assert not (rev_dir / "fail-article.md").exists()

    logs = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert [entry["outcome"] for entry in logs] == ["PASS", "REVIEW", "FAIL"]


def test_all_repository_sample_articles_satisfy_strict_schema_and_editorial_rules() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    articles_dir = repo_root / "content" / "articles"
    categories_cfg = load_yaml_config("categories.yaml")
    editorial_cfg = load_yaml_config("editorial_rules.yaml")

    valid_categories = {c["slug"] for c in categories_cfg["categories"]}
    required_sections = editorial_cfg["article_requirements"]["required_sections"]

    md_files = list(articles_dir.glob("*.md"))
    assert len(md_files) >= 10, "Expected sample articles covering all 10 categories"

    seen_categories: set[str] = set()
    for md_file in md_files:
        raw = md_file.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(raw)
        assert match is not None, f"Invalid frontmatter in {md_file.name}"
        meta = yaml.safe_load(match.group(1))
        body = match.group(2)

        assert meta["category"] in valid_categories, f"Invalid category in {md_file.name}"
        seen_categories.add(meta["category"])

        assert meta["language"] == "bn"
        assert meta["is_sample"] is True, f"Sample article {md_file.name} must be clearly labelled is_sample=True"
        assert meta["source_url"].startswith("https://")

        if meta["research_type"] == "preprint" or meta["publication_status"] == "preprint":
            assert meta["peer_reviewed"] is False, f"Preprint {md_file.name} must never be peer_reviewed=True"

        for section in required_sections:
            assert f"## {section}" in body, f"Missing section '{section}' in {md_file.name}"

    assert seen_categories == valid_categories, "Every one of the 10 categories must have at least one sample article"
