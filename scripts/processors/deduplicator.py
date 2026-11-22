from __future__ import annotations

from pathlib import Path
import re
import yaml

from scripts.collectors.base import normalize_doi
from scripts.models import StandardizedPaper

NON_ALNUM_RE = re.compile(r"[^a-z0-9\u0980-\u09ff\s]+")
SPACE_RE = re.compile(r"\s+")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def normalize_title(title: str) -> str:
    lowered = title.lower().strip()
    cleaned = NON_ALNUM_RE.sub(" ", lowered)
    return SPACE_RE.sub(" ", cleaned).strip()


def title_jaccard_similarity(title_a: str, title_b: str) -> float:
    tokens_a = set(normalize_title(title_a).split())
    tokens_b = set(normalize_title(title_b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union


class ExistingCorpusIndex:
    """Indexes already-published Markdown articles so duplicates are never re-published."""

    def __init__(self) -> None:
        self.dois: set[str] = set()
        self.pmids: set[str] = set()
        self.source_urls: set[str] = set()
        self.normalized_titles: set[str] = set()

    @classmethod
    def from_articles_dir(cls, articles_dir: Path) -> ExistingCorpusIndex:
        index = cls()
        if not articles_dir.exists():
            return index

        for md_path in articles_dir.glob("**/*.md"):
            text = md_path.read_text(encoding="utf-8")
            match = FRONTMATTER_RE.match(text)
            if not match:
                continue
            meta = yaml.safe_load(match.group(1)) or {}
            if not isinstance(meta, dict):
                continue

            doi = normalize_doi(meta.get("doi"))
            if doi:
                index.dois.add(doi)
            src = str(meta.get("source_url") or "").strip().rstrip("/")
            if src:
                index.source_urls.add(src.lower())
            title = str(meta.get("title") or "").strip()
            if title:
                index.normalized_titles.add(normalize_title(title))
        return index

    def contains(self, paper: StandardizedPaper) -> tuple[bool, str | None]:
        norm_doi = normalize_doi(paper.doi)
        if norm_doi and norm_doi in self.dois:
            return True, f"duplicate_doi:{norm_doi}"
        if paper.pmid and paper.pmid in self.pmids:
            return True, f"duplicate_pmid:{paper.pmid}"
        clean_url = paper.source_url.strip().rstrip("/").lower()
        if clean_url and clean_url in self.source_urls:
            return True, f"duplicate_url:{clean_url}"
        norm_title = normalize_title(paper.title)
        if norm_title and norm_title in self.normalized_titles:
            return True, "duplicate_title"
        return False, None


def deduplicate_papers(
    candidates: list[StandardizedPaper],
    existing_index: ExistingCorpusIndex | None = None,
    similarity_threshold: float = 0.90,
) -> tuple[list[StandardizedPaper], list[dict[str, str]]]:
    """
    Deduplicates candidate papers by DOI, PMID, and normalized title similarity.
    If both a preprint and a peer-reviewed version appear in the same batch,
    prefers the peer-reviewed record.
    """
    corpus = existing_index or ExistingCorpusIndex()
    accepted: list[StandardizedPaper] = []
    skipped: list[dict[str, str]] = []

    seen_dois: dict[str, int] = {}
    seen_pmids: dict[str, int] = {}
    seen_titles: list[tuple[str, int]] = []

    for paper in candidates:
        paper.doi = normalize_doi(paper.doi)
        in_corpus, reason = corpus.contains(paper)
        if in_corpus:
            skipped.append({"title": paper.title, "reason": reason or "in_existing_corpus"})
            continue

        matched_idx: int | None = None
        match_reason = ""

        if paper.doi and paper.doi in seen_dois:
            matched_idx = seen_dois[paper.doi]
            match_reason = f"batch_duplicate_doi:{paper.doi}"
        elif paper.pmid and paper.pmid in seen_pmids:
            matched_idx = seen_pmids[paper.pmid]
            match_reason = f"batch_duplicate_pmid:{paper.pmid}"
        else:
            norm_t = normalize_title(paper.title)
            for prev_norm, idx in seen_titles:
                if norm_t == prev_norm or (
                    len(norm_t) > 20
                    and title_jaccard_similarity(norm_t, prev_norm) >= similarity_threshold
                ):
                    matched_idx = idx
                    match_reason = "batch_duplicate_title"
                    break

        if matched_idx is not None:
            existing = accepted[matched_idx]
            # Upgrade preprint -> peer-reviewed if the newly seen record is peer-reviewed
            if paper.peer_reviewed and not existing.peer_reviewed:
                paper.provenance["merged_from"] = existing.source_adapter
                accepted[matched_idx] = paper
                if paper.doi:
                    seen_dois[paper.doi] = matched_idx
                if paper.pmid:
                    seen_pmids[paper.pmid] = matched_idx
            elif not existing.pmid and paper.pmid:
                existing.pmid = paper.pmid
                seen_pmids[paper.pmid] = matched_idx
            skipped.append({"title": paper.title, "reason": match_reason})
            continue

        new_idx = len(accepted)
        accepted.append(paper)
        if paper.doi:
            seen_dois[paper.doi] = new_idx
        if paper.pmid:
            seen_pmids[paper.pmid] = new_idx
        seen_titles.append((normalize_title(paper.title), new_idx))

    return accepted, skipped
