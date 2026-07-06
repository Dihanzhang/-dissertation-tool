"""
Module 2 — APA 7 Rule Checker (deterministic, no LLM).

168 rules across 8 categories:
  MEC (22)  — Mechanics & Formatting       §2, §6, §8.25/8.30
  BFL (34)  — Bias-Free Language           §5
  STY (16)  — Style & Grammar              §4
  HED (2)   — Heading Structure            §2.27
  CIT (15)  — In-Text Citations            §8
  REF (21)  — Reference List               §9
  TBL (6)   — Tables & Figures             §7
  PRF (3)   — Program Requirements         configurable

Input : list[ProseParagraph]  (from prose_extractor)
Output: list[Finding]

BFL rules → always Severity.SUGGESTION with explicit replacement.
STY001 (passive voice) → Severity.SUGGESTION.
All other rules → Severity.WARNING or Severity.ERROR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from docx import Document

from .prose_extractor import ProseParagraph, extract_prose, QUOTE_MASK
from .apa_bfl_rules import BFL_RULES
from .apa_ref_rules import check_ref_entries


# ===========================================================================
# Data Model
# ===========================================================================

class Severity(str, Enum):
    ERROR      = "error"
    WARNING    = "warning"
    SUGGESTION = "suggestion"
    INFO       = "info"          # kept for backward compatibility


class Category(str, Enum):
    MECHANICS  = "mechanics"
    BIAS_FREE  = "bias_free"
    STYLE      = "style"
    HEADING    = "heading"
    CITATION   = "citation"
    REFERENCE  = "reference"
    TABLE      = "table"
    PROFESSOR  = "professor"


@dataclass
class Finding:
    rule_id:       str
    severity:      Severity
    paragraph_index: int
    message:       str
    suggested_fix: str     = ""
    autofixable:   bool    = False
    excerpt:       str     = ""
    location_hint: str     = ""
    category:      str     = ""    # Category enum value string
    chapter:       str     = ""    # APA section reference, e.g. "§6.33"


# ===========================================================================
# Config
# ===========================================================================

def _load_config(path: Optional[str] = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent / "config" / "prof_checklist.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===========================================================================
# Shared utilities
# ===========================================================================

def _sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p for p in parts if p]


def _is_in_parentheses(text: str, pos: int) -> bool:
    depth = 0
    for c in text[:pos]:
        if c == '(':
            depth += 1
        elif c == ')':
            depth = max(0, depth - 1)
    return depth > 0


def _is_in_quotes(text: str, pos: int) -> bool:
    """Return True if position pos is inside double-quote marks."""
    count = text[:pos].count('"') + text[:pos].count('“') + text[:pos].count('”')
    return count % 2 == 1


def _near_quote_mask(masked: str, start: int, end: int, window: int = 10) -> bool:
    return QUOTE_MASK in masked[max(0, start - window):end + window]


def _loc(para: ProseParagraph) -> str:
    anchor = para.raw_text[:60].strip()
    if len(para.raw_text) > 60:
        anchor += "..."
    page = getattr(para, "page_number", 1)
    para_on_page = getattr(para, "paragraph_number_on_page", para.index + 1)
    return f'Page {page}, Para {para_on_page} - "{anchor}"'


def _excerpt(text: str, start: int, end: int, window: int = 20) -> str:
    return text[max(0, start - window):min(len(text), end + window)].strip()[:80]


def _is_indent_check_candidate(para: ProseParagraph) -> bool:
    """Only check first-line indent on substantial body paragraphs from DOCX."""
    if not getattr(para, "has_format_metadata", False):
        return False
    if para.heading_level is not None or para.is_reference_entry or getattr(para, "is_list_item", False):
        return False
    text = para.raw_text.strip()
    if not text:
        return False
    if not re.search(r'[.!?]\s*$', text):
        return False
    word_count = len(re.findall(r'\b\w+\b', text))
    sentence_count = len(_sentences(text))
    return word_count >= _INDENT_MIN_WORDS or sentence_count >= _INDENT_MIN_SENTENCES


# ===========================================================================
# MEC — Number exemption helpers (§6.32–6.33)
# ===========================================================================

_UNITS_RE = re.compile(
    r'\b\d+\s*(?:'
    r'months?|years?|weeks?|days?|hours?|minutes?|seconds?|'
    r'km|m\b|cm|mm|kg|g\b|mg|lb|oz|ft|in\.|'
    r'%|percent|participants?|items?|pages?|chapters?|sections?|trials?|'
    r'hr|min\b|ms\b|ns\b|s\b'
    r')\b',
    re.IGNORECASE,
)

_SERIES_NOUN_RE = re.compile(
    r'\b(?:'
    r'Table|Figure|Chart|Graph|Map|Chapter|Section|Part|Appendix|'
    r'Step|Phase|Stage|Level|Round|Wave|Grade|Class|Module|Unit|Lesson|'
    r'Condition|Trial|Session|Run|Block|Question|Item|Task|Criterion|'
    r'Group|Arm|Sample|Cohort|Row|Column|Line|Note|Footnote|'
    r'Equation|Formula|Example|Box|Day|Week|Month|Year|Version|Study|'
    r'Exhibit|Supplement|Cluster|Factor|Theme|Category'
    r')\s+\d+\b',
    re.IGNORECASE,
)

_VERSION_STR_RE  = re.compile(r'\b\w[\w.]*\s+\d+(?:\.\d+)+\b')
_ABBREV_NUM_RE   = re.compile(r'\b[A-Z]{2,}(?:\s*[-–]\s*|\s+)\d+\b')
_PERCENTAGE_RE   = re.compile(r'\b\d+(?:\.\d+)?\s*%')
_AGE_RE          = re.compile(r'\bage[ds]?\s+\d+\b', re.IGNORECASE)
_STAT_RE         = re.compile(
    r'[Nn]\s*=\s*\d+|[pr]\s*[<>=]\s*[\d.]+|[Mm][Ss]?\s*=\s*[\d.]+|'
    r'[Ff]\s*\(\d+,\s*\d+\)|\d+\s+out\s+of\s+\d+|\d+/\d+'
)
_ORDINAL_RE      = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.IGNORECASE)
_SCALE_SCORE_RE  = re.compile(
    r'(?:rated?|scored?|ranked?)\s+\d+\b|\d+\s*[-–]\s*point\s+scale|'
    r'\b\d+\s*to\s*\d+\s+scale',
    re.IGNORECASE,
)
_MONEY_RE        = re.compile(r'[$£€¥]\s*\d+')
_RANGE_CONTEXT_RE = re.compile(r'\d+\s*(?:-|–|—|to|through|and)\s*\d+', re.IGNORECASE)


def _exempt_numeral(text: str, m: re.Match) -> bool:
    """Return True if this numeral is exempt from the spell-out rule."""
    start, end = m.span()
    # Decimal fraction: the "5" in "361.5" — digit follows "." or another digit
    if start > 0 and text[start - 1] in '.0123456789':
        return True
    fwd  = text[start:min(len(text), end + 30)]
    bk20 = text[max(0, start - 20):end + 5]
    near = text[max(0, start - 15):min(len(text), end + 25)]
    if _SERIES_NOUN_RE.search(bk20):       return True
    if _UNITS_RE.match(fwd):               return True
    if _VERSION_STR_RE.search(near):       return True
    if _ABBREV_NUM_RE.search(bk20):        return True
    if _PERCENTAGE_RE.search(fwd):         return True
    if _AGE_RE.search(near):               return True
    if _STAT_RE.search(near):              return True
    if _ORDINAL_RE.match(text[start:end + 4]): return True
    if _SCALE_SCORE_RE.search(near):       return True
    if _MONEY_RE.search(text[max(0, start - 2):end + 1]): return True
    if _RANGE_CONTEXT_RE.search(near):      return True
    return False


_NUM_WORDS = {
    0: "zero",
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine",
}

_WORD_NUMS_HIGH = re.compile(
    r'\b(ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|'
    r'eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|'
    r'ninety|hundred|thousand|million)\b',
    re.IGNORECASE,
)

# High-number words that are part of proper names / APA-endorsed expressions
_WORD_NUM_EXEMPT_RE = re.compile(
    r'(?:'
    r'Twelve\s+Apostles|Five\s+Pillars|Ten\s+Commandments|'
    r'[Ss]even\s+Deadly|[Tt]hree\s+Wise|[Ee]ight\s+Beatitudes|'
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|'
    r'March|April|May|June|July|August|September|October|November|December)'
    r')',
    re.IGNORECASE,
)


# ===========================================================================
# MEC — Pattern constants
# ===========================================================================

# MEC001: Double space after period
_DOUBLE_SPACE_RE = re.compile(r'\.\s{2,}')

# MEC002: Sentence-starting numeral
_SENTENCE_START_NUM_RE = re.compile(
    r'(?:(?:^)|(?<=[.!?])\s+)(\d{1,3}(?:,\d{3})+|\d+)',
    re.MULTILINE,
)

# MEC003: Small numeral 1–9
_NUMERIC_TOKEN_RE = re.compile(r'(?<![\w.-])(\d[\d,]*(?:\.\d+)?)(?![\w.-])')

# MEC006: "N percent" → "N%"
_N_PERCENT_RE = re.compile(r'\b(\d+(?:\.\d+)?)\s+percent\b', re.IGNORECASE)

# MEC007: p value with leading zero
_P_ZERO_RE = re.compile(r'\bp\s*[=<>]\s*0\.(\d+)\b')

# MEC008: r / correlation with leading zero
_R_ZERO_RE = re.compile(r'\b(?:r|rho|tau)\s*=\s*0\.(\d+)\b', re.IGNORECASE)

# MEC009: p value threshold-only (p < .05 / p < .01)
_P_THRESHOLD_RE = re.compile(r'\bp\s*<\s*\.(0?[15]|10)\b')

# MEC010: 4+ digit number without comma
_BIG_NUM_RE = re.compile(r'\b(\d{4,})\b')
# Exceptions: years, DOI fragments, version strings, page refs
_BIG_NUM_YEAR_RE = re.compile(r'\b(1[89]\d{2}|20[0-3]\d)\b')
_BIG_NUM_CONTEXT_EXEMPT = re.compile(
    r'(?:doi\.org|ISBN|ISSN|SN|Serial|Model|ID|code|equation|df\s*=|'
    r'pp?\.\s*\d|p\.\s*\d|Figure\s+\d|Table\s+\d|'
    r'\b(?:k?MHz?|GHz)\b|°[CF]|degrees?\s*[CF]\b)',
    re.IGNORECASE,
)

_APA_FIRST_LINE_INDENT_TWIPS = 720  # 0.5 in. = 1.27 cm
_APA_FIRST_LINE_INDENT_TOLERANCE = 80
_INDENT_MIN_WORDS = 25
_INDENT_MIN_SENTENCES = 2

# MEC011: Apostrophe in number plural
_NUM_APOSTROPHE_RE = re.compile(r"\b(\d+)'s\b")

# MEC012: Spaced em dash
_SPACED_EMDASH_RE = re.compile(r' — ')

# MEC013: -ly adverb hyphenation
_LY_HYPHEN_RE = re.compile(r'\b([a-z]+ly)-([a-z]+)\b', re.IGNORECASE)
_LY_ADJECTIVE_EXEMPT_FIRST_WORDS = {
    "brotherly", "burly", "chilly", "comely", "costly", "cowardly",
    "curly", "daily", "deadly", "early", "elderly", "family",
    "fatherly", "friendly", "ghastly", "goodly", "hilly", "holy",
    "homely", "hourly", "jolly", "leisurely", "likely", "lively",
    "lonely", "lovely", "manly", "measly", "monthly", "motherly",
    "nightly", "oily", "orderly", "scholarly", "shapely", "sickly",
    "silly", "sisterly", "sly", "stately", "surly", "timely",
    "ugly", "unlikely", "weekly", "wily", "womanly", "woolly",
    "yearly",
}
_LY_ADVERB_FIRST_WORDS = {
    "accurately", "actively", "adequately", "approximately", "broadly",
    "carefully", "clearly", "closely", "commonly", "completely",
    "consistently", "directly", "effectively", "especially", "fully",
    "generally", "globally", "highly", "indirectly", "jointly",
    "largely", "locally", "merely", "mutually", "narrowly", "newly",
    "partially", "particularly", "poorly", "previously", "primarily",
    "quickly", "randomly", "rapidly", "recently", "relatively",
    "significantly", "slowly", "statistically", "strongly",
    "typically", "widely",
}
_LY_ADVERB_SUFFIXES = (
    "ably", "ally", "edly", "ently", "fully", "ibly", "ically",
    "ingly", "ively", "lessly", "ously",
)


def _looks_like_ly_adverb(word: str) -> bool:
    lower = word.lower()
    if lower in _LY_ADJECTIVE_EXEMPT_FIRST_WORDS:
        return False
    if lower in _LY_ADVERB_FIRST_WORDS:
        return True
    return lower.endswith(_LY_ADVERB_SUFFIXES)

# MEC014: Time unit spelled out with numeral (should use abbreviation)
_TIME_UNIT_SPELLED_RE = re.compile(
    r'\b(\d+)\s+(hours?|minutes?|seconds?|milliseconds?|microseconds?)\b',
    re.IGNORECASE,
)
_TIME_ABBREV_MAP = {
    'hour': 'hr', 'hours': 'hr',
    'minute': 'min', 'minutes': 'min',
    'second': 's', 'seconds': 's',
    'millisecond': 'ms', 'milliseconds': 'ms',
    'microsecond': 'μs', 'microseconds': 'μs',
}
# But day/week/month/year are NOT abbreviated — flag wrong abbrevs
_TIME_WRONG_ABBREV_RE = re.compile(r'\b(\d+)\s*(d\.|wk\.|mo\.)\b')

# MEC015: Plural unit symbols
_PLURAL_UNIT_RE = re.compile(
    r'\b\d+\s*(?:kgs|cms|mgs|mls|lbs|ozs|hrs|mins|secs|mss)\b',
    re.IGNORECASE,
)

# MEC018: Series nouns uncapitalized
_SERIES_NOUN_LC_RE = re.compile(
    r'\b(chapter|figure|table|row|column|trial|item|grade|step|section|'
    r'appendix|exhibit|condition|phase|stage|module|unit|version)\s+(\d+)\b',
)

# MEC019: "Page" / "Paragraph" capitalized before numeral
_PAGE_PARA_CAP_RE = re.compile(r'\b(Page|Paragraph)\s+\d+\b')

# MEC020: Inline quoted text ≥ 40 words
_INLINE_QUOTE_CONTENT_RE = re.compile(r'"([^"]{150,})"|“([^”]{150,})”')

# MEC021: Wrong ellipsis inside quoted material
_WRONG_ELLIPSIS_RE = re.compile(r'\.{3}|…')   # three dots or unicode ellipsis

# MEC022: Adjacent numerals ("2 5-point scales" → "two 5-point scales")
_ADJACENT_NUM_RE = re.compile(r'\b(\d+)\s+(\d+)[-–]')

# MEC017: Wordy title phrases
_WORDY_TITLE_RE = re.compile(
    r'\b(a\s+study\s+of|an?\s+investigation\s+of|an?\s+examination\s+of|'
    r'a\s+review\s+of|an?\s+analysis\s+of|an?\s+exploration\s+of|'
    r'a\s+discussion\s+of)\b',
    re.IGNORECASE,
)


# ===========================================================================
# STY — Pattern constants
# ===========================================================================

# STY001: Passive voice — be + past participle
_PASSIVE_RE = re.compile(
    r'\b(was|were|is|are|been|be|being)\s+(\w+ed|'
    r'known|shown|found|seen|given|written|done|made|taken|'
    r'chosen|broken|driven|grown|spoken|worn|drawn|begun|rung|'
    r'sung|swum|flown|thrown|blown|grown|spoken|hidden|bitten|frozen|'
    r'stolen|torn|worn|woven|shaken|sworn|taken|written|eaten|fallen|'
    r'risen|driven|given|forgiven|forgotten|gotten|ridden|stricken|'
    r'striven|striven|thriven|woken|woven)\b',
    re.IGNORECASE,
)
# Statistical passives exempt from STY001
_STAT_PASSIVE_EXEMPT_RE = re.compile(
    r'\b(?:was|were)\s+(?:correlated|regressed|administered|analyzed|'
    r'assigned|randomized|counterbalanced|stratified|matched|coded|'
    r'scored|rated|assessed|measured|calculated|computed|estimated|'
    r'controlled|adjusted|standardized|normalized|transformed|excluded|'
    r'included|recruited|enrolled|selected|screened|tested|interviewed|'
    r'observed)\b',
    re.IGNORECASE,
)

# STY002: Redundant phrases (§4.5)
_REDUNDANT_PAIRS: list[tuple[str, str]] = [
    (r'\bthey were both alike\b',       "they were alike"),
    (r'\ba sum total\b',                "a total"),
    (r'\babsolutely essential\b',       "essential"),
    (r'\bhas been previously found\b',  "was found"),
    (r'\bsmall in size\b',              "small"),
    (r'\bcompletely unanimous\b',       "unanimous"),
    (r'\bperiod of time\b',             "period"),
    (r'\bbriefly summarize\b|\bsummarize briefly\b', "summarize"),
    (r'\bthe reason is because\b',      "the reason is that"),
    (r'\bfour different groups\b',      "four groups"),
    (r'\bone and the same\b',           "the same"),
    (r'\bin close proximity\b',         "close"),
    (r'\bcompletely finished\b',        "finished"),
    (r'\bend result\b',                 "result"),
    (r'\bfuture plans\b',               "plans"),
    (r'\bpast history\b',               "history"),
    (r'\bactual experience\b',          "experience"),
    (r'\badvance planning\b',           "planning"),
    (r'\bbasic fundamentals\b',         "fundamentals"),
    (r'\bclose proximity\b',            "proximity"),
    (r'\bcollaborate together\b',       "collaborate"),
    (r'\bconsensus of opinion\b',       "consensus"),
    (r'\bdefinitely proved\b',          "proved"),
    (r'\beach individual\b',            "each"),
    (r'\bexact same\b',                 "same"),
    (r'\bfree gift\b',                  "gift"),
    (r'\bgeneral public\b',             "public (if no specific contrast)"),
    (r'\bhuman volunteers\b',           "volunteers"),
    (r'\bjoint collaboration\b',        "collaboration"),
    (r'\bnew innovation\b',             "innovation"),
    (r'\bplanned in advance\b',         "planned"),
    (r'\bunexpected surprise\b',        "surprise"),
    (r'\bvisual appearance\b',          "appearance"),
]
_REDUNDANT_RES = [
    (re.compile(pat, re.IGNORECASE), fix) for pat, fix in _REDUNDANT_PAIRS
]

# STY003: Wordy expressions (§4.4)
_WORDY_PAIRS: list[tuple[str, str]] = [
    (r'\bin\s+order\s+to\b',              "to"),
    (r'\bfor\s+the\s+purpose\s+of\b',     "to"),
    (r'\bdue\s+to\s+the\s+fact\s+that\b', "because"),
    (r'\bin\s+the\s+event\s+that\b',      "if"),
    (r'\bat\s+the\s+present\s+time\b',    "now"),
    (r'\bin\s+spite\s+of\s+the\s+fact\s+that\b', "although"),
    (r'\bwith\s+the\s+exception\s+of\b',  "except"),
    (r'\bthe\s+fact\s+that\b',            "(omit or recast the sentence)"),
    (r'\bwith\s+regard\s+to\b',           "regarding"),
    (r'\bin\s+terms\s+of\b',              "for / with / in (be specific)"),
    (r'\bon\s+the\s+basis\s+of\b',        "based on"),
    (r'\bhas\s+the\s+ability\s+to\b',     "can"),
    (r'\bis\s+able\s+to\b',               "can"),
    (r'\bmake\s+a\s+decision\b',          "decide"),
    (r'\bprovide\s+assistance\s+to\b',    "assist" ),
    (r'\bcome\s+to\s+a\s+conclusion\b',   "conclude"),
    (r'\bconduct\s+a\s+study\b',          "study"),
    (r'\bperform\s+an\s+analysis\b',      "analyze"),
    (r'\bit\s+is\s+important\s+to\s+note\s+that\b', "(omit)"),
    (r'\bit\s+should\s+be\s+noted\s+that\b', "(omit)"),
    (r'\bit\s+is\s+worth\s+noting\s+that\b', "(omit)"),
]
_WORDY_RES = [
    (re.compile(pat, re.IGNORECASE), fix) for pat, fix in _WORDY_PAIRS
]

# STY004: "that" to refer to people
_THAT_PEOPLE_RE = re.compile(
    r'\b(participants?|students?|children|adults?|patients?|'
    r'therapists?|researchers?|women|men|individuals?|people|'
    r'mothers?|fathers?|teachers?|clinicians?|practitioners?|respondents?)\s+'
    r'that\s+(were|was|had|did|said|reported|completed|scored|'
    r'participated|described|indicated|identified|noted|perceived|experienced)\b',
    re.IGNORECASE,
)

# STY005: "which" without preceding comma (restrictive use)
_WHICH_NO_COMMA_RE = re.compile(r'(?<!,)\s+which\b(?!\s+(?:is|are|was|were|of|to|at|in|on|by|for|from|about|has|had|have|will|would|can|could|should|shall|may|might|must|do|did|does))')
# Exclude "in which", "of which", "at which", etc.
_WHICH_PREP_RE = re.compile(r'\b(in|of|at|by|from|for|on|to|with|about|after|before|during|through|between|among|into|within|without|despite|following|regarding|concerning)\s+which\b', re.IGNORECASE)

# STY006: Dangling modifier "Based on X, the study..."
_DANGLING_MOD_RE = re.compile(
    r'\bBased\s+on\s+[^,]+,\s+(?:the\s+)?(?:study|research|data|analysis|results?|findings?|paper|dissertation|literature)\b',
    re.IGNORECASE,
)

# STY007: Colloquialisms
_COLLOQUIAL_RE = re.compile(
    r'\b(gonna|wanna|gotta|kinda|sorta|lotta|a\s+lot\s+of|'
    r'tons?\s+of|pretty\s+much|basically|'
    r'super\s+(?:important|relevant|useful|helpful|significant)|'
    r'very\s+unique|very\s+perfect|very\s+essential|'
    r'really\s+important|really\s+significant|'
    r'totally|utterly(?!\s+impossible))\b',
    re.IGNORECASE,
)

# STY008: Third-person self-reference
_SELF_REF_RE = re.compile(
    r'\bthe\s+(?:present\s+)?(?:researcher[s]?|author[s]?|investigator[s]?|writer[s]?|scholar[s]?)\b',
    re.IGNORECASE,
)

# STY009: Contractions
_CONTRACTION_RE = re.compile(
    r"\b(?:can['']t|won['']t|don['']t|doesn['']t|"
    r"didn['']t|isn['']t|aren['']t|wasn['']t|weren['']t|"
    r"haven['']t|hasn['']t|hadn['']t|wouldn['']t|"
    r"shouldn['']t|couldn['']t|shan['']t|"
    r"I['']m|I['']ve|I['']ll|I['']d|"
    r"we['']re|we['']ve|we['']ll|we['']d|"
    r"they['']re|they['']ve|they['']ll|they['']d|"
    r"he['']s|she['']s|it['']s|that['']s|"
    r"there['']s|here['']s|who['']s|what['']s|"
    r"could['']ve|would['']ve|should['']ve|"
    r"might['']ve|must['']ve|let['']s)\b",
    re.IGNORECASE,
)
_CONTRACTION_MAP = {
    "can't": "cannot",   "won't": "will not",   "don't": "do not",
    "doesn't": "does not", "didn't": "did not",  "isn't": "is not",
    "aren't": "are not", "wasn't": "was not",   "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "wouldn't": "would not", "shouldn't": "should not",
    "couldn't": "could not", "it's": "it is",   "that's": "that is",
    "there's": "there is",   "who's": "who is", "what's": "what is",
    "could've": "could have", "would've": "would have",
    "should've": "should have", "let's": "let us",
}

# STY010: Bare demonstrative as sentence subject
_BARE_DEMO_RE = re.compile(
    r'(?:^|(?<=[.!?])\s+)'
    r'(This|These|That|Those)\s+'
    r'(?:is\b|are\b|was\b|were\b|shows?\b|suggest[s]?\b|indicate[s]?\b|'
    r'demonstrate[s]?\b|reveal[s]?\b|confirms?\b|highlight[s]?\b|'
    r'supports?\b|illustrates?\b|proves?\b|establishes?\b|underscores?\b)',
    re.IGNORECASE | re.MULTILINE,
)

# STY011: Latin abbreviations in running text
_LATIN_ABBREV_RE = re.compile(r'\b(e\.g\.|i\.e\.|cf\.|viz\.|etc\.|vs\.)', re.IGNORECASE)
_LATIN_EXPANSIONS = {
    "e.g.": "for example", "i.e.": "that is", "cf.": "compare",
    "viz.": "namely",       "etc.": "and so forth", "vs.": "versus",
}

# STY012: ibid.
_IBID_RE = re.compile(r'\bibid\.?\b', re.IGNORECASE)

# STY013: Hedging "would"
_HEDGING_RE = re.compile(
    r'\b(?:it\s+would\s+(?:appear|seem|suggest|indicate|follow)|'
    r'would\s+(?:appear|seem)\s+to\b|'
    r'seems?\s+to\s+(?:suggest|indicate)\b)',
    re.IGNORECASE,
)

# STY014: "while" for contrast
_WHILE_CONTRAST_RE = re.compile(
    r'(?:^|(?<=[.!?;])\s+|,\s*)while\b',
    re.IGNORECASE | re.MULTILINE,
)

# STY015: Anthropomorphism — cognitive/volitional verbs only (§4.11)
# APA §4.11 explicitly permits "the study found/discovered/explored/showed" etc.
# Only flag verbs that imply cognition, volition, or belief.
_ANTHRO_RE = re.compile(
    r'\bthe\s+(?:study|experiment|table|figure|analysis|data|results?|'
    r'findings?|article|paper|research|dissertation|literature|survey|'
    r'investigation|evidence)\s+'
    r'(?:concludes?|claims?|argues?|believes?|thinks?|feels?|knows?|'
    r'understands?|decides?|chooses?|wants?|seeks?|tries?|hopes?|expects?)\b',
    re.IGNORECASE,
)

# STY016: Disorder/condition over-capitalized (§6.20)
_DISORDER_CAP_RE = re.compile(
    r'\b(Autism\s+Spectrum\s+Disorder|Attention\s+Deficit\s+(?:Hyperactivity\s+)?Disorder|'
    r'Post[- ]Traumatic\s+Stress\s+Disorder|Major\s+Depressive\s+Disorder|'
    r'Obsessive[- ]Compulsive\s+Disorder|Bipolar\s+Disorder|'
    r'Generalized\s+Anxiety\s+Disorder|Social\s+Anxiety\s+Disorder|'
    r'Borderline\s+Personality\s+Disorder|Substance\s+Use\s+Disorder)\b',
)
# Only flag mid-sentence (not after a period/colon/opening or as abbreviation in parens)


# ===========================================================================
# CIT — In-text citation patterns
# ===========================================================================

# CIT001: "and" in parenthetical citation
_CIT_AND_PAREN_RE = re.compile(
    r'\((?P<authors>[A-Z][A-Za-z\-\' ]+\s+and\s+[A-Z][A-Za-z\-\' ]+),\s*\d{4}',
)

# CIT002: "&" in narrative citation
_CIT_AMP_NARR_RE = re.compile(
    r'(?P<authors>[A-Z][A-Za-z\-\' ]+\s+&\s+[A-Z][A-Za-z\-\' ]+)\s+\(\d{4}',
)

# CIT003: Three+ authors listed in full (should be et al.)
_CIT_THREE_PLUS_RE = re.compile(
    r'\((?:[A-Z][A-Za-z\-]+,\s+){2,}(?:&\s+)?[A-Z][A-Za-z\-]+,\s*\d{4}[a-z]?\)',
)

# CIT004: Multiple citations — check alphabetical order
_MULTI_CIT_RE = re.compile(r'\(([^)]+;\s*[^)]+)\)')
_CIT_SURNAME_RE = re.compile(r'([A-Z][A-Za-z\-\']+)(?:\s+et\s+al\.)?(?:,\s*n\.d\.|\s*,\s*\d{4})')

# CIT005: Wrong et al. format
_ETAL_WRONG_RE = re.compile(r'\bet\.al\b|\betal\b|\bet\s+al\b(?!\.)', re.IGNORECASE)
_ETAL_EXTRA_PERIOD_RE = re.compile(r'\bet\.\s+al\.', re.IGNORECASE)

# CIT006: Wrong n.d. format in citations
# (N.D.) must use a separate case-sensitive pattern — with IGNORECASE it also matches
# the CORRECT format (n.d.).
_ND_WRONG_CIT_RE = re.compile(
    r'\((?:[A-Z][A-Za-z\-\']+,\s+)?(?:nd|n\.d|no\s+date)\)',
    re.IGNORECASE,
)
_ND_WRONG_CIT_CAPS_RE = re.compile(
    r'\((?:[A-Z][A-Za-z\-\']+,\s+)?N\.D\.\)',  # case-sensitive: catches (N.D.) form
)

# CIT007: Direct quote missing page number
_INLINE_QUOTE_CIT_RE = re.compile(
    r'(?:"[^"]{1,500}"|'
    r'“[^”]{1,500}”)'
    r'\s*\(([^)]+)\)',
)

# CIT011: Repeated narrative citation in same paragraph
_NARRATIVE_CIT_RE = re.compile(
    r'[A-Z][A-Za-z\-\' ]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-\' ]+)?\s+\(\d{4}[a-z]?\)',
)

# CIT012: First name in parenthetical citation
_FIRST_NAME_PAREN_RE = re.compile(
    r'\(([A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d{4}',
)

# CIT014: Personal communication in reference list
_PERSONAL_COMM_RE = re.compile(r'\bpersonal\s+communication\b', re.IGNORECASE)

# CIT019: Over-citation (same citation ≥ 3x in one paragraph)
_ANY_CIT_RE = re.compile(
    r'\(([A-Z][A-Za-z\-\' ]+(?:\s+et\s+al\.)?(?:\s*&\s*[A-Z][A-Za-z\-\']+)?),'
    r'\s*(?:n\.d\.|\d{4}[a-z]?)',
)

_GROUP_AUTHOR_WORD_RE = re.compile(
    r'\b(?:Association|Agency|Board|Bureau|Center|Centre|Committee|Commission|'
    r'Council|Department|Foundation|Group|Institute|Ministry|Office|Organization|'
    r'Organisation|Research|Services|University|Inc|LLC|Ltd|Corp|Company|'
    r'Gartner|PwC|Deloitte|McKinsey|Forrester|Markets)\b',
    re.IGNORECASE,
)


def _looks_like_group_author_name(author_text: str) -> bool:
    return bool(_GROUP_AUTHOR_WORD_RE.search(author_text))


# ===========================================================================
# TBL — Table rule patterns (prose references to tables)
# ===========================================================================

# TBL001: Positional references ("table above/below")
_TBL_POSITION_RE = re.compile(
    r'\b(?:table|figure|chart)\s+(?:above|below|on\s+the\s+(?:following|next|previous|preceding)\s+page)\b',
    re.IGNORECASE,
)

# TBL002: Roman numeral table numbers
_TBL_ROMAN_RE = re.compile(
    r'\b(?:Table|Figure)\s+([IVX]{1,6})\b',
)

# TBL005: Table or figure not called out in text
# (checked at document level, not per-paragraph)

# TBL003: Letter suffix on table/figure number (§7.19: no "Table 1A" or "Table 1B")
_TBL_LETTER_SUFFIX_RE = re.compile(
    r'\bTable\s+\d+[A-Za-z]\b',
)

# TBL006: "See Table X for" → APA prefers embedding in text
_TBL_SEE_RE = re.compile(
    r'\bSee\s+(?:Table|Figure)\s+\d+\s+for\b',
    re.IGNORECASE,
)


# ===========================================================================
# HED — Heading helpers
# ===========================================================================

_HEADING_STYLES_MAP = {
    "Heading 1": 1, "Heading 2": 2, "Heading 3": 3,
    "Heading 4": 4, "Heading 5": 5,
}


# ===========================================================================
# Rule checkers — one function per category
# ===========================================================================

def _check_mec(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """MEC001–MEC022: Mechanics and Formatting."""
    idx = para.index
    text = para.raw_text
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.MECHANICS.value

    def _add(rule_id, sev, msg, fix="", auto=False, exc="", ch=""):
        findings.append(Finding(
            rule_id=rule_id, severity=sev, paragraph_index=idx,
            message=msg, suggested_fix=fix, autofixable=auto,
            excerpt=exc or text[:80], location_hint=loc,
            category=cat, chapter=ch,
        ))

    # MEC023 - Body paragraph first-line indent (DOCX uploads only).
    if _is_indent_check_candidate(para):
        indent = getattr(para, "first_line_indent_twips", None)
        if indent is None or abs(indent - _APA_FIRST_LINE_INDENT_TWIPS) > _APA_FIRST_LINE_INDENT_TOLERANCE:
            _add(
                "MEC023",
                Severity.WARNING,
                "APA §2.24: Indent the first line of each body paragraph 0.5 in. (1.27 cm). "
                "This paragraph does not appear to have the required first-line indent.",
                "Set first-line indentation to 1.27 cm / 0.5 in. for this body paragraph.",
                False,
                text[:80],
                "§2.24",
            )

    # MEC001 — Double space after period
    for m in _DOUBLE_SPACE_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC001", Severity.WARNING,
             "APA §6.1: Use one space after a period. Double (or more) spaces detected.",
             "Remove extra space(s) after the period.", True,
             _excerpt(masked, m.start(), m.end()), "§6.1")

    # MEC002 — Sentence-starting numeral
    for m in _SENTENCE_START_NUM_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC002", Severity.WARNING,
             f"APA §6.33: Do not begin a sentence with a numeral ('{m.group().strip()}'). "
             "Reword the sentence or spell out the number if below 10.",
             "Reword sentence so the numeral is not first.",
             exc=masked[m.start():min(len(masked), m.end() + 40)].strip()[:80],
             ch="§6.33")

    # MEC003 — Small numeral 1–9
    numeral_threshold = cfg.get("numeral_threshold", 10)
    for m in _NUMERIC_TOKEN_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        token = m.group(1)
        if len(token) != 1:
            continue
        num = int(token)
        if num < numeral_threshold and not _exempt_numeral(masked, m):
            _add("MEC003", Severity.WARNING,
                 f"APA §6.33: Spell out numbers zero through nine in prose. "
                 f"'{m.group()}' → '{_NUM_WORDS.get(num, m.group())}'.",
                 f"Replace '{m.group()}' with '{_NUM_WORDS.get(num, m.group())}'",
                 True, _excerpt(masked, m.start(), m.end()), "§6.33")

    # MEC004 — Number ≥10 as words
    # APA §6.33 exception: numbers that BEGIN a sentence must be spelled out (or reworded).
    # So "Fifteen participants completed…" is correct. Only flag mid-sentence word-form numbers.
    _SENTENCE_START_RE = re.compile(r'(?:^|(?<=[.!?])\s+)', re.MULTILINE)
    _sentence_starts = {m.end() for m in _SENTENCE_START_RE.finditer(masked)}

    for m in _WORD_NUMS_HIGH.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        if _WORD_NUM_EXEMPT_RE.search(masked[max(0, m.start() - 5):m.end() + 10]):
            continue
        # Exempt if at the start of a sentence (APA §6.33 requires spelling out there)
        if m.start() in _sentence_starts:
            continue
        _add("MEC004", Severity.WARNING,
             f"APA §6.32: Numbers 10 and above should be expressed as numerals, not words. "
             f"'{m.group()}' should be written as a numeral.",
             f"Replace '{m.group()}' with its numeral form.",
             exc=_excerpt(masked, m.start(), m.end()), ch="§6.32")

    # MEC006 — "N percent" → "N%"
    for m in _N_PERCENT_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC006", Severity.WARNING,
             f"APA §6.44: Use the % symbol when preceded by a numeral. "
             f"'{m.group()}' → '{m.group(1)}%'.",
             f"Replace '{m.group()}' with '{m.group(1)}%'",
             True, _excerpt(masked, m.start(), m.end()), "§6.44")

    # MEC007 — p value with leading zero
    for m in _P_ZERO_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        corrected = m.group().replace('0.', '.').replace('0 .', ' .')
        _add("MEC007", Severity.WARNING,
             f"APA §6.36: p values cannot exceed 1, so no leading zero is used. "
             f"'{m.group()}' → drop the leading zero: p = .{m.group(1)}'.",
             f"Remove leading zero from p value", True,
             _excerpt(masked, m.start(), m.end()), "§6.36")

    # MEC008 — Correlation (r) with leading zero
    for m in _R_ZERO_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC008", Severity.WARNING,
             f"APA §6.36: Correlations and proportions cannot exceed 1, so no leading zero. "
             f"'{m.group()}' → drop the leading zero: '.{m.group(1)}'.",
             "Remove leading zero from correlation value", True,
             _excerpt(masked, m.start(), m.end()), "§6.36")

    # MEC009 — p value threshold-only (p < .05)
    for m in _P_THRESHOLD_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC009", Severity.WARNING,
             f"APA §6.43: Report exact p values rather than threshold comparisons. "
             f"'{m.group()}' should be replaced with the exact p value (e.g., p = .032). "
             "Exception: use p < .001 when the value is smaller than .001.",
             "Report exact p value (e.g., p = .032)",
             exc=_excerpt(masked, m.start(), m.end()), ch="§6.43")

    # MEC010 — Missing comma in 4+ digit numbers
    for m in _BIG_NUM_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        raw = m.group(1)
        if _BIG_NUM_YEAR_RE.match(raw):
            continue
        ctx = masked[max(0, m.start() - 20):m.end() + 20]
        if _BIG_NUM_CONTEXT_EXEMPT.search(ctx):
            continue
        # Check no comma already
        if ',' not in raw and len(raw) >= 4:
            # Format with commas
            formatted = f"{int(raw):,}"
            _add("MEC010", Severity.WARNING,
                 f"APA §6.38: Numbers of 1,000 or more use commas to separate groups of three digits. "
                 f"'{raw}' → '{formatted}'. "
                 "Exceptions: page numbers, degrees of freedom, serial numbers.",
                 f"Replace '{raw}' with '{formatted}'", True,
                 _excerpt(masked, m.start(), m.end()), "§6.38")

    # MEC011 — Apostrophe in number plural
    for m in _NUM_APOSTROPHE_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        corrected = m.group().replace("'s", "s")
        _add("MEC011", Severity.ERROR,
             f"APA §6.39: Form the plural of numbers without an apostrophe: "
             f"'{m.group()}' → '{corrected}'.",
             f"Replace '{m.group()}' with '{corrected}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.39")

    # MEC012 — Spaced em dash
    for m in _SPACED_EMDASH_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC012", Severity.WARNING,
             "APA §6.6: Em dashes (—) should not be surrounded by spaces. "
             "Remove the spaces immediately before and after the em dash.",
             "Remove spaces around the em dash: word—word",
             True, _excerpt(masked, m.start(), m.end()), "§6.6")

    # MEC013 — -ly adverb hyphenation
    for m in _LY_HYPHEN_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        if not _looks_like_ly_adverb(m.group(1)):
            continue
        corrected = f"{m.group(1)} {m.group(2)}"
        _add("MEC013", Severity.WARNING,
             f"APA §6.12: Do not hyphenate compound modifiers that include an adverb ending in '-ly'. "
             f"'{m.group()}' → '{corrected}'.",
             f"Replace '{m.group()}' with '{corrected}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.12")

    # MEC014 — Time unit spelled out with numeral
    for m in _TIME_UNIT_SPELLED_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        unit = m.group(2).lower()
        abbrev = _TIME_ABBREV_MAP.get(unit, unit)
        _add("MEC014", Severity.WARNING,
             f"APA §6.28: Abbreviate time units when paired with a numeral. "
             f"'{m.group()}' → '{m.group(1)} {abbrev}'.",
             f"Replace '{m.group()}' with '{m.group(1)} {abbrev}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.28")

    # Wrong day/week/month abbreviations
    for m in _TIME_WRONG_ABBREV_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC014", Severity.WARNING,
             f"APA §6.28: Do not abbreviate day, week, or month even when paired with a numeral. "
             f"Write them out in full: '3 days', '2 weeks', '6 months'.",
             "Write out the time unit in full",
             exc=_excerpt(masked, m.start(), m.end()), ch="§6.28")

    # MEC015 — Plural unit symbols
    for m in _PLURAL_UNIT_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC015", Severity.WARNING,
             f"APA §6.27: Unit symbols are not pluralized. "
             f"'{m.group().strip()}' — remove the trailing 's'.",
             "Remove the 's' from the unit symbol",
             exc=_excerpt(masked, m.start(), m.end()), ch="§6.27")

    # MEC018 — Series noun uncapitalized
    for m in _SERIES_NOUN_LC_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        corrected = m.group(1).capitalize() + " " + m.group(2)
        _add("MEC018", Severity.WARNING,
             f"APA §6.19: Nouns that precede a numeral in a series are capitalized. "
             f"'{m.group()}' → '{corrected}'.",
             f"Capitalize: '{corrected}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.19")

    # MEC019 — "Page" / "Paragraph" capitalized before numeral
    for m in _PAGE_PARA_CAP_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        corrected = m.group().lower()
        _add("MEC019", Severity.WARNING,
             f"APA §6.19: 'page' and 'paragraph' are NOT capitalized before numerals. "
             f"'{m.group()}' → '{corrected}'.",
             f"Use lowercase: '{corrected}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.19")

    # MEC020 — Inline quote ≥ 40 words (block quote required)
    # Rough check via character count (150+ chars ≈ 40+ words)
    for m in _INLINE_QUOTE_CONTENT_RE.finditer(text):
        quoted = (m.group(1) or m.group(2) or "").strip()
        word_count = len(quoted.split())
        if word_count >= 40:
            _add("MEC020", Severity.WARNING,
                 f"APA §8.25: Quoted text of {word_count} words must use block-quotation format "
                 "(indented 0.5 in., no quotation marks, citation after final punctuation). "
                 "Do not use inline double-quotation marks for quotations of 40 or more words.",
                 "Format as a block quotation: indent 0.5 in., remove quotation marks.",
                 exc=quoted[:80], ch="§8.25")

    # MEC021 — Wrong ellipsis format in quotations
    # Flag "..." or "…" inside quoted text (should be ". . ." with spaces)
    for q_match in re.finditer(r'"([^"]+)"|"([^"]+)"', text):
        q_text = q_match.group(1) or q_match.group(2) or ""
        for e_match in _WRONG_ELLIPSIS_RE.finditer(q_text):
            # Only flag if it looks like an omission (not end of sentence)
            if not q_text[e_match.end():e_match.end() + 1].strip():
                continue
            _add("MEC021", Severity.WARNING,
                 "APA §8.30: Within a quotation, use spaced ellipsis points (. . .) to indicate "
                 "omissions, not '...' or the ellipsis character (…).",
                 "Replace '...' or '…' with '. . .' (with spaces)",
                 exc=q_text[:80], ch="§8.30")
            break  # one finding per quote

    # MEC022 — Adjacent numerals (ambiguous: "2 5-point scales")
    for m in _ADJACENT_NUM_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("MEC022", Severity.WARNING,
             f"APA §6.34: Two adjacent numerals are ambiguous: '{m.group().strip()}'. "
             "Combine a word and a numeral to clarify: e.g., 'two 5-point scales' or '2 five-point scales'.",
             "Combine word + numeral to avoid ambiguity",
             exc=_excerpt(masked, m.start(), m.end()), ch="§6.34")

    # MEC017 — Wordy title phrases (check first ~200 chars only — likely title/abstract)
    if para.index < 5:
        for m in _WORDY_TITLE_RE.finditer(text):
            _add("MEC017", Severity.SUGGESTION,
                 f"APA §2.4: Avoid wordy opening phrases in titles such as '{m.group()}'. "
                 "The title should be concise and specific.",
                 "Remove the wordy phrase and start with the substantive content.",
                 exc=text[:80], ch="§2.4")


def _check_sty(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """STY001–STY016: Style and Grammar."""
    idx = para.index
    text = para.raw_text
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.STYLE.value

    def _add(rule_id, sev, msg, fix="", auto=False, exc="", ch=""):
        findings.append(Finding(
            rule_id=rule_id, severity=sev, paragraph_index=idx,
            message=msg, suggested_fix=fix, autofixable=auto,
            excerpt=exc or text[:80], location_hint=loc,
            category=cat, chapter=ch,
        ))

    # STY001 — Passive voice (suggestion, with statistical exemptions)
    for m in _PASSIVE_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        if _STAT_PASSIVE_EXEMPT_RE.search(masked[max(0, m.start() - 5):m.end() + 20]):
            continue
        _add("STY001", Severity.SUGGESTION,
             f"APA §4.13: Passive voice detected ('{m.group().strip()}'). "
             "Prefer active voice in scholarly writing — recast with an explicit subject.",
             "Recast as active voice.",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.13")

    # STY002 — Redundant phrases
    for pat, fix in _REDUNDANT_RES:
        for m in pat.finditer(masked):
            if _near_quote_mask(masked, m.start(), m.end()):
                continue
            _add("STY002", Severity.SUGGESTION,
                 f"APA §4.5: Redundant phrasing — '{m.group().strip()}' can be simplified to '{fix}'.",
                 f"Replace with '{fix}'", True,
                 _excerpt(masked, m.start(), m.end()), "§4.5")

    # STY003 — Wordy expressions
    for pat, fix in _WORDY_RES:
        for m in pat.finditer(masked):
            if _near_quote_mask(masked, m.start(), m.end()):
                continue
            _add("STY003", Severity.SUGGESTION,
                 f"APA §4.4: Wordy phrase — '{m.group().strip()}'. Consider replacing with '{fix}'.",
                 f"Replace with '{fix}'", True,
                 _excerpt(masked, m.start(), m.end()), "§4.4")

    # STY004 — "that" for people
    for m in _THAT_PEOPLE_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        corrected = m.group().replace(" that ", " who ")
        _add("STY004", Severity.WARNING,
             f"APA §4.19: Use 'who' (not 'that') to refer to people. "
             f"'{m.group().strip()}' → '{corrected.strip()}'.",
             f"Replace 'that' with 'who'", True,
             _excerpt(masked, m.start(), m.end()), "§4.19")

    # STY005 — "which" without comma (may be restrictive — should be "that")
    for m in _WHICH_NO_COMMA_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        ctx = masked[max(0, m.start() - 30):m.end() + 5]
        if _WHICH_PREP_RE.search(ctx):
            continue
        _add("STY005", Severity.SUGGESTION,
             "APA §4.21: 'which' without a preceding comma introduces a restrictive clause. "
             "APA Style reserves 'which' for nonrestrictive clauses (preceded by a comma). "
             "Use 'that' for restrictive clauses, or add a comma if the clause is nonrestrictive.",
             "Use 'that' for restrictive clauses, or add a comma before 'which' if nonrestrictive.",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.21")

    # STY006 — Dangling modifier
    for m in _DANGLING_MOD_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY006", Severity.WARNING,
             f"APA §4.23: Possible dangling modifier — '{m.group().strip()}'. "
             "The phrase 'Based on X' must be followed by a human agent, not a non-human subject. "
             "E.g., 'Based on the findings, we conclude…' not 'Based on the findings, the study suggests…'",
             "Recast: 'Based on X, we/I found…'",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.23")

    # STY007 — Colloquialisms
    for m in _COLLOQUIAL_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY007", Severity.SUGGESTION,
             f"APA §4.8: Colloquial or informal language detected: '{m.group().strip()}'. "
             "Academic writing requires formal, precise vocabulary.",
             "Replace with more formal academic language.",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.8")

    # STY008 — Third-person self-reference
    for m in _SELF_REF_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY008", Severity.WARNING,
             f"APA §4.16: Do not refer to yourself in the third person ('{m.group().strip()}'). "
             "Use first-person pronouns: 'I' (sole author) or 'we' (multiple authors).",
             f"Replace '{m.group().strip()}' with 'I' or 'we'",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.16")

    # STY009 — Contractions
    for m in _CONTRACTION_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        raw = m.group().lower().replace("’", "'")
        expansion = _CONTRACTION_MAP.get(raw, "expand this contraction")
        _add("STY009", Severity.WARNING,
             f"APA §4.7: Avoid contractions in scholarly writing. "
             f"'{m.group()}' → '{expansion}'.",
             f"Replace '{m.group()}' with '{expansion}'", True,
             _excerpt(masked, m.start(), m.end()), "§4.7")

    # STY010 — Bare demonstrative as subject
    for m in _BARE_DEMO_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY010", Severity.SUGGESTION,
             f"APA §4.11: Bare demonstrative as subject — '{m.group().strip()}'. "
             "Add a specific noun after the demonstrative for clarity: "
             "'This finding shows…' not 'This shows…'.",
             "Add a specific noun: 'This [noun] shows…'",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.11")

    # STY011 — Latin abbreviations in running text
    for m in _LATIN_ABBREV_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        if _is_in_parentheses(masked, m.start()):
            continue
        abbrev = m.group().lower()
        expansion = _LATIN_EXPANSIONS.get(abbrev, "the English equivalent")
        _add("STY011", Severity.WARNING,
             f"APA §6.29: '{m.group()}' should appear only in parenthetical text. "
             f"In running (narrative) text, use '{expansion}' instead.",
             f"Replace '{m.group()}' with '{expansion}'", True,
             _excerpt(masked, m.start(), m.end()), "§6.29")

    # STY012 — ibid.
    for m in _IBID_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY012", Severity.ERROR,
             "APA §8.16: 'ibid.' is never used in APA Style. "
             "Repeat the full citation or use the shortened narrative form.",
             "Remove 'ibid.' and provide the full or shortened citation.",
             exc=_excerpt(masked, m.start(), m.end()), ch="§8.16")

    # STY013 — Hedging "would"
    for m in _HEDGING_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY013", Severity.SUGGESTION,
             f"APA §4.14: Avoid hedging with 'would' for factual statements. "
             f"'{m.group().strip()}' → use the indicative: 'it appears', 'it seems', 'the findings suggest'.",
             "Replace with indicative mood: 'it appears', 'it seems', 'the data suggest'",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.14")

    # STY014 — "while" for contrast
    for m in _WHILE_CONTRAST_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY014", Severity.SUGGESTION,
             "APA §4.22: 'while' should be used only for simultaneous events. "
             "If expressing contrast or concession, use 'although', 'whereas', or 'but' instead.",
             "Replace 'while' with 'although', 'whereas', or 'but' (as appropriate)",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.22")

    # STY015 — Anthropomorphism
    for m in _ANTHRO_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("STY015", Severity.SUGGESTION,
             f"APA §4.11: Avoid attributing human characteristics to inanimate entities: "
             f"'{m.group().strip()}'. Use 'the findings indicate…' or 'we conclude…' instead.",
             "Recast with a human agent or use 'the findings indicate/show/suggest'",
             exc=_excerpt(masked, m.start(), m.end()), ch="§4.11")

    # STY016 — Disorder/condition over-capitalized mid-sentence
    for m in _DISORDER_CAP_RE.finditer(text):
        # Only flag if not at sentence start
        pre = text[:m.start()].rstrip()
        if pre and pre[-1] not in '.!?:':
            _add("STY016", Severity.WARNING,
                 f"APA §6.20: Clinical/diagnostic condition names are not capitalized unless part of "
                 f"an official proper-noun designation or at sentence start. "
                 f"Consider lowercase for '{m.group()}' unless it is the exact DSM/ICD title.",
                 "Use lowercase for condition names unless they are proper nouns or official titles.",
                 exc=_excerpt(text, m.start(), m.end()), ch="§6.20")


def _check_bfl(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """BFL001–BFL032+: Bias-Free Language (§5). All findings are SUGGESTION."""
    idx = para.index
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.BIAS_FREE.value

    for rule in BFL_RULES:
        for m in rule.pattern.finditer(masked):
            if _near_quote_mask(masked, m.start(), m.end()):
                continue
            findings.append(Finding(
                rule_id=rule.rule_id,
                severity=Severity.SUGGESTION,
                paragraph_index=idx,
                message=rule.message,
                suggested_fix=f"Consider replacing '{m.group()}' with '{rule.replacement}'",
                autofixable=False,
                excerpt=_excerpt(masked, m.start(), m.end()),
                location_hint=loc,
                category=cat,
                chapter=rule.chapter,
            ))


def _check_hed(
    paragraphs: list[ProseParagraph],
    heading_cfg: dict,
    findings: list[Finding],
) -> None:
    """HED001–HED002: Heading Structure (§2.27)."""
    cat = Category.HEADING.value
    prev_level: Optional[int] = None

    for i, para in enumerate(paragraphs):
        if para.is_reference_entry:
            continue

        if para.heading_level is not None and para.heading_level >= 1:
            level = para.heading_level
            loc = _loc(para)

            # HED001 — Skipped heading level
            if (
                heading_cfg.get("flag_skipped_heading_levels", True)
                and prev_level is not None
                and level > prev_level + 1
            ):
                findings.append(Finding(
                    rule_id="HED001",
                    severity=Severity.WARNING,
                    paragraph_index=para.index,
                    message=(
                        f"APA §2.27: Heading level skipped — Level {prev_level} → Level {level}. "
                        "Heading levels must be sequential; never jump from a lower to a higher level "
                        "by skipping an intermediate level."
                    ),
                    excerpt=para.raw_text[:80],
                    location_hint=loc,
                    category=cat,
                    chapter="§2.27",
                ))
            prev_level = level

    # HED002 — Heading immediately followed by another real heading with no body
    # prose between them. Layout elements (heading_level=0) are neutral: they are
    # skipped for this scan and do not themselves satisfy the body-text requirement.
    if heading_cfg.get("flag_heading_without_body", True):
        for i in range(len(paragraphs)):
            cur = paragraphs[i]
            if not (
                cur.heading_level is not None
                and cur.heading_level >= 1
                and not cur.is_reference_entry
            ):
                continue

            nxt = None
            for candidate in paragraphs[i + 1:]:
                if candidate.is_reference_entry:
                    break
                if candidate.heading_level is None:
                    break
                if candidate.heading_level >= 1:
                    nxt = candidate
                    break

            if (
                nxt is not None
                # Only flag when the next heading is at the same or higher
                # (more general) level.  A Level-1 heading immediately followed
                # by a Level-2 subheading is valid APA structure and must not
                # be flagged.  Level-2 → Level-2 or Level-2 → Level-1 (empty
                # section) are genuine violations.
                and nxt.heading_level <= cur.heading_level
            ):
                findings.append(Finding(
                    rule_id="HED002",
                    severity=Severity.WARNING,
                    paragraph_index=cur.index,
                    message=(
                        f"APA §2.27: Heading '{cur.raw_text[:60]}' is immediately followed by "
                        "another heading with no body text between them. "
                        "Add at least one prose paragraph after each heading."
                    ),
                    excerpt=cur.raw_text[:80],
                    location_hint=_loc(cur),
                    category=cat,
                    chapter="§2.27",
                ))


def _check_cit(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """CIT001–CIT019: In-Text Citations (§8)."""
    idx = para.index
    text = para.raw_text
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.CITATION.value

    def _add(rule_id, sev, msg, fix="", auto=False, exc="", ch=""):
        findings.append(Finding(
            rule_id=rule_id, severity=sev, paragraph_index=idx,
            message=msg, suggested_fix=fix, autofixable=auto,
            excerpt=exc or text[:80], location_hint=loc,
            category=cat, chapter=ch,
        ))

    # CIT001 — "and" in parenthetical citation (should be &)
    for m in _CIT_AND_PAREN_RE.finditer(text):
        if _looks_like_group_author_name(m.group("authors")):
            continue
        _add("CIT001", Severity.ERROR,
             f"APA §8.13: Use '&' (not 'and') between author names inside parenthetical citations. "
             f"Found: '{m.group()[:60]}'.",
             "Replace 'and' with '&' inside parenthetical citations",
             exc=text[m.start():min(len(text), m.end() + 5)].strip()[:80], ch="§8.13")

    # CIT002 — "&" in narrative citation (should be "and")
    for m in _CIT_AMP_NARR_RE.finditer(text):
        if _looks_like_group_author_name(m.group("authors")):
            continue
        _add("CIT002", Severity.ERROR,
             f"APA §8.13: Use 'and' (not '&') between author names in narrative citations. "
             f"Found: '{m.group()[:60]}'.",
             "Replace '&' with 'and' in narrative citations",
             exc=text[m.start():min(len(text), m.end() + 5)].strip()[:80], ch="§8.13")

    # CIT003 — Three+ authors fully listed (should be et al.)
    for m in _CIT_THREE_PLUS_RE.finditer(text):
        _add("CIT003", Severity.ERROR,
             f"APA §8.17: For sources with three or more authors, use 'et al.' from the first citation. "
             f"'{m.group()[:80]}' should be shortened to 'Author et al., YYYY'.",
             "Shorten to: (First Author et al., YYYY)",
             exc=m.group()[:80], ch="§8.17")

    # CIT004 — Multiple citations not in alphabetical order
    for m in _MULTI_CIT_RE.finditer(text):
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(';')]
        surnames = []
        for part in parts:
            sm = _CIT_SURNAME_RE.match(part.strip())
            if sm:
                surnames.append(sm.group(1).lower())
        if len(surnames) >= 2:
            for i in range(len(surnames) - 1):
                if surnames[i] > surnames[i + 1]:
                    _add("CIT004", Severity.WARNING,
                         f"APA §8.19: Multiple citations in one set of parentheses must be ordered "
                         f"alphabetically by first author's surname. "
                         f"Found: '({inner[:80]})'.",
                         "Reorder citations alphabetically by first author surname",
                         exc=m.group()[:80], ch="§8.19")
                    break

    # CIT005 — Wrong et al. format
    for m in _ETAL_WRONG_RE.finditer(text):
        _add("CIT005", Severity.ERROR,
             f"APA §8.18: Incorrect 'et al.' format — '{m.group()}'. "
             "Correct format: 'et al.' — lowercase, space between 'et' and 'al', period after 'al' only.",
             "Replace with 'et al.'", True,
             exc=_excerpt(text, m.start(), m.end()), ch="§8.18")

    for m in _ETAL_EXTRA_PERIOD_RE.finditer(text):
        _add("CIT005", Severity.ERROR,
             f"APA §8.18: 'et.' should not have a period — '{m.group()}' → 'et al.'",
             "Replace 'et.' with 'et'", True,
             exc=_excerpt(text, m.start(), m.end()), ch="§8.18")

    # CIT006 — Wrong n.d. format in citations
    for m in list(_ND_WRONG_CIT_RE.finditer(text)) + list(_ND_WRONG_CIT_CAPS_RE.finditer(text)):
        _add("CIT006", Severity.WARNING,
             f"APA §8.22: Incorrect no-date format '{m.group()}'. "
             "Use '(Author, n.d.)' — 'n.d.' with periods after each letter.",
             "Replace with '(Author, n.d.)'",
             exc=_excerpt(text, m.start(), m.end()), ch="§8.22")

    # CIT007 — Direct quote missing page number
    for m in _INLINE_QUOTE_CIT_RE.finditer(text):
        cit_content = m.group(1) or ""
        if not re.search(r'p{1,2}\.\s*\d+|para\.\s*\d+', cit_content):
            _add("CIT007", Severity.WARNING,
                 "APA §8.23: Direct quotations require a page number (p. X) or paragraph number "
                 "(para. X) in the citation. The citation appears to be missing a page/paragraph locator.",
                 "Add page number: (Author, YYYY, p. X)",
                 exc=text[m.start():min(len(text), m.end() + 5)].strip()[:80], ch="§8.23")

    # CIT011 — Repeated narrative citation in same paragraph
    if cfg.get("flag_repeated_narrative_citations", True):
        seen: dict[str, int] = {}
        for m in _NARRATIVE_CIT_RE.finditer(text):
            key = re.sub(r'\s+', ' ', m.group().strip())
            seen[key] = seen.get(key, 0) + 1
        for cite_key, count in seen.items():
            if count > 1:
                _add("CIT011", Severity.INFO,
                     f"APA §8.16: '{cite_key}' appears {count} times as a narrative citation "
                     "in the same paragraph. After the first full citation, the year may be omitted: "
                     "'Smith also argued…'",
                     "Omit the year on subsequent narrative mentions within the same paragraph",
                     exc=text[:80], ch="§8.16")

    # CIT012 — First name in parenthetical citation
    for m in _FIRST_NAME_PAREN_RE.finditer(text):
        _add("CIT012", Severity.WARNING,
             f"APA §8.11: Parenthetical citations use only the author's surname. "
             f"'{m.group()[:60]}' appears to include a first name.",
             "Use only the surname in parenthetical citations: (Surname, YYYY)",
             exc=_excerpt(text, m.start(), m.end()), ch="§8.11")

    # CIT014 — Personal communication cited in text (must NOT appear in reference list)
    if _PERSONAL_COMM_RE.search(text):
        _add("CIT014", Severity.INFO,
             "APA §8.9: Personal communications (emails, interviews, conversations) are cited in text "
             "only — they do NOT appear in the reference list because they cannot be retrieved.",
             "Ensure this personal communication is NOT listed in the References section",
             exc=text[:80], ch="§8.9")

    # CIT019 — Over-citation (same citation ≥ 3x in one paragraph)
    cit_counts: dict[str, int] = {}
    for m in _ANY_CIT_RE.finditer(text):
        key = m.group(1).strip().lower()
        cit_counts[key] = cit_counts.get(key, 0) + 1
    for cite, count in cit_counts.items():
        if count >= 3:
            _add("CIT019", Severity.INFO,
                 f"APA §8.1: '{cite}' is cited {count} times in a single paragraph. "
                 "Over-citation reduces readability. Cite once at the most relevant point; "
                 "subsequent sentences can omit the citation when the source is clear.",
                 "Reduce to one citation per paragraph per source (where context is clear)",
                 exc=text[:80], ch="§8.1")


def _check_ref_entries(
    ref_paragraphs: list[ProseParagraph],
    cfg: dict,
    findings: list[Finding],
) -> None:
    """REF001–REF021: Reference List Rules (§9)."""
    entries = [
        {"index": p.index, "text": p.raw_text, "raw_text": p.raw_text}
        for p in ref_paragraphs
        if p.is_reference_entry
    ]
    if not entries:
        return

    para_by_index = {p.index: p for p in ref_paragraphs}
    raw_findings = check_ref_entries(entries, cfg)
    for rf in raw_findings:
        para = para_by_index.get(rf["paragraph_index"])
        findings.append(Finding(
            rule_id=rf["rule_id"],
            severity=Severity.WARNING if rf["severity"] == "warning" else Severity.ERROR,
            paragraph_index=rf["paragraph_index"],
            message=rf["message"],
            suggested_fix=rf.get("suggested_fix", ""),
            excerpt=rf.get("excerpt", ""),
            location_hint=_loc(para) if para else rf.get("location_hint", ""),
            category=Category.REFERENCE.value,
            chapter=rf.get("chapter", "§9"),
        ))


def _check_tbl(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """TBL001–TBL006: Table and Figure rules (§7)."""
    idx = para.index
    text = para.raw_text
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.TABLE.value

    def _add(rule_id, sev, msg, fix="", exc="", ch=""):
        findings.append(Finding(
            rule_id=rule_id, severity=sev, paragraph_index=idx,
            message=msg, suggested_fix=fix,
            excerpt=exc or text[:80], location_hint=loc,
            category=cat, chapter=ch,
        ))

    # TBL001 — Positional references ("table above/below")
    for m in _TBL_POSITION_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("TBL001", Severity.WARNING,
             f"APA §7.2: Do not refer to tables or figures by position ('{m.group()}') because "
             "position can change during typesetting. Use the table/figure number instead: "
             "'as shown in Table 3'.",
             "Replace positional reference with 'Table X' or 'Figure X'",
             _excerpt(masked, m.start(), m.end()), "§7.2")

    # TBL002 — Roman numeral table/figure numbers
    for m in _TBL_ROMAN_RE.finditer(text):
        _add("TBL002", Severity.WARNING,
             f"APA §7.10: Use Arabic numerals for table and figure numbers, not Roman numerals. "
             f"'{m.group()}' should use an Arabic numeral.",
             f"Replace '{m.group()}' with an Arabic numeral",
             _excerpt(text, m.start(), m.end()), "§7.10")

    # TBL003 — Letter suffix on table number (§7.19)
    for m in _TBL_LETTER_SUFFIX_RE.finditer(text):
        _add("TBL003", Severity.WARNING,
             f"APA §7.19: Do not use letters to distinguish subtables "
             f"(e.g., '{m.group()}' is incorrect). Number them separately as Table 1 and Table 2.",
             f"Remove the letter suffix and assign a separate sequential number",
             _excerpt(text, m.start(), m.end()), "§7.19")

    # TBL006 — "See Table X for" construction (prefer in-text integration)
    for m in _TBL_SEE_RE.finditer(masked):
        if _near_quote_mask(masked, m.start(), m.end()):
            continue
        _add("TBL006", Severity.INFO,
             f"APA §7.2: '{m.group().strip()}' — APA recommends integrating table references "
             "into the prose (e.g., 'The descriptive statistics (Table 3) show…') rather than "
             "directing the reader with 'See Table X for…'.",
             "Integrate the reference naturally into the sentence",
             _excerpt(masked, m.start(), m.end()), "§7.2")


def _check_prf(para: ProseParagraph, cfg: dict, findings: list[Finding]) -> None:
    """PRF001–PRF003: Program/Professor Requirements (configurable)."""
    idx = para.index
    text = para.raw_text
    masked = para.masked_text
    loc = _loc(para)
    cat = Category.PROFESSOR.value

    def _add(rule_id, sev, msg, fix="", ch=""):
        findings.append(Finding(
            rule_id=rule_id, severity=sev, paragraph_index=idx,
            message=msg, suggested_fix=fix,
            excerpt=text[:80], location_hint=loc,
            category=cat, chapter=ch,
        ))

    min_s = cfg.get("min_sentences_per_paragraph", 2)
    max_s = cfg.get("max_sentences_per_paragraph", 0)
    flag_pronouns = cfg.get("flag_first_person_pronouns", False)

    clean = masked.replace(QUOTE_MASK, "").strip()
    if clean:
        sentence_count = len(_sentences(clean))

        # PRF001 — Paragraph too short
        if sentence_count < min_s:
            _add("PRF001", Severity.INFO,
                 f"Short paragraph: {sentence_count} sentence(s) detected "
                 f"(program minimum: {min_s}). "
                 "APA §4.6: single-sentence paragraphs are abrupt — use infrequently.",
                 "Expand this paragraph or merge it with an adjacent one.",
                 "§4.6")

        # PRF002 — Paragraph too long
        if max_s and sentence_count > max_s:
            _add("PRF002", Severity.INFO,
                 f"Long paragraph: {sentence_count} sentences detected "
                 f"(program maximum: {max_s}). "
                 "Consider breaking this paragraph into two focused paragraphs.",
                 "Split into two paragraphs.")

    # PRF003 — First-person pronouns (off by default; APA §4.16 endorses them)
    if flag_pronouns:
        _PRONOUN_RE = re.compile(r'\b(we|us|our|I|me|my)\b', re.IGNORECASE)
        for m in _PRONOUN_RE.finditer(masked):
            if _near_quote_mask(masked, m.start(), m.end()):
                continue
            findings.append(Finding(
                rule_id="PRF003",
                severity=Severity.INFO,
                paragraph_index=idx,
                message=(
                    f"First-person pronoun '{m.group()}' detected. "
                    "Note: APA 7 §4.16 endorses first-person pronouns — confirm with your "
                    "program's requirements before changing."
                ),
                suggested_fix="",
                excerpt=_excerpt(masked, m.start(), m.end()),
                location_hint=loc,
                category=cat,
                chapter="§4.16",
            ))


# ===========================================================================
# Abstract length check (MEC016) — document-level
# ===========================================================================

def _check_abstract_length(paragraphs: list[ProseParagraph], findings: list[Finding]) -> None:
    """MEC016: Abstract must not exceed 250 words (§2.9)."""
    in_abstract = False
    abstract_text: list[str] = []
    abstract_idx = 0

    for para in paragraphs:
        text_lower = para.raw_text.lower().strip()
        if text_lower == "abstract":
            in_abstract = True
            abstract_idx = para.index
            continue
        # Stop at next heading or second blank heading
        if in_abstract:
            if para.heading_level is not None and text_lower != "abstract":
                break
            if not para.is_reference_entry:
                abstract_text.append(para.raw_text)

    if abstract_text:
        total_words = sum(len(t.split()) for t in abstract_text)
        if total_words > 250:
            findings.append(Finding(
                rule_id="MEC016",
                severity=Severity.WARNING,
                paragraph_index=abstract_idx,
                message=(
                    f"APA §2.9: The abstract is {total_words} words, which exceeds the 250-word maximum. "
                    "Condense the abstract to 250 words or fewer."
                ),
                suggested_fix="Shorten the abstract to ≤ 250 words.",
                excerpt="(Abstract section)",
                location_hint="Abstract section",
                category=Category.MECHANICS.value,
                chapter="§2.9",
            ))


# ===========================================================================
# Main entry points
# ===========================================================================

def check_paragraphs(
    paragraphs: list[ProseParagraph],
    prose_cfg: dict,
    heading_cfg: dict,
) -> list[Finding]:
    """Run all APA 7 rule checks on an extracted paragraph list."""
    findings: list[Finding] = []

    ref_paragraphs: list[ProseParagraph] = []
    prose_paragraphs: list[ProseParagraph] = []

    for para in paragraphs:
        if para.is_reference_entry:
            ref_paragraphs.append(para)
        else:
            prose_paragraphs.append(para)

    # Document-level checks
    _check_abstract_length(paragraphs, findings)
    _check_hed(paragraphs, heading_cfg, findings)
    _check_ref_entries(ref_paragraphs, prose_cfg, findings)

    # Paragraph-level checks (prose only)
    for para in prose_paragraphs:
        if para.heading_level is not None:
            # Headings: skip prose rules but allow table/citation rules if text warrants
            continue

        _check_mec(para, prose_cfg, findings)
        _check_sty(para, prose_cfg, findings)
        _check_bfl(para, prose_cfg, findings)
        _check_cit(para, prose_cfg, findings)
        _check_tbl(para, prose_cfg, findings)
        _check_prf(para, prose_cfg, findings)

    return findings


def check_document(
    doc_path: str,
    config_path: Optional[str] = None,
) -> list[Finding]:
    """Run all Module-2 rule checks on a .docx file."""
    cfg = _load_config(config_path)
    prose_cfg = cfg.get("prose_rules", {})
    heading_cfg = cfg.get("heading_rules", {})
    doc = Document(doc_path)
    paragraphs = extract_prose(doc)
    return check_paragraphs(paragraphs, prose_cfg, heading_cfg)
