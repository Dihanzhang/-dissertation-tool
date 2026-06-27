"""
Safe text splitter for oversized Module 1 submissions.

Splits at paragraph boundaries first, then sentence boundaries.
Never splits inside a citation span.
"""

from __future__ import annotations

import re

from .module3_citation_matcher import parse_citations


def count_words(text: str) -> int:
    return len(text.split())


def _citation_char_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) char spans of all citations in text."""
    spans = []
    for c in parse_citations(text):
        start = c.position_in_para
        end = start + len(c.raw)
        spans.append((start, end))
    return spans


def _inside_citation(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def estimate_chunks(text: str, word_cap: int) -> int:
    """Return how many chunks the text would split into."""
    import math
    return math.ceil(count_words(text) / word_cap)


def split_into_chunks(text: str, word_cap: int) -> list[str]:
    """
    Split text into ≤word_cap-word chunks.

    Priority order for split points:
      1. Paragraph boundaries (\\n\\n)
      2. Sentence boundaries (. ! ? followed by whitespace)

    Never splits inside a citation span (Author, Year).
    """
    if count_words(text) <= word_cap:
        return [text]

    # Split on paragraph separators
    paragraphs = re.split(r'(\n\n+)', text)  # keep separators
    # Reconstruct paragraph units with their trailing separator
    para_units: list[str] = []
    i = 0
    while i < len(paragraphs):
        chunk = paragraphs[i]
        sep = paragraphs[i + 1] if i + 1 < len(paragraphs) and paragraphs[i + 1].startswith('\n') else ''
        if not chunk.startswith('\n'):
            para_units.append(chunk + sep)
        i += 1 if not sep else 2

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for unit in para_units:
        unit_words = count_words(unit)

        if unit_words > word_cap:
            # Single paragraph too large — must split at sentence level
            if current:
                chunks.append(''.join(current).strip())
                current = []
                current_words = 0
            chunks.extend(_split_at_sentences(unit.strip(), word_cap))
            continue

        if current_words + unit_words > word_cap and current:
            chunks.append(''.join(current).strip())
            current = []
            current_words = 0

        current.append(unit)
        current_words += unit_words

    if current:
        chunks.append(''.join(current).strip())

    return [c for c in chunks if c.strip()]


def _split_at_sentences(para: str, word_cap: int) -> list[str]:
    """Split an oversized paragraph at safe sentence boundaries."""
    cite_spans = _citation_char_spans(para)

    # Find positions right after sentence-ending punctuation
    boundary_positions: list[int] = []
    for m in re.finditer(r'(?<=[.!?])\s+', para):
        pos = m.start()
        if not _inside_citation(pos, cite_spans):
            boundary_positions.append(pos)

    if not boundary_positions:
        # Cannot split safely — return as single chunk
        return [para]

    chunks: list[str] = []
    current_start = 0

    for bp in boundary_positions:
        segment = para[current_start:bp]
        if count_words(para[current_start:]) <= word_cap:
            break
        if count_words(segment) >= word_cap:
            chunks.append(segment.strip())
            current_start = bp

    remainder = para[current_start:].strip()
    if remainder:
        chunks.append(remainder)

    return [c for c in chunks if c.strip()]
