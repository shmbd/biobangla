from __future__ import annotations

from scripts.ai.validator import ArticleQualityValidator
from scripts.config_loader import load_yaml_config
from scripts.models import GeneratedArticleDraft, StandardizedPaper
from scripts.processors.license_checker import evaluate_license


def _valid_bangla_body(doi: str = "10.1371/journal.pbio.3001234", is_preprint: bool = False) -> str:
    preprint_line = (
        "এই গবেষণাটি একটি প্রিপ্রিন্ট পাণ্ডুলিপি এবং এখনো স্বাধীন বিজ্ঞানীদের পিয়ার-রিভিউ সম্পন্ন করেনি। "
        if is_preprint
        else "এই গবেষণাটি আন্তর্জাতিক জার্নালে পিয়ার-রিভিউ প্রক্রিয়ায় যাচাইকৃত। "
    )
    return f"""## গবেষণার প্রেক্ষাপট

আধুনিক অণুজীববিজ্ঞান ও জিনতত্ত্বের গবেষণায় ব্যাকটেরিয়া এবং ভাইরাসের মধ্যকার সহ-বিবর্তনীয় লড়াই বোঝা অত্যন্ত গুরুত্বপূর্ণ। {preprint_line}গবেষকেরা দীর্ঘদিন ধরে অনুসন্ধান করছিলেন কীভাবে সামুদ্রিক ব্যাকটেরিয়া নতুন ব্যাকটেরিওফাজ আক্রমণ থেকে নিজেদের কোষীয় গঠন সুরক্ষিত রাখে এবং কোন জিনগত সংকেত এই প্রক্রিয়াকে নিয়ন্ত্রণ করে।

## গবেষণা পদ্ধতি

এই গবেষণায় বিজ্ঞানী দল গবেষণাগারের নিয়ন্ত্রিত ইন ভিট্রো (In-vitro) কোষ কালচার এবং পূর্ণাঙ্গ জিনোম সিকোয়েন্সিং পদ্ধতি ব্যবহার করেছেন। মূল গবেষণাপত্রের শনাক্তকারী সূত্র DOI: `{doi}` অনুযায়ী বিভিন্ন ব্যাকটেরিয়া স্ট্রেইনের মিউটেশন তৈরি করে প্রতিটি প্রোটিনের কার্যকারিতা আলাদাভাবে পরিমাপ করা হয়েছে এবং নিয়ন্ত্রণ গ্রুপের সাথে পরিসংখ্যানগত তুলনা সম্পন্ন করা হয়েছে।

## প্রধান ফলাফল

পরীক্ষামূলক উপাত্তে দেখা গেছে যে নির্দিষ্ট প্রতিরক্ষা অপেরন সক্রিয় হলে ভাইরাসের ডিএনএ অনুলিপন প্রক্রিয়া প্রাথমিক ধাপেই বাধাগ্রস্ত হয়। বন্য-ধরনের ব্যাকটেরিয়ার তুলনায় মিউট্যান্ট কোষে সংক্রমণের হার উল্লেখযোগ্যভাবে পরিবর্তিত হয়েছে। তবে লেখকেরা স্পষ্ট করেছেন যে গবেষণাগারের এই কোষীয় ফলাফল প্রাকৃতিক সামুদ্রিক পরিবেশে কীভাবে কাজ করে তা জানতে আরও মাঠপর্যায়ের পর্যবেক্ষণ প্রয়োজন।

## বৈজ্ঞানিক গুরুত্ব

এই মৌলিক আবিষ্কার ব্যাকটেরিয়ার প্রতিরক্ষা ব্যবস্থার বৈচিত্র্য সম্পর্কে আমাদের জ্ঞানকে সমৃদ্ধ করেছে এবং ভবিষ্যতে জৈবপ্রযুক্তি ও আণবিক জীববিজ্ঞানের নতুন গবেষণাগারে এনজাইম নকশায় সহায়ক ভিত্তি তৈরি করতে পারে।

## সীমাবদ্ধতা ও সতর্কতা

গবেষণাটি কেবল নির্দিষ্ট কয়েকটি মডেল ব্যাকটেরিয়া স্ট্রেইনের ওপর নিয়ন্ত্রিত তাপমাত্রায় পরিচালিত হয়েছে; মানবদেহ বা ক্লিনিক্যাল চিকিৎসায় এর কোনো প্রত্যক্ষ প্রয়োগ পরীক্ষা করা হয়নি। {preprint_line}এই প্রতিবেদনটি শুধুমাত্র বৈজ্ঞানিক শিক্ষার উদ্দেশ্যে রচিত এবং কোনো চিকিৎসা পরামর্শ নয়।"""


def _sample_paper(**overrides) -> StandardizedPaper:
    base = {
        "title": "Anti-phage defense operons in marine Vibrio species",
        "abstract": "Marine bacteria encode diverse anti-phage defense systems.",
        "authors": ["S. Ahmed", "L. Chen"],
        "journal": "PLOS Biology",
        "published_date": "2026-09-12",
        "source_url": "https://doi.org/10.1371/journal.pbio.3001234",
        "source_adapter": "plos",
        "doi": "10.1371/journal.pbio.3001234",
        "research_type": "original-research",
        "peer_reviewed": True,
        "publication_status": "peer-reviewed",
        "license": "CC BY 4.0",
        "is_open_access": True,
        "category": "microbiology",
        "study_model": "in-vitro",
        "allow_media_reuse": True,
    }
    base.update(overrides)
    return StandardizedPaper(**base)


def test_license_checker_enforces_media_restrictions() -> None:
    rules = load_yaml_config("editorial_rules.yaml")

    cc_by_paper = _sample_paper(license="CC BY 4.0")
    dec_open = evaluate_license(cc_by_paper, rules)
    assert dec_open.allow_media_reuse is True

    nc_nd_paper = _sample_paper(license="CC BY-NC-ND 4.0", is_open_access=False)
    dec_restricted = evaluate_license(nc_nd_paper, rules)
    assert dec_restricted.allow_media_reuse is False
    assert dec_restricted.allow_metadata_and_original_summary is True


def test_validator_passes_compliant_article() -> None:
    rules = load_yaml_config("editorial_rules.yaml")
    validator = ArticleQualityValidator(rules)
    paper = _sample_paper()
    draft = GeneratedArticleDraft(
        slug="anti-phage-vibrio-abc123",
        title_bn="সামুদ্রিক ব্যাকটেরিয়ায় ভাইরাস-প্রতিরোধী জিনগত কৌশলের নতুন তথ্য",
        description_bn="সামুদ্রিক Vibrio ব্যাকটেরিয়া কীভাবে ব্যাকটেরিওফাজ ভাইরাসের আক্রমণ প্রতিহত করে তার আণবিক বিশ্লেষণ।",
        body_markdown_bn=_valid_bangla_body(),
        tags_bn=["অণুজীববিজ্ঞান", "ব্যাকটেরিওফাজ"],
        key_findings_bn=["নির্দিষ্ট প্রতিরক্ষা অপেরন ভাইরাসের বংশবৃদ্ধি রোধ করে।"],
        paper=paper,
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
    )
    report = validator.validate(draft)
    assert report.outcome == "PASS"


def test_validator_fails_medical_advice_and_hallucinated_doi() -> None:
    rules = load_yaml_config("editorial_rules.yaml")
    validator = ArticleQualityValidator(rules)
    paper = _sample_paper()

    bad_body = (
        _valid_bangla_body(doi="10.9999/fake.hallucinated.doi")
        + "\n\nডাক্তারের পরামর্শ ছাড়াই এই ওষুধ সেবন করুন।"
    )
    draft = GeneratedArticleDraft(
        slug="bad-draft-123",
        title_bn="সামুদ্রিক ব্যাকটেরিয়ার গবেষণা নিয়ে প্রতিবেদন",
        description_bn="গবেষণাপত্রের ফলাফল ও সীমাবদ্ধতার সংক্ষিপ্ত বিবরণ এখানে দেওয়া হলো।",
        body_markdown_bn=bad_body,
        tags_bn=["অণুজীববিজ্ঞান"],
        key_findings_bn=[],
        paper=paper,
        ai_provider="openai_compatible",
        ai_model="gpt-4o-mini",
    )
    report = validator.validate(draft)
    assert report.outcome == "FAIL"
    failed_names = {c.name for c in report.checks if c.status == "FAIL"}
    assert "medical_safety" in failed_names
    assert "factual_citation_consistency" in failed_names


def test_validator_holds_preprint_missing_disclaimer_and_blocks_copyrighted_image() -> None:
    rules = load_yaml_config("editorial_rules.yaml")
    validator = ArticleQualityValidator(rules)

    preprint_paper = _sample_paper(
        journal="bioRxiv (Preprint Server)",
        doi="10.1101/2026.09.01.123456",
        research_type="preprint",
        peer_reviewed=False,
        publication_status="preprint",
        license="CC BY-NC-ND 4.0",
        allow_media_reuse=False,
    )

    # 1. Missing preprint disclaimer in Bangla body -> REVIEW
    draft_review = GeneratedArticleDraft(
        slug="preprint-missing-note",
        title_bn="জিনোমিক অনুক্রম বিশ্লেষণ বিষয়ক নতুন প্রাথমিক গবেষণা প্রতিবেদন",
        description_bn="নতুন এই গবেষণায় জিনোমিক অনুক্রমের পরিবর্তন বিশ্লেষণ করা হয়েছে বিস্তারিতভাবে।",
        body_markdown_bn=_valid_bangla_body(
            doi="10.1101/2026.09.01.123456", is_preprint=False
        ).replace("পিয়ার-রিভিউ", "যাচাই"),
        tags_bn=["জিনতত্ত্ব"],
        key_findings_bn=[],
        paper=preprint_paper,
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
    )
    rep_review = validator.validate(draft_review)
    assert rep_review.outcome == "REVIEW"

    # 2. Attaching publisher image under non-open media license -> FAIL
    draft_illegal_img = GeneratedArticleDraft(
        slug="illegal-image-test",
        title_bn="প্রিপ্রিন্ট জিনোমিক অনুক্রম বিশ্লেষণ বিষয়ক গবেষণা প্রতিবেদন",
        description_bn="প্রিপ্রিন্ট সার্ভারে প্রকাশিত নতুন এই গবেষণার ফলাফল ও সীমাবদ্ধতা।",
        body_markdown_bn=_valid_bangla_body(
            doi="10.1101/2026.09.01.123456", is_preprint=True
        ),
        tags_bn=["জিনতত্ত্ব"],
        key_findings_bn=[],
        paper=preprint_paper,
        ai_provider="gemini",
        ai_model="gemini-2.5-flash",
        image="https://publisher.example.com/copyrighted-figure1.png",
        image_attribution="Publisher Figure",
    )
    rep_fail = validator.validate(draft_illegal_img)
    assert rep_fail.outcome == "FAIL"
