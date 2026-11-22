from __future__ import annotations

from pathlib import Path

from scripts.config_loader import load_yaml_config
from scripts.models import StandardizedPaper
from scripts.processors.classifier import classify_paper
from scripts.processors.deduplicator import ExistingCorpusIndex, deduplicate_papers


def _make_paper(**overrides) -> StandardizedPaper:
    defaults = {
        "title": "CRISPR-Cas9 gene editing in bacterial phage immunity",
        "abstract": "We study CRISPR Cas9 endonuclease activity in vitro using purified protein.",
        "authors": ["A. Researcher"],
        "journal": "PLOS Biology",
        "published_date": "2026-09-10",
        "source_url": "https://doi.org/10.1371/journal.pbio.1000001",
        "source_adapter": "plos",
        "doi": "10.1371/journal.pbio.1000001",
        "peer_reviewed": True,
        "publication_status": "peer-reviewed",
        "research_type": "original-research",
    }
    defaults.update(overrides)
    return StandardizedPaper(**defaults)


def test_deduplication_by_doi_pmid_and_preprint_upgrade() -> None:
    preprint_ver = _make_paper(
        title="Novel coral symbiont thermal adaptation in reef ecosystems",
        doi="10.1101/2026.04.01.111222",
        journal="bioRxiv (Preprint Server)",
        research_type="preprint",
        peer_reviewed=False,
        publication_status="preprint",
    )
    published_ver = _make_paper(
        title="Novel coral symbiont thermal adaptation in reef ecosystems!",
        doi="10.1371/journal.pbio.3008888",
        pmid="39887766",
        journal="PLOS Biology",
        research_type="original-research",
        peer_reviewed=True,
        publication_status="peer-reviewed",
    )
    duplicate_doi = _make_paper(
        title="Different punctuation title",
        doi="https://doi.org/10.1371/JOURNAL.PBIO.3008888",
    )

    accepted, skipped = deduplicate_papers([preprint_ver, published_ver, duplicate_doi])
    assert len(accepted) == 1
    assert len(skipped) == 2
    # Must upgrade to the peer-reviewed journal version
    assert accepted[0].peer_reviewed is True
    assert accepted[0].journal == "PLOS Biology"


def test_existing_corpus_index_blocks_already_published_doi() -> None:
    articles_dir = Path(__file__).resolve().parent.parent / "content" / "articles"
    corpus = ExistingCorpusIndex.from_articles_dir(articles_dir)

    duplicate_crispr = _make_paper(
        title="Programmable dual-RNA-guided DNA endonuclease",
        doi="10.1126/science.1225829",
    )
    accepted, skipped = deduplicate_papers([duplicate_crispr], existing_index=corpus)
    assert len(accepted) == 0
    assert len(skipped) == 1
    assert "duplicate_doi" in skipped[0]["reason"]


def test_classifier_assigns_categories_study_models_and_filters_non_biology() -> None:
    categories_cfg = load_yaml_config("categories.yaml")

    marine_paper = _make_paper(
        title="Ocean acidification alters phytoplankton and coral reef calcifiers",
        abstract="Field survey across tropical reef ecosystems reveals marine plankton shifts.",
    )
    classify_paper(marine_paper, categories_cfg)
    assert marine_paper.is_biological is True
    assert marine_paper.category == "marine-biology"
    assert marine_paper.study_model == "field-ecology"

    in_vitro_paper = _make_paper(
        title="CRISPR-Cas9 metabolic engineering of synthetic biology biosensors",
        abstract="In vitro cell culture experiments demonstrate high specificity.",
    )
    classify_paper(in_vitro_paper, categories_cfg)
    assert in_vitro_paper.category == "biotechnology"
    assert in_vitro_paper.study_model == "in-vitro"

    astro_paper = _make_paper(
        title="Superconductor quantum gravity fluctuations near a black hole",
        abstract="Astrophysics and cosmology simulation of event horizons.",
    )
    classify_paper(astro_paper, categories_cfg)
    assert astro_paper.is_biological is False
