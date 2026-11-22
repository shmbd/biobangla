from __future__ import annotations

import logging
from typing import Any
import xml.etree.ElementTree as ET

from scripts.collectors.base import (
    BaseCollector,
    normalize_doi,
    normalize_iso_date,
    strip_markup,
)
from scripts.models import PublicationStatus, ResearchType, StandardizedPaper

logger = logging.getLogger("biobangla.rss")

ATOM_NS = "{http://www.w3.org/2005/Atom}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"


class RssFeedCollector(BaseCollector):
    """Configurable RSS 2.0 & Atom 1.0 scientific feed collector."""

    source_key = "rss_feeds"

    def collect(self, max_items: int = 15) -> list[StandardizedPaper]:
        feeds = self.config.get("feeds") or []
        rate = float(self.config.get("rate_limit_per_second", 1.0))
        collected: list[StandardizedPaper] = []

        for feed_cfg in feeds:
            url = str(feed_cfg.get("url", "")).strip()
            if not url:
                continue
            try:
                xml_text = self.http.get_text(
                    url, rate_limit_per_second=rate, check_robots=True
                )
                items = self.parse_feed_xml(xml_text, feed_cfg)
                collected.extend(items[:max_items])
            except Exception as exc:
                logger.warning("RSS feed %s failed: %s", url, exc)
        return collected[:max_items]

    def parse_feed_xml(
        self, xml_text: str, feed_cfg: dict[str, Any]
    ) -> list[StandardizedPaper]:
        root = ET.fromstring(xml_text)
        journal = str(feed_cfg.get("journal") or feed_cfg.get("name") or "Scientific Feed")
        peer_reviewed = bool(feed_cfg.get("peer_reviewed", True))
        default_license = str(feed_cfg.get("default_license", "Unknown"))
        is_preprint_feed = not peer_reviewed

        papers: list[StandardizedPaper] = []

        # Atom 1.0 (<feed><entry>...)
        atom_entries = root.findall(f".//{ATOM_NS}entry") or root.findall(".//entry")
        if atom_entries:
            for entry in atom_entries:
                title = strip_markup(
                    entry.findtext(f"{ATOM_NS}title") or entry.findtext("title")
                )
                summary = strip_markup(
                    entry.findtext(f"{ATOM_NS}summary")
                    or entry.findtext(f"{ATOM_NS}content")
                    or entry.findtext("summary")
                    or entry.findtext("content")
                )
                link = ""
                for link_el in entry.findall(f"{ATOM_NS}link") + entry.findall("link"):
                    href = link_el.attrib.get("href", "").strip()
                    rel = link_el.attrib.get("rel", "alternate")
                    if href and rel in ("alternate", ""):
                        link = href
                        break

                entry_id = (
                    entry.findtext(f"{ATOM_NS}id") or entry.findtext("id") or link
                )
                doi = normalize_doi(entry_id) or normalize_doi(link) or normalize_doi(summary)
                pub_raw = (
                    entry.findtext(f"{ATOM_NS}published")
                    or entry.findtext(f"{ATOM_NS}updated")
                    or entry.findtext("published")
                    or entry.findtext("updated")
                )

                authors = [
                    strip_markup(
                        a.findtext(f"{ATOM_NS}name") or a.findtext("name")
                    )
                    for a in (entry.findall(f"{ATOM_NS}author") + entry.findall("author"))
                ]
                authors = [a for a in authors if a] or [f"{journal} Authors"]

                if not title or not summary or not (link or doi):
                    continue

                research_type: ResearchType = (
                    "preprint" if is_preprint_feed else "original-research"
                )
                pub_status: PublicationStatus = (
                    "preprint" if is_preprint_feed else "peer-reviewed"
                )

                papers.append(
                    StandardizedPaper(
                        title=title,
                        abstract=summary,
                        authors=authors,
                        journal=journal,
                        published_date=normalize_iso_date(pub_raw),
                        source_url=link or f"https://doi.org/{doi}",
                        source_adapter=self.source_key,
                        doi=doi,
                        research_type=research_type,
                        peer_reviewed=peer_reviewed,
                        publication_status=pub_status,
                        license=default_license,
                        is_open_access="cc" in default_license.lower(),
                        provenance={"source": "Atom Feed", "feed_id": feed_cfg.get("id")},
                    )
                )
            return papers

        # RSS 2.0 (<rss><channel><item>...)
        for item in root.findall(".//item"):
            title = strip_markup(item.findtext("title"))
            description = strip_markup(item.findtext("description"))
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip()
            dc_id = (item.findtext(f"{DC_NS}identifier") or "").strip()
            doi = (
                normalize_doi(dc_id)
                or normalize_doi(guid)
                or normalize_doi(link)
                or normalize_doi(description)
            )
            pub_raw = item.findtext("pubDate") or item.findtext(f"{DC_NS}date")
            creators = [
                strip_markup(c.text)
                for c in item.findall(f"{DC_NS}creator")
                if c.text
            ] or [f"{journal} Authors"]

            if not title or not description or not (link or doi):
                continue

            research_type = "preprint" if is_preprint_feed else "original-research"
            pub_status = "preprint" if is_preprint_feed else "peer-reviewed"

            papers.append(
                StandardizedPaper(
                    title=title,
                    abstract=description,
                    authors=creators,
                    journal=journal,
                    published_date=normalize_iso_date(pub_raw),
                    source_url=link or f"https://doi.org/{doi}",
                    source_adapter=self.source_key,
                    doi=doi,
                    research_type=research_type,
                    peer_reviewed=peer_reviewed,
                    publication_status=pub_status,
                    license=default_license,
                    is_open_access="cc" in default_license.lower(),
                    provenance={"source": "RSS Feed", "feed_id": feed_cfg.get("id")},
                )
            )
        return papers
