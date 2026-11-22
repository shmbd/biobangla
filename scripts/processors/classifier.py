from __future__ import annotations

import re
from typing import Any

from scripts.models import StandardizedPaper, StudyModel

BIOLOGY_CORE_SIGNALS = (
    "cell", "cells", "cellular", "gene", "genes", "genetic", "genetics", "genome",
    "genomic", "genomics", "dna", "rna", "mrna", "trna", "rrna", "protein", "proteins",
    "proteome", "enzyme", "enzymes", "bacteria", "bacterial", "bacterium", "virus",
    "viral", "virology", "fungi", "fungal", "microbiome", "microbiota", "microbial",
    "immune", "immunity", "immunology", "antibody", "antibodies", "antigen", "vaccine",
    "t-cell", "b-cell", "cytokine", "macrophage", "species", "organism", "organisms",
    "ecology", "ecological", "ecosystem", "biodiversity", "marine", "coral", "reef",
    "phytoplankton", "botany", "photosynthesis", "chloroplast", "stomata", "arabidopsis",
    "crop", "crops", "seedling", "zoology", "vertebrate", "invertebrate", "mammalian",
    "evolution", "evolutionary", "phylogeny", "phylogenetic", "mutation", "mutations",
    "crispr", "cas9", "biomedical", "neuron", "neurons", "neural circuit", "synaptic",
    "stem cell", "organoid", "tissue", "cancer", "tumor", "oncology", "metabolism",
    "metabolic", "antibiotic", "pathogen", "pathogens", "symbiosis", "fossil", "hominin",
    "transcription", "chromatin", "epigenetic", "mice", "murine", "zebrafish", "drosophila",
)

NON_BIOLOGY_EXCLUSIONS = (
    "astrophysics", "black hole", "superconductor", "quantum gravity",
    "cosmology", "semiconductor", "cryptocurrency", "blockchain",
    "physics-informed neural", "weighted k-out-of-n", "reliability engineering",
    "finite element", "power plant", "photovoltaic", "wireless sensor",
    "audit transformation", "supply chain", "portland cement", "reinforced concrete",
)

_BIO_SIGNAL_PATTERNS = [
    (kw, re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE))
    for kw in BIOLOGY_CORE_SIGNALS
]
_EXCLUSION_PATTERNS = [
    re.compile(rf"\b{re.escape(ex)}\b", re.IGNORECASE)
    for ex in NON_BIOLOGY_EXCLUSIONS
]


def classify_paper(
    paper: StandardizedPaper, categories_config: dict[str, Any]
) -> StandardizedPaper:
    """
    Classifies biological relevance using strict word-boundary matching, assigns one of
    the 10 biobangla categories, verifies preprint/review status, and detects study model.
    """
    haystack = f"{paper.title} {paper.abstract} {paper.journal}"
    haystack_lower = haystack.lower()

    # 1. Check biological relevance with whole-word boundaries (prevents 'rna' matching 'journal'
    #    or 'gene' matching 'general')
    has_exclusion = any(pat.search(haystack) for pat in _EXCLUSION_PATTERNS)
    bio_hits = sum(1 for _, pat in _BIO_SIGNAL_PATTERNS if pat.search(haystack))

    dedicated_bio_source = paper.source_adapter in (
        "plos", "biorxiv", "pubmed", "europe_pmc", "rss_feeds"
    )
    min_required_hits = 1 if dedicated_bio_source else 2
    paper.is_biological = (bio_hits >= min_required_hits) and not has_exclusion

    # 2. Enforce preprint vs review vs original-research classification
    journal_lower = paper.journal.lower()
    if (
        "biorxiv" in journal_lower
        or "medrxiv" in journal_lower
        or "preprint" in journal_lower
        or paper.publication_status == "preprint"
        or paper.research_type == "preprint"
    ):
        paper.research_type = "preprint"
        paper.publication_status = "preprint"
        paper.peer_reviewed = False
    elif paper.research_type == "original-research":
        if re.search(r"\b(systematic review|meta-analysis|a review of)\b", haystack_lower):
            paper.research_type = "review"

    # 3. Score against the 10 configured categories using word boundaries
    default_cat = str(categories_config.get("default_category", "biomedical-science"))
    best_slug = default_cat
    best_score = 0

    for cat in categories_config.get("categories") or []:
        slug = str(cat.get("slug", "")).strip()
        keywords = cat.get("keywords") or []
        score = 0
        for kw in keywords:
            kw_pat = re.compile(rf"\b{re.escape(str(kw))}\b", re.IGNORECASE)
            if kw_pat.search(paper.title):
                score += 3
            if kw_pat.search(paper.abstract):
                score += 1
        if score > best_score and slug:
            best_score = score
            best_slug = slug

    paper.category = best_slug

    # 4. Infer study model (distinguishing in-vitro, animal, human clinical, observational, etc.)
    paper.study_model = infer_study_model(haystack_lower, paper.research_type)
    return paper


def infer_study_model(text_lower: str, research_type: str) -> StudyModel:
    if research_type in ("review", "editorial"):
        return "multi-study"
    if any(
        term in text_lower
        for term in (
            "randomized controlled trial",
            "phase i",
            "phase ii",
            "phase iii",
            "clinical trial",
            "patients treated",
        )
    ):
        return "human-clinical"
    if any(
        term in text_lower
        for term in ("cohort study", "epidemiological", "cross-sectional", "observational study")
    ):
        return "human-observational"
    if any(
        term in text_lower
        for term in ("mice", "mouse model", "murine", "zebrafish", "drosophila", "rat model", "in vivo")
    ):
        return "animal"
    if any(
        term in text_lower
        for term in ("in vitro", "cell line", "cell culture", "organoid", "purified protein")
    ):
        return "in-vitro"
    if any(
        term in text_lower
        for term in ("field survey", "agroecosystem", "reef", "forest plot", "wild population")
    ):
        return "field-ecology"
    if any(
        term in text_lower
        for term in ("genome assembly", "sequencing", "phylogenetic", "metagenomic", "in silico")
    ):
        return "computational"
    return "multi-study"
