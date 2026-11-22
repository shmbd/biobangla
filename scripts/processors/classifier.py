from __future__ import annotations

import re
from typing import Any

from scripts.models import StandardizedPaper, StudyModel

BIOLOGY_CORE_SIGNALS = {
    "cell", "cells", "cellular", "gene", "genes", "genetic", "genome", "genomic",
    "dna", "rna", "mrna", "protein", "proteins", "enzyme", "bacteria", "bacterial",
    "virus", "viral", "fungi", "microbiome", "microbial", "immune", "antibody",
    "vaccine", "t-cell", "cytokine", "species", "organism", "ecology", "ecosystem",
    "biodiversity", "marine", "coral", "ocean", "plant", "photosynthesis", "crop",
    "arabidopsis", "animal", "vertebrate", "invertebrate", "evolution", "phylogeny",
    "mutation", "crispr", "clinical", "biomedical", "neuron", "stem cell", "tissue",
    "cancer", "tumor", "metabolism", "antibiotic", "pathogen", "symbiosis", "fossil",
}

NON_BIOLOGY_EXCLUSIONS = {
    "astrophysics", "black hole", "superconductor", "quantum gravity",
    "cosmology", "semiconductor fabrication", "cryptocurrency", "blockchain",
}


def classify_paper(
    paper: StandardizedPaper, categories_config: dict[str, Any]
) -> StandardizedPaper:
    """
    Classifies biological relevance, assigns one of the 10 biobangla categories,
    verifies preprint/review status, and detects study model (in-vitro, animal, human, etc.).
    """
    haystack = f"{paper.title} {paper.abstract} {paper.journal}".lower()

    # 1. Check biological relevance
    has_exclusion = any(ex in haystack for ex in NON_BIOLOGY_EXCLUSIONS)
    bio_hits = sum(1 for kw in BIOLOGY_CORE_SIGNALS if kw in haystack)
    paper.is_biological = (bio_hits >= 1) and not (has_exclusion and bio_hits < 2)

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
        if re.search(r"\b(systematic review|meta-analysis|a review of)\b", haystack):
            paper.research_type = "review"

    # 3. Score against the 10 configured categories
    default_cat = str(categories_config.get("default_category", "biomedical-science"))
    best_slug = default_cat
    best_score = 0

    for cat in categories_config.get("categories") or []:
        slug = str(cat.get("slug", "")).strip()
        keywords = cat.get("keywords") or []
        score = 0
        for kw in keywords:
            kw_low = str(kw).lower()
            if kw_low in paper.title.lower():
                score += 3
            if kw_low in paper.abstract.lower():
                score += 1
        if score > best_score and slug:
            best_score = score
            best_slug = slug

    paper.category = best_slug

    # 4. Infer study model (distinguishing in-vitro, animal, human clinical, observational, etc.)
    paper.study_model = infer_study_model(haystack, paper.research_type)
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
