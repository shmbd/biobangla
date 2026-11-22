from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml_config(filename: str, config_dir: Path | None = None) -> dict[str, Any]:
    target_dir = config_dir or CONFIG_DIR
    file_path = target_dir / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top-level of {file_path}")
    return data


def load_all_configs(config_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    return {
        "sources": load_yaml_config("sources.yaml", config_dir),
        "categories": load_yaml_config("categories.yaml", config_dir),
        "glossary": load_yaml_config("glossary.yaml", config_dir),
        "editorial_rules": load_yaml_config("editorial_rules.yaml", config_dir),
    }
