"""
Citation lock for Module 1.

Before the LLM call: extract all citation spans.
After the LLM call: verify every citation is still present, character-identical,
and no new citations were added.

This is enforced in code — not relied upon from the prompt alone.
"""

from __future__ import annotations

from .module3_citation_matcher import parse_citations


def extract_citation_spans(text: str) -> list[str]:
    """Return the raw citation strings found in text, deduplicated but order-preserving."""
    seen: set[str] = set()
    result: list[str] = []
    for c in parse_citations(text):
        if c.raw not in seen:
            seen.add(c.raw)
            result.append(c.raw)
    return result


def verify_citations_preserved(
    original: str,
    revised: str,
) -> tuple[bool, list[str]]:
    """
    Verify:
      1. Every citation in original is present verbatim in revised.
      2. No citation in revised was absent from original (LLM added one).

    Returns (ok, problems_list).
    """
    original_spans = extract_citation_spans(original)
    revised_spans = extract_citation_spans(revised)

    problems: list[str] = []

    for span in original_spans:
        if span not in revised:
            problems.append(f"Citation dropped or altered: '{span}'")

    original_set = set(original_spans)
    for span in revised_spans:
        if span not in original_set:
            problems.append(f"Citation added by LLM: '{span}'")

    return (len(problems) == 0, problems)
