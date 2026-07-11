from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.modules.module2_apa_checker import check_paragraphs
from backend.app.modules.module3_citation_matcher import run_citation_check_paragraphs
from backend.app.modules.prose_extractor import extract_prose


ROOT = Path(__file__).resolve().parent

PROSE_CONFIG = {
    "min_sentences_per_paragraph": 3,
    "numeral_threshold": 10,
    "flag_repeated_narrative_citations": True,
    "flag_first_person_pronouns": False,
}

HEADING_CONFIG = {
    "flag_heading_without_body": True,
    "flag_skipped_heading_levels": True,
}

CITATION_BUCKETS = [
    "missing_references",
    "uncited_references",
    "year_mismatches",
    "spelling_mismatches",
    "co_author_only_matches",
]


def detected_rule_ids(docx_path: Path) -> set[str]:
    paragraphs = extract_prose(Document(docx_path))
    reference_text = "\n".join(p.raw_text for p in paragraphs if p.is_reference_entry)

    apa_findings = check_paragraphs(paragraphs, PROSE_CONFIG, HEADING_CONFIG)
    citation_result = run_citation_check_paragraphs(paragraphs, reference_text)

    rule_ids = {finding.rule_id for finding in apa_findings}
    for bucket in CITATION_BUCKETS:
        if getattr(citation_result, bucket):
            rule_ids.add(bucket)
    return rule_ids


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    failed = False

    for case in manifest["cases"]:
        docx_path = ROOT / "docs" / case["file"]
        expected = {
            rule
            for rule in case["expected_rule_coverage"]
            if not rule.startswith("should_not_")
        }
        actual = detected_rule_ids(docx_path)
        missing = sorted(expected - actual)

        print(case["file"])
        print(f"  expected: {len(expected)} actual: {len(actual)} missing: {missing}")

        if missing:
            failed = True
        if case["file"] == "06_false_positive_traps.docx" and actual:
            print(f"  unexpected false-positive rules: {sorted(actual)}")
            failed = True

    if failed:
        print("\nRegression check failed.")
        return 1

    print("\nRegression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
