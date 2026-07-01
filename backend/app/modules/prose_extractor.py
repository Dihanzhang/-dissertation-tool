"""
Extract author-prose spans from a .docx document.

Returns a list of ProseParagraph objects — only paragraphs that are genuine
author prose, with inline quoted spans masked out.  Everything else (block
quotes, table cells, reference-list entries) is excluded before any rule runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from docx import Document
from docx.oxml.ns import qn


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ProseParagraph:
    """A paragraph of author prose, with quoted text replaced by placeholder."""
    index: int           # paragraph index in the document (0-based)
    style_name: str
    raw_text: str        # original unmasked text
    masked_text: str     # quoted spans replaced with QUOTE_MASK
    heading_level: Optional[int]  # 1-5 for APA headings, None if not a heading
    is_reference_entry: bool = False
    page_number: int = 1
    paragraph_number_on_page: int = 1


QUOTE_MASK = "\x00QUOTE\x00"

# Regex for inline quotation marks (straight and curly)
_INLINE_QUOTE_RE = re.compile(
    r'"[^"]*?"'          # straight double quotes
    r'|“[^”]*?”'  # curly "…"
)

# APA heading style names → heading level
_HEADING_STYLES = {
    "Heading 1": 1, "Heading 2": 2, "Heading 3": 3,
    "Heading 4": 4, "Heading 5": 5,
}

# Word built-in non-prose styles that should be skipped by prose rules.
# Title-page elements (Title, Subtitle, Author, Date) and navigation/caption styles
# use these names. Treat them as heading_level=0 so prose and heading rules skip them.
_SKIP_STYLES: set[str] = {
    "Title", "Subtitle", "Author", "Date",
    "TOC Heading", "TOC 1", "TOC 2", "TOC 3",
    "Caption", "Figure Caption", "Table Caption",
    "Endnote Text", "Footnote Text",
    "Header", "Footer",
    "List Paragraph", "List Bullet", "List Number",
    "Cover", "Cover Page",
}

# Heuristic for heading-like lines in Normal-styled paragraphs.
_HEADING_HEURISTIC_LIST_ITEM = re.compile(r'^[\d]+[.)]\s|^[-•*–]\s')
_HEADING_HEURISTIC_PAREN_YEAR = re.compile(r'\(\d{4}[a-z]?\)')

# Table and figure label pattern — "Table 1", "Figure 3" etc.
# These must never be classified as headings even when bold/centered.
_TABLE_FIGURE_LABEL_RE = re.compile(r'^(?:Table|Figure)\s+\d+\s*$', re.IGNORECASE)
_TERMINAL_PUNCT_RE = re.compile(r'[.!?]\s*$')


def _looks_like_heading(text: str) -> bool:
    """
    Text-only fallback — only catches ALL-CAPS section labels.
    Mixed-case short text is NOT treated as a heading here because too many
    non-heading elements (author names, dates, institutions) match that pattern.
    """
    stripped = text.strip()
    if not stripped or '\n' in stripped:
        return False
    if _HEADING_HEURISTIC_LIST_ITEM.match(stripped):
        return False
    if _HEADING_HEURISTIC_PAREN_YEAR.search(stripped):
        return False
    # Only ALL-CAPS short lines qualify (e.g. "ABSTRACT", "REFERENCES")
    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(stripped) <= 200:
        return True
    return False


def _all_runs_bold(para) -> bool:
    """Return True if every non-empty run in the paragraph is bold."""
    runs = [r for r in para.runs if r.text.strip()]
    return bool(runs) and all(r.bold for r in runs)


def _is_centered(para) -> bool:
    """Return True if the paragraph is centre-aligned."""
    try:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        return para.alignment == WD_ALIGN_PARAGRAPH.CENTER
    except Exception:
        return False

# Block-quote style names (Word built-in + common custom names)
_BLOCK_QUOTE_STYLES = {
    "Quote",
    "Intense Quote",
    "Block Text",
    "Block Quote",
    "Blockquote",
}

# Reference-section heading keywords
_REF_HEADING_KEYWORDS = re.compile(
    r"^\s*references?\s*$", re.IGNORECASE
)


def _is_block_quote(para) -> bool:
    """Return True if this paragraph should be treated as a block quotation."""
    style = para.style.name if para.style else ""
    if style in _BLOCK_QUOTE_STYLES:
        return True
    # Structural detection: left-indented paragraph
    pPr = para._p.find(qn("w:pPr"))
    if pPr is not None:
        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            left = ind.get(qn("w:left"), "0")
            try:
                if int(left) >= 720:   # 720 twips = 0.5 inch — APA block-quote indent
                    return True
            except ValueError:
                pass
    return False


def _heading_level(para) -> Optional[int]:
    """Return heading level for this paragraph, or None if it is body prose.

    Returns:
        0  — layout/skip element (title page, caption, TOC): not body prose but
             also not a real APA section heading; exempt from HED001/HED002.
        1–5 — real APA section heading (Heading 1–5 style or manually formatted).
        None — body prose; all prose rules apply.
    """
    style = para.style.name if para.style else ""

    # 1. Explicit Word heading styles (Heading 1–5)
    if style in _HEADING_STYLES:
        return _HEADING_STYLES[style]

    # 2. Known non-prose layout styles (Title, Subtitle, Author, Date, Caption…)
    #    Return 0: prose rules skip them AND they don't participate in HED001/HED002.
    if style in _SKIP_STYLES:
        return 0

    text = para.text.strip()
    if not text:
        return None

    # 3. Explicit table/figure label exclusion — never classify as a heading
    #    even if the paragraph is bold or centered ("Table 1", "Figure 3", etc.)
    if _TABLE_FIGURE_LABEL_RE.match(text):
        return 0

    # 4. XML-based formatting: manually formatted headings in Normal-style paragraphs.
    #    APA Level 1 = bold + centred.  APA Level 2 = bold + flush-left.
    #    Centering alone is insufficient (title-page elements are centred but not bold).
    if _is_centered(para) and _all_runs_bold(para) and len(text) <= 200:
        return 1

    # All runs bold but left-aligned → APA Level 2 equivalent heuristic.
    # Returning 2 instead of 1 prevents HED002 from firing when a Level-1 heading
    # is immediately followed by a bold flush-left subheading (a common dissertation
    # pattern that is correct APA 7 structure).
    if _all_runs_bold(para) and len(text) <= 200:
        return 2

    # 5. Text-only heuristic (last resort) — ALL-CAPS only
    if _looks_like_heading(text):
        return 1

    # 6. Title-page / preamble fragment: short paragraph with no terminal punctuation
    #    and no in-text citation. Catches author names, institution lines, degree
    #    programs, dates, and subtitles that use Normal style rather than a named
    #    title-page style. Treated as a layout element (level 0) so that PRF001 and
    #    other prose rules do not fire on them.
    if len(text.split()) <= 8 and not re.search(r'[.!?]', text):
        return 0

    return None


def _is_real_heading(p: ProseParagraph) -> bool:
    return p.heading_level is not None and p.heading_level >= 1


def _is_explicit_word_heading(p: ProseParagraph) -> bool:
    return p.style_name in _HEADING_STYLES


def _mask_inline_quotes(text: str) -> str:
    return _INLINE_QUOTE_RE.sub(QUOTE_MASK, text)


def _is_in_table(para) -> bool:
    """Return True if this paragraph lives inside a table cell."""
    parent = para._p.getparent()
    while parent is not None:
        if parent.tag == qn("w:tc"):
            return True
        parent = parent.getparent()
    return False


def _contains_page_break(para) -> bool:
    """Return True if the paragraph contains an explicit DOCX page break marker."""
    if para._p.xpath('.//w:br[@w:type="page"]'):
        return True
    return bool(para._p.xpath('.//w:lastRenderedPageBreak'))


def _is_table_figure_label_text(text: str) -> bool:
    return bool(_TABLE_FIGURE_LABEL_RE.match(text.strip()))


def _is_table_figure_title_after_label(text: str) -> bool:
    """Return True for a likely separate table/figure title following its label."""
    stripped = text.strip()
    if not stripped or len(stripped) > 200:
        return False
    if _HEADING_HEURISTIC_LIST_ITEM.match(stripped):
        return False
    if _HEADING_HEURISTIC_PAREN_YEAR.search(stripped):
        return False
    return not _TERMINAL_PUNCT_RE.search(stripped)


def extract_prose(doc: Document) -> list[ProseParagraph]:
    """
    Walk the document body and return only author-prose paragraphs.

    Excludes:
    - All table cells
    - Block-quote style paragraphs
    - Reference list entries (everything after a "References" heading)
    - Headings themselves (returned as ProseParagraph with heading_level set,
      so callers can check heading-level rules, but their text is not checked
      for word-level prose rules)
    """
    paragraphs: list[ProseParagraph] = []
    in_reference_section = False
    page_number = 1
    paragraph_number_on_page = 0
    previous_was_table_figure_label = False

    for idx, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        has_page_break = _contains_page_break(para)

        # Skip empty paragraphs
        if not text:
            if has_page_break:
                page_number += 1
                paragraph_number_on_page = 0
                previous_was_table_figure_label = False
            continue

        # Skip table cells entirely
        if _is_in_table(para):
            if has_page_break:
                page_number += 1
                paragraph_number_on_page = 0
                previous_was_table_figure_label = False
            continue

        level = _heading_level(para)
        if previous_was_table_figure_label and _is_table_figure_title_after_label(text):
            level = 0
        # Check if we've hit the reference list
        if level is not None and _REF_HEADING_KEYWORDS.match(text):
            in_reference_section = True

        if in_reference_section and level is None:
            paragraph_number_on_page += 1
            # Reference entry — skip prose rules but keep for citation matching
            paragraphs.append(ProseParagraph(
                index=idx,
                style_name=para.style.name if para.style else "",
                raw_text=text,
                masked_text=text,
                heading_level=None,
                is_reference_entry=True,
                page_number=page_number,
                paragraph_number_on_page=paragraph_number_on_page,
            ))
            previous_was_table_figure_label = False
            if has_page_break:
                page_number += 1
                paragraph_number_on_page = 0
            continue

        # Block quotes — exclude from prose rule scanning
        if _is_block_quote(para):
            previous_was_table_figure_label = False
            if has_page_break:
                page_number += 1
                paragraph_number_on_page = 0
            continue

        if level is None:
            paragraph_number_on_page += 1

        masked = _mask_inline_quotes(text)

        paragraphs.append(ProseParagraph(
            index=idx,
            style_name=para.style.name if para.style else "",
            raw_text=text,
            masked_text=masked,
            heading_level=level,
            is_reference_entry=False,
            page_number=page_number,
            paragraph_number_on_page=paragraph_number_on_page,
        ))
        previous_was_table_figure_label = _is_table_figure_label_text(text)
        if has_page_break:
            page_number += 1
            paragraph_number_on_page = 0
            previous_was_table_figure_label = False

    # Post-processing: reclassify heuristic headings in the title-page / preamble
    # zone as layout elements (level 0). Documents often place the title,
    # subtitle, author, and institution in Normal style with bold/centred
    # formatting; these look like headings to the heuristic but must not trigger
    # HED001/HED002 or PRF001.
    first_explicit_heading_pos = next(
        (j for j, p in enumerate(paragraphs)
         if _is_real_heading(p) and _is_explicit_word_heading(p)),
        None,
    )
    if first_explicit_heading_pos is not None:
        for j in range(first_explicit_heading_pos):
            p = paragraphs[j]
            if _is_real_heading(p) and not _is_explicit_word_heading(p):
                paragraphs[j].heading_level = 0
    else:
        # All-manual documents have no Word Heading styles. In that case, treat
        # earlier heuristic headings before the first body paragraph as preamble,
        # but preserve the final real heading immediately before that body text as
        # the likely first APA section heading.
        first_body_pos = next(
            (j for j, p in enumerate(paragraphs)
             if p.heading_level is None and not p.is_reference_entry),
            None,
        )
        if first_body_pos is not None:
            real_heading_positions = [
                j for j, p in enumerate(paragraphs[:first_body_pos])
                if _is_real_heading(p)
            ]
            for j in real_heading_positions[:-1]:
                paragraphs[j].heading_level = 0

    return paragraphs


def get_table_texts(doc: Document) -> set[str]:
    """Return all cell text from all tables — used to exclude from rule checks."""
    texts: set[str] = set()
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.add(cell.text.strip())
    return texts
