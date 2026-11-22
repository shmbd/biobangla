from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any
import unicodedata
from urllib.parse import urlparse

from scripts.collectors.base import DOI_EXTRACT_RE, normalize_doi
from scripts.models import CheckResult, GeneratedArticleDraft, QualityOutcome, ValidationReport
from scripts.processors.deduplicator import ExistingCorpusIndex, title_jaccard_similarity

DOI_FORMAT_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
BANGLA_CHAR_RE = re.compile(r"[\u0980-\u09FF]")
ALPHA_CHAR_RE = re.compile(r"[A-Za-z\u0980-\u09FF]")


def _bangla_ratio(text: str) -> float:
    letters = ALPHA_CHAR_RE.findall(text)
    if not letters:
        return 0.0
    bn_letters = BANGLA_CHAR_RE.findall(text)
    return len(bn_letters) / len(letters)


def _word_count(text: str) -> int:
    cleaned = re.sub(r"[#*`>\-\[\]()]", " ", text)
    return len([w for w in cleaned.split() if w.strip()])


class ArticleQualityValidator:
    """
    Independent deterministic Quality Control Gate before publication.
    NOTE: Never uses AI self-assessment as scientific verification.
    Outcomes:
      - PASS: Eligible for automatic publication
      - REVIEW: Held in review queue for human editorial inspection
      - FAIL: Rejected immediately
    """

    def __init__(
        self,
        editorial_rules: dict[str, Any],
        existing_corpus: ExistingCorpusIndex | None = None,
    ) -> None:
        self.rules = editorial_rules
        self.corpus = existing_corpus or ExistingCorpusIndex()

    def validate(self, draft: GeneratedArticleDraft) -> ValidationReport:
        checks: list[CheckResult] = []
        paper = draft.paper

        # 1. Source URL validation
        parsed_url = urlparse(paper.source_url or "")
        if parsed_url.scheme == "https" and bool(parsed_url.netloc):
            checks.append(CheckResult("source_url", "PASS", "বৈধ HTTPS উৎস লিংক উপস্থিত।"))
        elif parsed_url.scheme == "http" and bool(parsed_url.netloc):
            checks.append(
                CheckResult("source_url", "REVIEW", "উৎস লিংক HTTPS নয় (HTTP); মানব যাচাই প্রয়োজন।")
            )
        else:
            checks.append(CheckResult("source_url", "FAIL", "বৈধ উৎস URL অনুপস্থিত।"))

        # 2. DOI validation
        req_doi = bool(
            self.rules.get("article_requirements", {}).get(
                "require_doi_for_journal_articles", True
            )
        )
        if paper.doi:
            norm_doi = normalize_doi(paper.doi)
            if norm_doi and DOI_FORMAT_RE.match(norm_doi):
                checks.append(CheckResult("doi_format", "PASS", f"বৈধ DOI: {norm_doi}"))
            else:
                checks.append(CheckResult("doi_format", "FAIL", f"ত্রুটিপূর্ণ DOI বিন্যাস: {paper.doi}"))
        elif req_doi and paper.research_type == "original-research":
            checks.append(
                CheckResult("doi_format", "REVIEW", "DOI অনুপস্থিত; প্রকাশের পূর্বে ম্যানুয়াল যাচাই প্রয়োজন।")
            )
        else:
            checks.append(CheckResult("doi_format", "PASS", "বিকল্প উৎস শনাক্তকারী ব্যবহৃত।"))

        # 3. Date sanity check
        try:
            pub_dt = datetime.strptime(paper.published_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            max_future = datetime.now(timezone.utc) + timedelta(days=3)
            if pub_dt > max_future:
                checks.append(
                    CheckResult("publication_date", "FAIL", "প্রকাশের তারিখ ভবিষ্যতের হতে পারে না।")
                )
            else:
                checks.append(CheckResult("publication_date", "PASS", "প্রকাশের তারিখ বৈধ।"))
        except ValueError:
            checks.append(
                CheckResult("publication_date", "FAIL", f"অবৈধ তারিখের বিন্যাস: {paper.published_date}")
            )

        # 4. Duplicate status against existing corpus
        is_dup, dup_reason = self.corpus.contains(paper)
        if is_dup:
            checks.append(
                CheckResult("duplicate_check", "FAIL", f"ডুপ্লিকেট নিবন্ধ শনাক্ত ({dup_reason})।")
            )
        else:
            checks.append(CheckResult("duplicate_check", "PASS", "কোনো ডুপ্লিকেট পাওয়া যায়নি।"))

        # 5. Preprint scientific integrity rules
        is_preprint = (
            paper.research_type == "preprint"
            or paper.publication_status == "preprint"
            or "biorxiv" in paper.journal.lower()
            or "medrxiv" in paper.journal.lower()
        )
        if is_preprint:
            if paper.peer_reviewed:
                checks.append(
                    CheckResult(
                        "preprint_integrity",
                        "FAIL",
                        "প্রিপ্রিন্ট নিবন্ধে peer_reviewed=True সেট করা কঠোরভাবে নিষিদ্ধ।",
                    )
                )
            else:
                combined_bn = unicodedata.normalize(
                    "NFC",
                    f"{draft.title_bn} {draft.description_bn} {draft.body_markdown_bn}",
                ).replace("য়", "য়")
                req_kw = [
                    unicodedata.normalize("NFC", k).replace("য়", "য়")
                    for k in self.rules.get("preprint_rules", {}).get(
                        "required_disclaimer_keywords_bn", ["প্রিপ্রিন্ট", "পিয়ার-রিভিউ"]
                    )
                ]
                forbid_phrases = self.rules.get("preprint_rules", {}).get(
                    "forbid_phrases_for_preprints", []
                )
                norm_no_hyphen = combined_bn.replace("-", " ")
                if any(fp in combined_bn for fp in forbid_phrases):
                    checks.append(
                        CheckResult(
                            "preprint_integrity",
                            "FAIL",
                            "প্রিপ্রিন্ট নিবন্ধে চূড়ান্ত পিয়ার-রিভিউকৃত প্রমাণের বিভ্রান্তিকর দাবি পাওয়া গেছে।",
                        )
                    )
                elif all(kw.replace("-", " ") in norm_no_hyphen for kw in req_kw):
                    checks.append(
                        CheckResult(
                            "preprint_integrity",
                            "PASS",
                            "প্রিপ্রিন্ট সতর্কতা ও অ-পর্যালোচিত মর্যাদা সঠিকভাবে উল্লেখিত।",
                        )
                    )
                else:
                    checks.append(
                        CheckResult(
                            "preprint_integrity",
                            "REVIEW",
                            "প্রিপ্রিন্ট নিবন্ধের মূল পাঠে 'প্রিপ্রিন্ট' ও 'পিয়ার-রিভিউ' শব্দের স্পষ্ট সতর্কতা যোগ করা প্রয়োজন।",
                        )
                    )
        else:
            checks.append(CheckResult("preprint_integrity", "PASS", "পিয়ার-রিভিউ মর্যাদা সামঞ্জস্যপূর্ণ।"))

        # 6. License & media reuse restrictions
        if draft.image:
            if not paper.allow_media_reuse:
                checks.append(
                    CheckResult(
                        "license_compliance",
                        "FAIL",
                        f"'{paper.license}' লাইসেন্সের অধীনে প্রকাশকের ছবি ব্যবহার নিষিদ্ধ।",
                    )
                )
            elif not draft.image_attribution or len(draft.image_attribution.strip()) < 5:
                checks.append(
                    CheckResult(
                        "license_compliance",
                        "FAIL",
                        "ছবির উৎস স্বীকৃতি (image_attribution) অনুপস্থিত।",
                    )
                )
            else:
                checks.append(
                    CheckResult("license_compliance", "PASS", "উন্মুক্ত লাইসেন্স ও ছবির স্বীকৃতি বৈধ।")
                )
        else:
            checks.append(
                CheckResult(
                    "license_compliance",
                    "PASS",
                    "কপিরাইটযুক্ত বাহ্যিক ছবি ব্যবহৃত হয়নি (মৌলিক CSS/SVG রেখাচিত্র ব্যবহৃত)।",
                )
            )

        # 7. Medical safety & overstatement check
        full_text = f"{draft.title_bn}\n{draft.description_bn}\n{draft.body_markdown_bn}"
        prohibited = self.rules.get("medical_safety_rules", {}).get("prohibited_patterns", [])
        warnings = self.rules.get("medical_safety_rules", {}).get(
            "overstatement_warning_patterns", []
        )
        hit_prohibited = [p for p in prohibited if p in full_text]
        hit_warnings = [w for w in warnings if w in full_text]
        if hit_prohibited:
            checks.append(
                CheckResult(
                    "medical_safety",
                    "FAIL",
                    f"নিষিদ্ধ চিকিৎসা পরামর্শ/অসমর্থিত দাবি শনাক্ত: {', '.join(hit_prohibited)}",
                )
            )
        elif hit_warnings:
            checks.append(
                CheckResult(
                    "medical_safety",
                    "REVIEW",
                    f"অতিরঞ্জিত শব্দচয়ন শনাক্ত ({', '.join(hit_warnings)}); সম্পাদনা প্রয়োজন।",
                )
            )
        else:
            checks.append(
                CheckResult("medical_safety", "PASS", "কোনো অননুমোদিত চিকিৎসা দাবি পাওয়া যায়নি।")
            )

        # 8. Bangla language quality & non-verbatim abstract check
        min_bn_ratio = float(
            self.rules.get("article_requirements", {}).get("min_bangla_character_ratio", 0.45)
        )
        bn_ratio = _bangla_ratio(draft.body_markdown_bn)
        overlap_with_abstract = title_jaccard_similarity(draft.body_markdown_bn, paper.abstract)
        if overlap_with_abstract > 0.65:
            checks.append(
                CheckResult(
                    "bangla_quality",
                    "FAIL",
                    "মূল ইংরেজি অ্যাবস্ট্রাক্ট হুবহু কপি করা হয়েছে।",
                )
            )
        elif bn_ratio < min_bn_ratio:
            checks.append(
                CheckResult(
                    "bangla_quality",
                    "FAIL",
                    f"বাংলা অক্ষরের অনুপাত অপর্যাপ্ত ({bn_ratio:.2f} < {min_bn_ratio:.2f})।",
                )
            )
        elif len(draft.title_bn.strip()) < 12 or len(draft.description_bn.strip()) < 25:
            checks.append(
                CheckResult("bangla_quality", "FAIL", "বাংলা শিরোনাম বা সারসংক্ষেপ অসম্পূর্ণ।")
            )
        else:
            checks.append(
                CheckResult(
                    "bangla_quality",
                    "PASS",
                    f"বাংলা ভাষার অনুপাত সন্তোষজনক ({bn_ratio:.2f})।",
                )
            )

        # 9. Required sections & article length
        req_sections = self.rules.get("article_requirements", {}).get("required_sections", [])
        missing_sections = [s for s in req_sections if s not in draft.body_markdown_bn]
        min_words = int(self.rules.get("article_requirements", {}).get("min_word_count", 220))
        max_words = int(self.rules.get("article_requirements", {}).get("max_word_count", 1800))
        words = _word_count(draft.body_markdown_bn)

        if missing_sections:
            checks.append(
                CheckResult(
                    "structure_and_length",
                    "FAIL",
                    f"আবশ্যিক অনুচ্ছেদ অনুপস্থিত: {', '.join(missing_sections)}",
                )
            )
        elif words < 140 or words > max_words:
            checks.append(
                CheckResult(
                    "structure_and_length",
                    "FAIL",
                    f"নিবন্ধের শব্দসংখ্যা গ্রহণযোগ্য সীমার বাইরে ({words} শব্দ)।",
                )
            )
        elif words < min_words:
            checks.append(
                CheckResult(
                    "structure_and_length",
                    "REVIEW",
                    f"নিবন্ধটি কিছুটা সংক্ষিপ্ত ({words} < {min_words} শব্দ); মানব সম্পাদকের পর্যালোচনা প্রয়োজন।",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "structure_and_length",
                    "PASS",
                    f"সকল আবশ্যিক শিরোনাম উপস্থিত এবং দৈর্ঘ্য উপযুক্ত ({words} শব্দ)।",
                )
            )

        # 10. Factual citation & DOI consistency check (detects hallucinated DOIs)
        mentioned_dois = {m.lower().rstrip(".,;)") for m in DOI_EXTRACT_RE.findall(full_text)}
        expected_doi = normalize_doi(paper.doi)
        if mentioned_dois:
            if not expected_doi or any(d != expected_doi for d in mentioned_dois):
                checks.append(
                    CheckResult(
                        "factual_citation_consistency",
                        "FAIL",
                        f"পাঠে উল্লিখিত DOI ({mentioned_dois}) মূল গবেষণাপত্রের DOI ({expected_doi})-এর সাথে মেলেনি!",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        "factual_citation_consistency",
                        "PASS",
                        "পাঠে উল্লিখিত DOI মূল উৎসের সাথে সম্পূর্ণ সামঞ্জস্যপূর্ণ।",
                    )
                )
        else:
            checks.append(
                CheckResult("factual_citation_consistency", "PASS", "কোনো কাল্পনিক DOI পাওয়া যায়নি।")
            )

        # 11. Mock provider safety gate: Mock/offline drafts are held for REVIEW unless explicitly testing
        if draft.ai_provider == "mock":
            checks.append(
                CheckResult(
                    "provider_verification",
                    "REVIEW",
                    "মক (offline template) প্রোভাইডার ব্যবহৃত হয়েছে; স্বয়ংক্রিয় লাইভ প্রকাশের বদলে REVIEW কিউতে সংরক্ষিত।",
                )
            )

        # Aggregate final outcome: any FAIL -> FAIL; else any REVIEW -> REVIEW; else PASS
        statuses = {c.status for c in checks}
        if "FAIL" in statuses:
            final_outcome: QualityOutcome = "FAIL"
        elif "REVIEW" in statuses:
            final_outcome = "REVIEW"
        else:
            final_outcome = "PASS"

        reasons = [f"[{c.status}] {c.name}: {c.message}" for c in checks if c.status != "PASS"]
        return ValidationReport(outcome=final_outcome, checks=checks, reasons=reasons)
