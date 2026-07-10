"""
APA 7 Reference List Rules — Chapter 9.
Text-pattern rules applied to reference list entries.

check_ref_entries(entries) returns a list of Finding-like dicts; the caller
converts them to Finding objects.  This avoids circular imports.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Shared reference patterns
# ---------------------------------------------------------------------------

# DOI in new format: https://doi.org/10.xxxx/...
_DOI_CORRECT = re.compile(r'https://doi\.org/10\.\d{4,}', re.IGNORECASE)

# Old DOI formats
_DOI_OLD_HTTP = re.compile(r'http://doi\.org/', re.IGNORECASE)
_DOI_OLD_DX = re.compile(r'http://dx\.doi\.org/', re.IGNORECASE)
_DOI_LABEL = re.compile(r'\bDOI:\s*10\.|\bdoi:\s*10\.', re.IGNORECASE)

# URL with "Retrieved from" or "Accessed from"
_RETRIEVED_FROM = re.compile(r'\bRetrieved\s+from\s+https?://', re.IGNORECASE)
_ACCESSED_FROM = re.compile(r'\bAccessed\s+from\s+https?://', re.IGNORECASE)

# Period after URL/DOI at end of reference (wrong: URLs/DOIs should have no trailing period)
_PERIOD_AFTER_URL = re.compile(r'https?://\S+\.\s*$')

# n.d. format errors
# NOTE: (N.D.) must be checked case-sensitively in a separate pattern.
# Adding re.IGNORECASE to \(N\.D\.\) would also match the CORRECT format (n.d.).
_ND_WRONG = re.compile(
    r'\(nd\)|\(n\.d\)|\(no\s+date\)|\(no-date\)',
    re.IGNORECASE,
)
_ND_WRONG_CAPS = re.compile(r'\(N\.D\.\)')  # case-sensitive: catches wrong-case (N.D.)

# "and" used between authors in reference (should be &)
_AND_BETWEEN_AUTHORS = re.compile(
    r'(?:[A-Z][a-z]+(?:[-\'][A-Z][a-z]+)?,\s+[A-Z]\.(?:\s+[A-Z]\.)?\s+)and\s+[A-Z]',
)

# Plural unit symbols in references (incorrect)
_PLURAL_UNITS = re.compile(r'\b\d+\s*(?:kgs|cms|mgs|mls|lbs|hrs|mins|secs)\b', re.IGNORECASE)

# "edition"/"editors" spelled out (should be abbrev)
_SPELLED_EDITION = re.compile(r'\((?:\d+(?:st|nd|rd|th)\s+)?edition\)', re.IGNORECASE)
_SPELLED_EDITORS = re.compile(r'\bEditors\b(?!\s+\()', re.IGNORECASE)

# Business structure designations (should be omitted from publisher names)
_BUSINESS_SUFFIX = re.compile(r'\b(Inc\.|Ltd\.|LLC|L\.L\.C\.|Co\.)\s', re.IGNORECASE)

# "Bibliography" header (should be "References")
_BIBLIOGRAPHY = re.compile(r'^\s*Bibliography\s*$', re.IGNORECASE)

# Wrong n.d. forms in author+date position
_IN_PRESS_FORMAT = re.compile(r'\(in-press\)|\(In Press\)|\(In press\)')

# Date missing period: (2020) without trailing period
_DATE_NO_PERIOD = re.compile(r'\(\d{4}(?:[a-z])?\)\s+[A-Z]')

# Same author — year without disambiguation letter detection
# (handled in check_ref_order, not here)

# "Reference" (singular) as section header
_REF_SINGULAR = re.compile(r'^\s*Reference\s*$')

# "et al." in reference list (should not appear — list all authors up to 20)
_ETAL_IN_REF = re.compile(r'\bet\s+al\.?\b', re.IGNORECASE)

# Original work published phrase format
_ORIG_WORK = re.compile(r'\boriginally\s+published\b|\bfirst\s+published\b', re.IGNORECASE)

# Trans. without (Original work published YYYY)
_TRANS_WITHOUT_ORIG = re.compile(r'\bTrans\.\)', re.IGNORECASE)
_ORIG_WORK_PHRASE = re.compile(r'\(Original\s+work\s+published\s+\d{4}\)', re.IGNORECASE)

# Author name "and" between names
_AUTHOR_AND = re.compile(
    r'\b[A-Z][a-z]+,\s+[A-Z]\.\s+(?:[A-Z]\.\s+)?and\s+[A-Z][a-z]+,',
)

# Three+ author ref with et al. (wrong — should list up to 20)
# We check: if & appears, that's correct. If "et al." appears in a REF entry, flag it.

# Issue number with space before: "30 (5)" should be "30(5)"
_ISSUE_SPACE = re.compile(r'(\d+)\s+\((\d+)\)')

# Article number not capitalized: "article e0158474" → "Article e0158474"
_ARTICLE_LOWER = re.compile(r'\barticle\s+[a-zA-Z0-9]+', re.IGNORECASE)
_ARTICLE_CORRECT = re.compile(r'\bArticle\s+[a-zA-Z0-9]+')

# ISBN/ISSN in reference entries (§9.34 — should not appear)
_ISBN_ISSN_RE = re.compile(r'\bISBN[:\s]|\bISSN[:\s]', re.IGNORECASE)

# Reference article/chapter title segment after the date.
_REF_TITLE_SEGMENT_RE = re.compile(r'\(\d{4}[^)]*\)\.\s+(?P<title>.+?)\.\s+')
_PERSONAL_COMMUNICATION_RE = re.compile(r'\bpersonal\s+communication\b', re.IGNORECASE)
_TITLE_CASE_EXEMPT_WORDS = {
    "I", "AI", "APA", "COVID", "USA", "US", "UK",
}
_LOWERCASE_TITLE_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into",
    "nor", "of", "on", "or", "the", "to", "with", "without",
}


def _looks_like_reference_title_case_error(text: str) -> tuple[bool, str]:
    match = _REF_TITLE_SEGMENT_RE.search(text)
    if not match:
        return False, ""
    title = match.group("title").strip()
    # Ignore the first word and the first word after a colon; both may be capitalized.
    exempt_positions = {0}
    words = list(re.finditer(r'\b[A-Za-z][A-Za-z-]*\b', title))
    for idx, word in enumerate(words):
        if title[:word.start()].rstrip().endswith(":"):
            exempt_positions.add(idx)

    unexpected_caps = []
    for idx, word in enumerate(words):
        raw = word.group(0)
        if idx in exempt_positions:
            continue
        if raw in _TITLE_CASE_EXEMPT_WORDS:
            continue
        if raw.lower() in _LOWERCASE_TITLE_WORDS and raw != raw.lower():
            unexpected_caps.append(raw)
            continue
        if raw[:1].isupper() and raw[1:] != raw[1:].upper():
            unexpected_caps.append(raw)
    return len(unexpected_caps) >= 2, title


# ---------------------------------------------------------------------------
# Alphabetical order check helper
# ---------------------------------------------------------------------------

def _extract_sort_key(entry: str) -> str:
    """Extract the first author surname for alphabetization comparison."""
    # Most references start with "Surname, I." or "Group Name"
    # Take text up to first comma or parenthesis
    entry = entry.strip()
    # Strip leading "The ", "A ", "An " for no-author entries
    entry_clean = re.sub(r'^(?:The|A|An)\s+', '', entry, flags=re.IGNORECASE)
    # Get first author surname: text before first comma
    m = re.match(r'^([A-Za-z\-\' ]+?)(?:,|\()', entry_clean)
    if m:
        return m.group(1).strip().lower().replace(' ', '').replace('-', '').replace("'", '')
    return entry_clean[:20].lower()


# ---------------------------------------------------------------------------
# Main reference checker
# ---------------------------------------------------------------------------

def check_ref_entries(
    entries: list[dict],   # list of {"index": int, "text": str, "raw_text": str}
    cfg: dict = None,
) -> list[dict]:
    """
    Check reference list entries for APA 7 formatting violations.

    Returns a list of finding-dicts with keys:
    rule_id, severity, paragraph_index, message, suggested_fix, excerpt, chapter
    """
    cfg = cfg or {}
    findings: list[dict] = []

    texts = [e["text"] for e in entries]
    prev_key: Optional[str] = None

    for entry in entries:
        idx = entry["index"]
        text = entry["text"]
        loc = f'Reference entry — "{text[:60].rstrip()}{"…" if len(text) > 60 else ""}"'

        def _add(rule_id, severity, message, suggested_fix="", chapter="§9"):
            findings.append({
                "rule_id": rule_id,
                "severity": severity,
                "paragraph_index": idx,
                "message": message,
                "suggested_fix": suggested_fix,
                "excerpt": text[:80],
                "location_hint": loc,
                "chapter": chapter,
            })

        # REF001 — Old DOI format (§9.34)
        if _DOI_OLD_HTTP.search(text) or _DOI_OLD_DX.search(text):
            _add(
                "REF001", "warning",
                "APA §9.34: Old DOI format detected. Replace 'http://doi.org/' or "
                "'http://dx.doi.org/' with 'https://doi.org/'.",
                "Change to: https://doi.org/...",
                "§9.34",
            )

        # REF002 — DOI label format (§9.34)
        if _DOI_LABEL.search(text):
            _add(
                "REF002", "warning",
                "APA §9.34: Do not prefix DOIs with 'DOI:' or 'doi:'. "
                "Format as a hyperlink: https://doi.org/10.XXXX/XXXX",
                "Remove 'DOI:' label and use full URL format",
                "§9.34",
            )

        # REF003 — "Retrieved from" before URL (§9.35)
        if _RETRIEVED_FROM.search(text):
            _add(
                "REF003", "warning",
                "APA §9.35: Do not use 'Retrieved from' before a URL. Remove that phrase.",
                "Delete 'Retrieved from'",
                "§9.35",
            )

        # REF004 — "Accessed from" (§9.35)
        if _ACCESSED_FROM.search(text):
            _add(
                "REF004", "warning",
                "APA §9.35: Do not use 'Accessed from' before a URL. Remove that phrase.",
                "Delete 'Accessed from'",
                "§9.35",
            )

        # REF005 — Period after URL/DOI (§9.35)
        if _PERIOD_AFTER_URL.search(text):
            _add(
                "REF005", "warning",
                "APA §9.35: Do not add a period after a DOI or URL at the end of a reference.",
                "Remove the trailing period after the URL/DOI",
                "§9.35",
            )

        # REF006 — Wrong n.d. format (§9.17)
        # Check case-insensitive wrong forms first, then uppercase-specific (N.D.) separately.
        m = _ND_WRONG.search(text) or _ND_WRONG_CAPS.search(text)
        if m:
            _add(
                "REF006", "error",
                f"APA §9.17: '{m.group()}' is not the correct format. Use '(n.d.)' — "
                "two periods, no spaces.",
                "Replace with (n.d.)",
                "§9.17",
            )

        # REF007 — "and" between authors (should be &) (§9.8)
        if _AND_BETWEEN_AUTHORS.search(text) or _AUTHOR_AND.search(text):
            _add(
                "REF007", "warning",
                "APA §9.8: Use '&' (ampersand) — not 'and' — between author names in the reference list.",
                "Replace 'and' with '&' between author names",
                "§9.8",
            )

        # REF008 — "et al." in reference entry (§9.8)
        # et al. is for in-text only; reference lists must list up to 20 authors.
        if _ETAL_IN_REF.search(text):
            _add(
                "REF008", "error",
                "APA §9.8: Do not use 'et al.' in the reference list. "
                "List all authors up to 20; for 21 or more, list the first 19, "
                "add an ellipsis (…), then the final author's name.",
                "List all authors (up to 20) or use the 21+ format",
                "§9.8",
            )

        # REF009 — Spelled-out edition (§9.22 / §9.50)
        m = _SPELLED_EDITION.search(text)
        if m:
            _add(
                "REF009", "warning",
                f"APA §9.50: Spell out of 'edition' detected: '{m.group()}'. "
                "Use standard abbreviation: '2nd ed.' or 'Rev. ed.'",
                "Use 'ed.' abbreviation",
                "§9.50",
            )

        # REF022 — "Editors" spelled out in reference (§9.50)
        m = _SPELLED_EDITORS.search(text)
        if m:
            _add(
                "REF022", "warning",
                f"APA §9.50: 'Editors' should be abbreviated in reference list entries. "
                "Use 'Ed.' for one editor or 'Eds.' for multiple editors.",
                "Replace 'Editors' with 'Eds.'",
                "§9.50",
            )

        # REF010 — Business structure designations (§9.29)
        m = _BUSINESS_SUFFIX.search(text)
        if m:
            _add(
                "REF010", "warning",
                f"APA §9.29: Omit publisher business designations ('{m.group().strip()}') "
                "from reference list entries.",
                f"Remove '{m.group().strip()}' from publisher name",
                "§9.29",
            )

        # REF011 — Date missing period (§9.14)
        if _DATE_NO_PERIOD.search(text):
            _add(
                "REF011", "warning",
                "APA §9.14: A period is required after the date parenthetical: (2020). "
                "The title element must begin after the date period.",
                "Add a period after the closing parenthesis of the date",
                "§9.14",
            )

        # REF012 — in-press format (§9.14)
        m = _IN_PRESS_FORMAT.search(text)
        if m:
            _add(
                "REF012", "warning",
                f"APA §9.14: '{m.group()}' is incorrectly formatted. "
                "Use '(in press)' — lowercase, no hyphens.",
                "Replace with (in press)",
                "§9.14",
            )

        # REF013 — Journal issue with space before parenthesis (§9.25)
        m = _ISSUE_SPACE.search(text)
        if m:
            _add(
                "REF013", "warning",
                f"APA §9.25: Space before issue number parenthesis: '{m.group()}'. "
                "Issue number must immediately follow volume with no space: e.g., 30(5).",
                f"Change '{m.group()}' to '{m.group(1)}({m.group(2)})'",
                "§9.25",
            )

        # REF014 — "article" not capitalized (§9.27)
        if _ARTICLE_LOWER.search(text) and not _ARTICLE_CORRECT.search(text):
            _add(
                "REF014", "warning",
                "APA §9.27: Article number descriptors must be capitalized: 'Article e0158474', not 'article e0158474'.",
                "Capitalize 'Article'",
                "§9.27",
            )

        # REF015 — Translated work missing original year (§9.39)
        if _TRANS_WITHOUT_ORIG.search(text) and not _ORIG_WORK_PHRASE.search(text):
            _add(
                "REF015", "warning",
                "APA §9.39: References to translated works must include '(Original work published YYYY)' "
                "at the end of the entry.",
                "Add '(Original work published YYYY)' at the end",
                "§9.39",
            )

        # REF016 — Wrong 'original work published' phrasing (§9.41)
        m = _ORIG_WORK.search(text)
        if m:
            _add(
                "REF016", "warning",
                f"APA §9.41: '{m.group()}' is incorrect phrasing. "
                "Use the exact phrase: '(Original work published YYYY)'.",
                "Use '(Original work published YYYY)'",
                "§9.41",
            )

        # REF017 — Plural unit symbols (§6.27)
        m = _PLURAL_UNITS.search(text)
        if m:
            _add(
                "REF017", "warning",
                f"APA §6.27: Unit symbols are not pluralized: '{m.group()}'. "
                "Use 'kg', 'cm', 'mg', etc. without trailing 's'.",
                f"Remove the 's' from '{m.group()}'",
                "§6.27",
            )

        # REF023 — ISBN or ISSN in reference entry (§9.34)
        m = _ISBN_ISSN_RE.search(text)
        if m:
            _add(
                "REF023", "warning",
                "APA §9.34: Do not include ISBN or ISSN numbers in reference list entries. "
                "These identifiers are not part of APA Style references.",
                f"Remove '{m.group().strip()}' from the reference entry",
                "§9.34",
            )

        # REF024 — Article/chapter title should use sentence case (§9.19)
        title_case_error, title = _looks_like_reference_title_case_error(text)
        if title_case_error:
            _add(
                "REF024", "warning",
                "APA §9.19: Titles of articles and chapters in the reference list use sentence case, "
                "not title case. Capitalize only the first word of the title/subtitle and proper nouns.",
                "Convert the reference title to sentence case.",
                "§9.19",
            )

        # REF025 — Personal communications do not appear in References (§8.9)
        if _PERSONAL_COMMUNICATION_RE.search(text):
            _add(
                "REF025", "error",
                "APA §8.9: Personal communications are cited only in text and should not appear "
                "in the reference list because readers cannot retrieve them.",
                "Remove this personal communication from the reference list.",
                "§8.9",
            )

        # REF018 — Alphabetical order (§9.44)
        current_key = _extract_sort_key(text)
        if prev_key is not None and current_key < prev_key:
            _add(
                "REF018", "warning",
                "APA §9.44: Reference list must be in alphabetical order by first author surname. "
                f"This entry ('{current_key[:20]}') appears to be out of order "
                f"after an entry beginning with '{prev_key[:20]}'.",
                "Reorder reference list entries alphabetically by first author surname",
                "§9.44",
            )
        prev_key = current_key

    # REF019 — "Bibliography" as header (§9.43)
    for entry in entries:
        if _BIBLIOGRAPHY.match(entry["text"]):
            findings.append({
                "rule_id": "REF019",
                "severity": "error",
                "paragraph_index": entry["index"],
                "message": "APA §9.43: The section header should be 'References', not 'Bibliography'. "
                           "APA Style uses 'References' for the list of cited works.",
                "suggested_fix": "Change 'Bibliography' to 'References'",
                "excerpt": entry["text"][:80],
                "location_hint": f'Heading — "{entry["text"][:60]}"',
                "chapter": "§9.43",
            })

    # REF020 — "Reference" singular header (§9.43)
    for entry in entries:
        if _REF_SINGULAR.match(entry["text"]):
            findings.append({
                "rule_id": "REF020",
                "severity": "warning",
                "paragraph_index": entry["index"],
                "message": "APA §9.43: The section header 'Reference' (singular) is incorrect. "
                           "Use 'References' (plural).",
                "suggested_fix": "Change 'Reference' to 'References'",
                "excerpt": entry["text"][:80],
                "location_hint": f'Heading — "{entry["text"][:60]}"',
                "chapter": "§9.43",
            })

    # REF021 — Check for same author + same year without disambiguation (§9.47)
    _check_same_author_year(entries, findings)

    return findings


def _check_same_author_year(entries: list[dict], findings: list[dict]) -> None:
    """Flag same author + same year entries that lack a/b/c disambiguation."""
    seen: dict[str, list[int]] = {}
    _AUTHOR_YEAR_RE = re.compile(
        r'^(.+?)\.\s*\((\d{4})([a-z]?)(?:,\s+[A-Za-z]+\s+\d+)?\)\.',
    )
    for entry in entries:
        text = entry["text"].strip()
        m = _AUTHOR_YEAR_RE.match(text)
        if not m:
            continue
        author_part = m.group(1).strip()
        year = m.group(2)
        suffix = m.group(3)  # 'a', 'b', '', etc.
        key = f"{_extract_sort_key(author_part)}_{year}"
        seen.setdefault(key, []).append(entry["index"])

    for key, indices in seen.items():
        if len(indices) > 1:
            for idx in indices:
                findings.append({
                    "rule_id": "REF021",
                    "severity": "warning",
                    "paragraph_index": idx,
                    "message": "APA §9.47: Multiple works by the same author(s) in the same year "
                               "must be distinguished with lowercase letters after the year: 2020a, 2020b, etc. "
                               "The same letters must appear in the corresponding in-text citations.",
                    "suggested_fix": "Add 'a', 'b', 'c' after the year in both the reference list and in-text citations",
                    "excerpt": "",
                    "location_hint": f"Reference index {idx + 1}",
                    "chapter": "§9.47",
                })
