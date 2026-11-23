from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from scripts.collectors.base import strip_markup
from scripts.http_client import PoliteHttpClient
from scripts.models import StandardizedPaper

logger = logging.getLogger("biobangla.fulltext")

MAX_EXCERPT_CHARS = 10000


def parse_jats_fulltext_xml(xml_text: str, max_chars: int = MAX_EXCERPT_CHARS) -> str:
    """
    Extracts structured scientific sections (Introduction, Methods, Results, Discussion,
    Limitations/Conclusions) from official Europe PMC Open Access JATS XML.
    Never extracts raw reference tables or copyrighted figure binaries.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""

    body = root.find(".//body")
    if body is None:
        return ""

    sections_out: list[str] = []
    total_len = 0

    # Iterate top-level <sec> elements inside <body>
    top_secs = body.findall("./sec") or body.findall(".//sec")
    for sec in top_secs:
        title_el = sec.find("./title")
        sec_title = strip_markup("".join(title_el.itertext())) if title_el is not None else ""
        sec_lower = sec_title.lower()

        # Skip supplementary/acknowledgements/funding/competing-interests noise
        if any(
            skip in sec_lower
            for skip in (
                "acknowledg",
                "funding",
                "competing interest",
                "conflict of interest",
                "supplementary",
                "author contribution",
                "data availability",
                "ethics declaration",
            )
        ):
            continue

        paragraphs: list[str] = []
        for p_el in sec.findall(".//p"):
            p_text = strip_markup("".join(p_el.itertext()))
            if len(p_text) >= 40:
                paragraphs.append(p_text)
            if sum(len(x) for x in paragraphs) >= 2400:
                break

        if not paragraphs:
            continue

        joined = "\n".join(paragraphs)[:2500]
        header = f"[{sec_title}]" if sec_title else "[Article Section]"
        chunk = f"{header}\n{joined}"
        sections_out.append(chunk)
        total_len += len(chunk)
        if total_len >= max_chars:
            break

    return "\n\n".join(sections_out)[:max_chars].strip()


def enrich_with_open_access_fulltext(
    paper: StandardizedPaper,
    http_client: PoliteHttpClient,
    rate_limit_per_second: float = 2.0,
) -> StandardizedPaper:
    """
    When an article has an Open Access PMCID in Europe PMC (or resolvable via DOI),
    fetches the permitted full-text JATS XML so the AI journalist reads the full paper
    (background, methods, results, discussion, limitations) rather than only the abstract.
    Never bypasses paywalls on closed-access articles.
    """
    if paper.article_body_excerpt:
        return paper

    pmcid = (paper.pmcid or "").strip()

    # Resolve PMCID via Europe PMC if DOI is present and PMCID wasn't populated yet
    if not pmcid and paper.doi:
        try:
            lookup = http_client.get_json(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={
                    "query": f'DOI:"{paper.doi}"',
                    "resultType": "lite",
                    "format": "json",
                    "pageSize": 1,
                },
                rate_limit_per_second=rate_limit_per_second,
            )
            results = lookup.get("resultList", {}).get("result", [])
            if results:
                first = results[0]
                if first.get("isOpenAccess") == "Y" and first.get("pmcid"):
                    pmcid = str(first["pmcid"]).strip()
                    paper.pmcid = pmcid
                    paper.is_open_access = True
        except Exception as exc:
            logger.debug("PMCID lookup skipped for DOI %s: %s", paper.doi, exc)

    if not pmcid or not pmcid.upper().startswith("PMC"):
        paper.provenance["content_depth"] = "abstract_only"
        return paper

    xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    try:
        xml_text = http_client.get_text(
            xml_url,
            headers={"Accept": "application/xml, text/xml"},
            rate_limit_per_second=rate_limit_per_second,
            check_robots=False,
        )
        excerpt = parse_jats_fulltext_xml(xml_text)
        if excerpt:
            paper.article_body_excerpt = excerpt
            paper.provenance["content_depth"] = "full_text_open_access_xml"
            logger.info(
                "Read full open-access article XML for %s (%d chars)",
                pmcid,
                len(excerpt),
            )
        else:
            paper.provenance["content_depth"] = "abstract_only"
    except Exception as exc:
        logger.debug("FullTextXML not available for %s: %s", pmcid, exc)
        paper.provenance["content_depth"] = "abstract_only"

    return paper
