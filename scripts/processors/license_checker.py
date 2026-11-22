from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.models import StandardizedPaper


@dataclass
class LicenseDecision:
    normalized_license: str
    is_open_access: bool
    allow_metadata_and_original_summary: bool
    allow_media_reuse: bool
    notes: str


def evaluate_license(
    paper: StandardizedPaper, editorial_rules: dict[str, Any]
) -> LicenseDecision:
    """
    Checks reuse license permissions.
    - Factual metadata + original Bangla journalistic analysis is permitted when a valid public source URL exists,
      WITHOUT copying copyrighted prose or bypassing paywalls.
    - Image/figure reuse is STRICTLY forbidden unless the license explicitly matches an open media license
      (CC0, CC BY, CC BY-SA, Public Domain) without ND/NC media restrictions.
    """
    raw = (paper.license or "Unknown").strip()
    upper = raw.upper().replace("_", "-")

    allowed_list = [
        str(x).upper().replace("_", "-")
        for x in (editorial_rules.get("license_policy", {}).get("allowed_media_licenses") or [])
    ]

    has_nd_or_nc = ("NC" in upper) or ("ND" in upper)

    is_open_media = False
    normalized = raw or "Unknown"

    if "CC0" in upper or "PUBLIC DOMAIN" in upper:
        normalized = "CC0 / Public Domain"
        is_open_media = True
    elif ("CC BY-SA" in upper or "CC-BY-SA" in upper) and not has_nd_or_nc:
        normalized = "CC BY-SA 4.0"
        is_open_media = True
    elif ("CC BY" in upper or "CC-BY" in upper) and not has_nd_or_nc:
        normalized = "CC BY 4.0"
        is_open_media = True
    elif any(al == upper for al in allowed_list) and not has_nd_or_nc:
        is_open_media = True

    paper.license = normalized
    paper.is_open_access = is_open_media or paper.is_open_access
    paper.allow_media_reuse = is_open_media

    has_valid_url = paper.source_url.startswith("https://") or paper.source_url.startswith("http://")

    return LicenseDecision(
        normalized_license=normalized,
        is_open_access=paper.is_open_access,
        allow_metadata_and_original_summary=has_valid_url,
        allow_media_reuse=is_open_media,
        notes=(
            "উন্মুক্ত লাইসেন্স: উৎস স্বীকৃতিসহ চিত্র ও মেটাডেটা ব্যবহারযোগ্য।"
            if is_open_media
            else "সংরক্ষিত প্রকাশনা/প্রিপ্রিন্ট লাইসেন্স: কেবল মেটাডেটা, DOI ও মৌলিক বাংলা ব্যাখ্যা অনুমোদিত; প্রকাশকের কোনো ছবি বা হুবহু অনুবাদ নিষিদ্ধ।"
        ),
    )
