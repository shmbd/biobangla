from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import pytest

from scripts.ai.provider import (
    AIProviderError,
    MockJournalismProvider,
    create_ai_provider_from_env,
)
from scripts.ai.validator import ArticleQualityValidator
from scripts.ai.writer import BanglaScienceWriter, build_stable_slug
from scripts.config_loader import load_all_configs
from tests.test_license_and_validator import _sample_paper


def test_ai_provider_env_requires_key_for_live_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    with pytest.raises(AIProviderError):
        create_ai_provider_from_env()

    monkeypatch.setenv("AI_PROVIDER", "mock")
    provider = create_ai_provider_from_env()
    assert provider.provider_name == "mock"
    assert provider.is_mock is True


def test_writer_and_validator_hold_mock_draft_in_review() -> None:
    configs = load_all_configs()
    writer = BanglaScienceWriter(
        provider=MockJournalismProvider(),
        glossary_config=configs["glossary"],
        editorial_rules=configs["editorial_rules"],
    )
    validator = ArticleQualityValidator(configs["editorial_rules"])

    paper = _sample_paper(doi="10.1371/journal.pbio.3007777")
    draft = writer.write_article(paper)
    assert draft.is_sample is True
    assert build_stable_slug(paper) == draft.slug

    report = validator.validate(draft)
    # Mock drafts must never auto-publish as PASS; they are held in REVIEW
    assert report.outcome == "REVIEW"


def test_run_process_cli_dry_run_end_to_end(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    candidate_file = tmp_path / "candidates.json"
    candidate_file.write_text(
        json.dumps(
            {
                "summary": {"total_raw_records": 1},
                "candidates": [_sample_paper(doi="10.1371/journal.pbio.3005555").to_dict()],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_process.py"),
            "--input",
            str(candidate_file),
            "--state-dir",
            str(tmp_path / "state"),
            "--dry-run",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
