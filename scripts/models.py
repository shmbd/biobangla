from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ResearchType = Literal["original-research", "review", "preprint", "editorial"]
PublicationStatus = Literal["peer-reviewed", "preprint", "editorial-summary"]
StudyModel = Literal[
    "in-vitro",
    "animal",
    "human-observational",
    "human-clinical",
    "computational",
    "field-ecology",
    "multi-study",
]
QualityOutcome = Literal["PASS", "REVIEW", "FAIL"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class StandardizedPaper:
    """Normalized metadata record produced by all source collectors."""

    title: str
    abstract: str
    authors: list[str]
    journal: str
    published_date: str  # ISO YYYY-MM-DD
    source_url: str
    source_adapter: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    research_type: ResearchType = "original-research"
    peer_reviewed: bool = True
    publication_status: PublicationStatus = "peer-reviewed"
    license: str = "Unknown"
    is_open_access: bool = False
    category: str = "biomedical-science"
    study_model: StudyModel = "multi-study"
    is_biological: bool = True
    allow_media_reuse: bool = False
    article_body_excerpt: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce strict preprint invariant at model construction level
        if self.research_type == "preprint" or self.publication_status == "preprint":
            self.peer_reviewed = False
            self.publication_status = "preprint"
            self.research_type = "preprint"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StandardizedPaper:
        return cls(**payload)


@dataclass
class GeneratedArticleDraft:
    """Original Bangla scientific journalism draft generated from a StandardizedPaper."""

    slug: str
    title_bn: str
    description_bn: str
    body_markdown_bn: str
    tags_bn: list[str]
    key_findings_bn: list[str]
    paper: StandardizedPaper
    ai_provider: str
    ai_model: str
    is_sample: bool = False
    image: str | None = None
    image_alt: str | None = None
    image_attribution: str | None = None
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GeneratedArticleDraft:
        paper_data = payload["paper"]
        paper = (
            paper_data
            if isinstance(paper_data, StandardizedPaper)
            else StandardizedPaper.from_dict(paper_data)
        )
        rest = {k: v for k, v in payload.items() if k != "paper"}
        return cls(paper=paper, **rest)


@dataclass
class CheckResult:
    name: str
    status: QualityOutcome
    message: str


@dataclass
class ValidationReport:
    outcome: QualityOutcome
    checks: list[CheckResult]
    reasons: list[str]
    validated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "checks": [asdict(c) for c in self.checks],
            "reasons": self.reasons,
            "validated_at": self.validated_at,
        }
