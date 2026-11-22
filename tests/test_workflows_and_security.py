from __future__ import annotations

from pathlib import Path
import re
import yaml

PINNED_ACTION_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def test_github_actions_workflows_are_valid_pinned_and_least_privilege() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    wf_dir = repo_root / ".github" / "workflows"
    wf_files = sorted(wf_dir.glob("*.yml"))
    assert len(wf_files) >= 4, "Expected collect.yml, process.yml, deploy.yml, and ci.yml"

    expected_names = {"collect.yml", "process.yml", "deploy.yml", "ci.yml"}
    assert expected_names.issubset({f.name for f in wf_files})

    for wf_path in wf_files:
        doc = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        assert isinstance(doc, dict), f"Invalid YAML in {wf_path.name}"
        assert "permissions" in doc, f"Missing least-privilege permissions in {wf_path.name}"
        assert "concurrency" in doc, f"Missing concurrency control in {wf_path.name}"

        # PyYAML parses bare `on:` as boolean True or string "on"
        triggers = doc.get("on") or doc.get(True)
        assert triggers is not None, f"Missing triggers in {wf_path.name}"
        assert "workflow_dispatch" in triggers, f"Missing manual workflow_dispatch in {wf_path.name}"

        jobs = doc.get("jobs") or {}
        for job_name, job_cfg in jobs.items():
            for step in job_cfg.get("steps") or []:
                uses = step.get("uses")
                if uses:
                    assert PINNED_ACTION_RE.match(uses.strip()), (
                        f"Unpinned action '{uses}' in {wf_path.name} ({job_name}); "
                        "must use 40-char immutable SHA."
                    )
