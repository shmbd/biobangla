from __future__ import annotations

import email.message
import io
import urllib.error
import pytest

from scripts.collectors.biorxiv import BioRxivCollector
from scripts.collectors.crossref import CrossrefCollector
from scripts.collectors.europe_pmc import EuropePmcCollector
from scripts.collectors.plos import PlosCollector
from scripts.collectors.pubmed import PubMedCollector
from scripts.collectors.rss import RssFeedCollector
from scripts.http_client import AccessRestrictedError, PoliteHttpClient


class DummyHttpClient(PoliteHttpClient):
    def __init__(self) -> None:
        super().__init__(
            user_agent="biobangla-test/1.0",
            contact_email="test@example.org",
            respect_robots_txt=False,
            sleep_fn=lambda _: None,
        )


def test_europe_pmc_distinguishes_peer_reviewed_and_preprint() -> None:
    collector = EuropePmcCollector(DummyHttpClient(), {})
    sample_payload = {
        "resultList": {
            "result": [
                {
                    "id": "PMC12345",
                    "source": "MED",
                    "pmid": "39001122",
                    "pmcid": "PMC12345",
                    "doi": "10.1371/journal.pbio.3002500",
                    "title": "Bacterial phage defense systems in marine Vibrio",
                    "abstractText": "We characterize an anti-phage immune mechanism in marine bacteria.",
                    "authorString": "Rahman A, Sen S",
                    "journalTitle": "PLOS Biology",
                    "firstPublicationDate": "2026-08-14",
                    "isOpenAccess": "Y",
                    "license": "cc by",
                    "pubTypeList": {"pubType": ["research-article", "Journal Article"]},
                },
                {
                    "id": "PPR998877",
                    "source": "PPR",
                    "doi": "10.1101/2026.08.01.600123",
                    "title": "Preprint draft on single-cell transcriptomics",
                    "abstractText": "Preliminary single-cell RNA-seq atlas of zebrafish fin regeneration.",
                    "authorString": "Karim M",
                    "firstPublicationDate": "2026-08-18",
                    "isOpenAccess": "Y",
                    "pubTypeList": {"pubType": ["Preprint"]},
                },
            ]
        }
    }
    papers = collector.parse_response(sample_payload)
    assert len(papers) == 2

    journal_paper = papers[0]
    assert journal_paper.peer_reviewed is True
    assert journal_paper.publication_status == "peer-reviewed"
    assert journal_paper.doi == "10.1371/journal.pbio.3002500"

    preprint_paper = papers[1]
    assert preprint_paper.peer_reviewed is False
    assert preprint_paper.research_type == "preprint"
    assert preprint_paper.publication_status == "preprint"


def test_biorxiv_collector_never_marks_peer_reviewed() -> None:
    collector = BioRxivCollector(DummyHttpClient(), {})
    payload = {
        "collection": [
            {
                "doi": "10.1101/2026.07.10.555111",
                "title": "Evolutionary dynamics of plastid genomes in land plants",
                "authors": "Das, R.; Ahmed, T.",
                "date": "2026-07-11",
                "version": "2",
                "category": "evolutionary biology",
                "license": "cc_by_nc_nd",
                "abstract": "Comparative plastid genome analysis across 45 angiosperm lineages.",
            }
        ]
    }
    papers = collector.parse_response(payload)
    assert len(papers) == 1
    assert papers[0].peer_reviewed is False
    assert papers[0].research_type == "preprint"
    assert papers[0].publication_status == "preprint"
    assert papers[0].source_url.endswith("v2")


def test_pubmed_xml_parser_extracts_metadata_and_review_type() -> None:
    collector = PubMedCollector(DummyHttpClient(), {})
    xml_sample = """<?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>38112233</PMID>
          <Article>
            <Journal>
              <Title>Nature Immunology</Title>
              <JournalIssue>
                <PubDate><Year>2026</Year><Month>Sep</Month><Day>5</Day></PubDate>
              </JournalIssue>
            </Journal>
            <ArticleTitle>Memory T cell metabolism in chronic viral infection</ArticleTitle>
            <Abstract>
              <AbstractText>This review synthesizes metabolic checkpoints in CD8+ T cells.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author><LastName>Chowdhury</LastName><ForeName>Nadia</ForeName></Author>
            </AuthorList>
            <PublicationTypeList>
              <PublicationType>Journal Article</PublicationType>
              <PublicationType>Review</PublicationType>
            </PublicationTypeList>
          </Article>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1038/s41590-026-01999-x</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>"""

    papers = collector.parse_efetch_xml(xml_sample)
    assert len(papers) == 1
    assert papers[0].pmid == "38112233"
    assert papers[0].doi == "10.1038/s41590-026-01999-x"
    assert papers[0].research_type == "review"
    assert papers[0].published_date == "2026-09-05"
    assert papers[0].authors == ["Nadia Chowdhury"]


def test_crossref_strips_jats_xml_and_reads_cc_by_license() -> None:
    collector = CrossrefCollector(DummyHttpClient(), {})
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.7554/eLife.91234",
                    "type": "journal-article",
                    "title": ["Stomatal aperture regulation in <i>Arabidopsis thaliana</i>"],
                    "abstract": "<jats:p>Guard cells respond to abscisic acid signaling.</jats:p>",
                    "author": [{"given": "Farhana", "family": "Islam"}],
                    "container-title": ["eLife"],
                    "published-online": {"date-parts": [[2026, 6, 20]]},
                    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
                }
            ]
        }
    }
    papers = collector.parse_response(payload)
    assert len(papers) == 1
    assert "<jats:p>" not in papers[0].abstract
    assert "<i>" not in papers[0].title
    assert papers[0].license == "CC BY"
    assert papers[0].is_open_access is True


def test_plos_and_atom_rss_parsers() -> None:
    plos = PlosCollector(DummyHttpClient(), {"default_license": "CC BY 4.0"})
    plos_papers = plos.parse_response(
        {
            "response": {
                "docs": [
                    {
                        "id": "10.1371/journal.pgen.1011222",
                        "journal": "PLOS Genetics",
                        "publication_date": "2026-05-12T00:00:00Z",
                        "article_type": "Research Article",
                        "author_display": ["Amina Begum"],
                        "title_display": "Epigenetic chromatin remodeling in yeast",
                        "abstract": ["Chromatin remodeling complexes regulate transcription."],
                    }
                ]
            }
        }
    )
    assert len(plos_papers) == 1
    assert plos_papers[0].license == "CC BY 4.0"

    rss = RssFeedCollector(DummyHttpClient(), {})
    atom_xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Coral reef microbiome resilience</title>
        <id>https://doi.org/10.1371/journal.pbio.3009999</id>
        <link href="https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3009999" rel="alternate"/>
        <published>2026-08-01T00:00:00Z</published>
        <summary>Symbiotic bacteria buffer thermal stress in reef corals.</summary>
        <author><name>Tanvir Hasan</name></author>
      </entry>
    </feed>"""
    feed_papers = rss.parse_feed_xml(
        atom_xml,
        {"id": "plos_bio", "journal": "PLOS Biology", "peer_reviewed": True, "default_license": "CC BY 4.0"},
    )
    assert len(feed_papers) == 1
    assert feed_papers[0].doi == "10.1371/journal.pbio.3009999"


def test_http_client_refuses_403_paywall_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_urlopen(request, timeout=25):
        nonlocal calls
        calls += 1
        hdrs = email.message.Message()
        raise urllib.error.HTTPError(
            request.full_url, 403, "Forbidden Paywall", hdrs, io.BytesIO(b"")
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = DummyHttpClient()
    with pytest.raises(AccessRestrictedError):
        client.get_text("https://publisher.example.com/paywalled-article")
    assert calls == 1  # Never retries 403 blocks
