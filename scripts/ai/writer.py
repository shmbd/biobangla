from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from scripts.ai.provider import AIProvider
from scripts.models import GeneratedArticleDraft, StandardizedPaper

SLUG_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def build_stable_slug(paper: StandardizedPaper) -> str:
    base = SLUG_CLEAN_RE.sub("-", paper.title.lower()).strip("-")
    short_base = "-".join(base.split("-")[:8]) or "research-report"
    identifier = (paper.doi or paper.pmid or paper.source_url).encode("utf-8")
    digest = hashlib.sha256(identifier).hexdigest()[:6]
    return f"{short_base}-{digest}"


def build_system_prompt(
    glossary_config: dict[str, Any], editorial_rules: dict[str, Any]
) -> str:
    terms = glossary_config.get("terms") or []
    glossary_lines = [
        f"- {t['en']} -> {t['bn']} ({t.get('usage_note', '')})"
        for t in terms[:20]
        if "en" in t and "bn" in t
    ]
    immutable = ", ".join(glossary_config.get("immutable_symbols") or [])
    required_sections = editorial_rules.get("article_requirements", {}).get(
        "required_sections", []
    )
    sections_formatted = "\n".join(f"## {sec}" for sec in required_sections)

    return f"""আপনি 'জীববিজ্ঞান (biobangla)' সাময়িকীর একজন জ্যেষ্ঠ বিজ্ঞান সাংবাদিক ও জীববিজ্ঞান সম্পাদক।
আপনার কাজ হলো প্রদত্ত বৈজ্ঞানিক গবেষণাপত্রের তথ্যের ভিত্তিতে সম্পূর্ণ মৌলিক, তথ্যনিষ্ঠ ও প্রাঞ্জল বাংলা বিজ্ঞান সাংবাদিকতা রচনা করা।

কঠোর সম্পাদনা নিয়মাবলি:
১. মূল ইংরেজি অ্যাবস্ট্রাক্টের হুবহু আক্ষরিক অনুবাদ করবেন না; সহজ ও প্রমিত বাংলায় মৌলিক ব্যাখ্যা লিখুন।
২. কখনোই কোনো সংখ্যা, ফলাফল, লেখকের নাম, জার্নাল বা সিদ্ধান্ত নিজে থেকে বানাবেন না (Never invent data or claims)।
৩. জীবপ্রজাতির দ্বিপদ বৈজ্ঞানিক নাম, জিনের প্রতীক, প্রোটিনের নাম এবং DOI অবিকল সংরক্ষণ করুন: {immutable}।
৪. ইন-ভিট্রো (কোষীয় পরীক্ষা), প্রাণী মডেল এবং মানব ক্লিনিক্যাল ট্রায়ালের পার্থক্য স্পষ্ট রাখুন। সহসম্পর্ককে (Correlation) কার্যকারণ (Causation) বলবেন না।
৫. যদি peer_reviewed=false বা প্রিপ্রিন্ট হয়, তবে লেখায় স্পষ্টভাবে উল্লেখ করুন যে এটি একটি 'প্রিপ্রিন্ট' এবং এখনো 'পিয়ার-রিভিউ' সম্পন্ন করেনি।
৬. কোনো চিকিৎসা পরামর্শ, ওষুধ সেবনের নির্দেশ বা অসমর্থিত ক্লিনিক্যাল সুপারিশ দেবেন না।
৭. নিবন্ধের মূল অংশে অবশ্যই নিচের পাঁচটি Markdown শিরোনাম হুবহু থাকতে হবে:
{sections_formatted}
৮. যদি 'article_fulltext_sections' প্রদান করা থাকে, তবে কেবল সংক্ষিপ্ত অ্যাবস্ট্রাক্টের ওপর নির্ভর না করে মূল গবেষণাপত্রের পদ্ধতি (Methods), নমুনার আকার বা জীবপ্রজাতি, প্রধান ফলাফল (Results) এবং আলোচনা ও সীমাবদ্ধতা (Discussion/Limitations) অংশগুলো মনোযোগ দিয়ে পড়ে তথ্যসমৃদ্ধ কিন্তু সহজবোধ্য বাংলা প্রতিবেদন লিখুন।

প্রমিত বাংলা পরিভাষা নির্দেশিকা:
{chr(10).join(glossary_lines)}

আউটপুট অবশ্যই বৈধ JSON অবজেক্ট হতে হবে নিচের কী (keys)-সহ:
{{
  "title_bn": "বাংলা শিরোনাম",
  "description_bn": "২-৩ বাক্যের সংক্ষিপ্ত সারসংক্ষেপ",
  "tags_bn": ["ট্যাগ১", "ট্যাগ২", "ট্যাগ৩"],
  "key_findings_bn": ["প্রধান তথ্য ১", "প্রধান তথ্য ২", "প্রধান তথ্য ৩"],
  "body_markdown_bn": "পাঁচটি ## শিরোনামসহ পূর্ণাঙ্গ ও বিস্তারিত বাংলা Markdown নিবন্ধ (কমপক্ষে ৩০০ থেকে ৪৫০ শব্দ)"
}}"""


class BanglaScienceWriter:
    """Generates structured Bangla scientific journalism drafts via any configured AIProvider."""

    def __init__(
        self,
        provider: AIProvider,
        glossary_config: dict[str, Any],
        editorial_rules: dict[str, Any],
    ) -> None:
        self.provider = provider
        self.glossary_config = glossary_config
        self.editorial_rules = editorial_rules
        self._system_prompt = build_system_prompt(glossary_config, editorial_rules)

    def write_article(self, paper: StandardizedPaper) -> GeneratedArticleDraft:
        paper_payload: dict[str, Any] = {
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors,
            "journal": paper.journal,
            "published_date": paper.published_date,
            "doi": paper.doi,
            "source_url": paper.source_url,
            "research_type": paper.research_type,
            "peer_reviewed": paper.peer_reviewed,
            "publication_status": paper.publication_status,
            "study_model": paper.study_model,
            "category": paper.category,
        }
        if paper.article_body_excerpt:
            paper_payload["article_fulltext_sections"] = paper.article_body_excerpt
        user_prompt = (
            "নিচের গবেষণাপত্রটির মেটাডেটা ও সারসংক্ষেপ থেকে নিয়ম মেনে বাংলা বৈজ্ঞানিক প্রতিবেদন JSON আকারে তৈরি করুন:\n"
            + json.dumps(paper_payload, ensure_ascii=False, indent=2)
        )

        result = self.provider.generate_json(self._system_prompt, user_prompt)
        title_bn = str(result.get("title_bn") or "").strip()
        description_bn = str(result.get("description_bn") or "").strip()
        body_bn = str(result.get("body_markdown_bn") or "").strip()
        tags_bn = [str(t).strip() for t in (result.get("tags_bn") or []) if str(t).strip()]
        findings_bn = [
            str(f).strip() for f in (result.get("key_findings_bn") or []) if str(f).strip()
        ]

        if not tags_bn:
            tags_bn = ["জীববিজ্ঞান"]

        return GeneratedArticleDraft(
            slug=build_stable_slug(paper),
            title_bn=title_bn,
            description_bn=description_bn,
            body_markdown_bn=body_bn,
            tags_bn=tags_bn,
            key_findings_bn=findings_bn,
            paper=paper,
            ai_provider=self.provider.provider_name,
            ai_model=self.provider.model_name,
            is_sample=self.provider.is_mock,
        )
