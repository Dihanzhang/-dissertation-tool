"""
Module 1 — Dissertation Editor (LLM, server-side, metered).

Improves clarity, conciseness, doctoral register, and passive voice.
Preserves citations, author voice, and the Organizational Change & Leadership framing.

Hard guarantees enforced in code (not solely in the prompt):
  - Citation lock: every in-text citation survives character-identical.
  - Body-text only: reference list is never passed here.
  - Low temperature (≤ 0.3).
  - Per-sentence edit-distance: heavy rewrites are classified separately.
  - Everything is returned as a suggestion list — nothing auto-applied.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from rapidfuzz.distance import Levenshtein as _lev

from .citation_lock import verify_citations_preserved
from .provider import LLMProvider, get_provider

# ---------------------------------------------------------------------------
# Config (all tunable via env vars)
# ---------------------------------------------------------------------------

HEAVY_EDIT_THRESHOLD = float(os.getenv("HEAVY_EDIT_THRESHOLD", "0.40"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You are an academic writing editor specialising in doctoral dissertations in Organizational Change, Leadership, and Learning.

Review the provided text for:
1. Passive voice — suggest active voice alternatives where clearer
2. Clarity — remove unnecessary hedging, vague phrases, or redundancy
3. Conciseness — tighten wordy constructions without losing meaning
4. Doctoral register — elevate colloquial or imprecise word choices to scholarly equivalents

Return a JSON array of sentence-level suggestions. Each element has exactly:
- "original": the EXACT sentence copied verbatim from the input text
- "revised": your suggested improvement
- "reason": one short phrase: "passive voice", "clarity", "conciseness", "register", or a compound like "passive voice + clarity"

STRICT RULES — violating these causes your output to be silently discarded:
- NEVER modify, remove, or add any in-text citation. (Author, Year) and Author (Year) are UNTOUCHABLE.
- NEVER restructure paragraphs, merge sentences, or reorder content.
- NEVER change meaning, add content, or remove information.
- Omit sentences that need no change.
- Be conservative: prefer leaving a sentence unchanged over a heavy rewrite.
- Preserve the author's voice, domain vocabulary (sensemaking, adaptive capacity, change readiness, etc.), and the Organisational Change & Leadership framing.

Return ONLY a valid JSON array. No markdown fences, no preamble, no text outside the array.
If there are no suggestions, return: []"""

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class EditSuggestion:
    original: str
    revised: str
    reason: str
    edit_type: str        # "light" | "heavy"
    change_ratio: float   # 0.0 = identical, 1.0 = completely rewritten


@dataclass
class Module1Result:
    suggestions: list[EditSuggestion]
    rejected_by_citation_lock: int
    rejected_sentence_not_found: int
    model_used: str
    input_tokens: int
    output_tokens: int
    word_count: int
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _change_ratio(original: str, revised: str) -> float:
    if original == revised:
        return 0.0
    return 1.0 - _lev.normalized_similarity(original, revised)


def _parse_llm_json(raw: str) -> list[dict]:
    """Parse LLM output as JSON, tolerating markdown fences."""
    clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(clean)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try to extract JSON array from within surrounding text
    m = re.search(r'\[.*\]', clean, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return []


def _normalise_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def run_module1(
    text: str,
    provider: Optional[LLMProvider] = None,
    tier: str = "paid",
) -> Module1Result:
    """
    Run one Module-1 pass on a text chunk (caller must ensure ≤ word cap).
    Returns a Module1Result with suggestions. Never auto-applies anything.
    """
    if provider is None:
        provider = get_provider(tier=tier)

    word_count = len(text.split())

    raw_response, input_tokens, output_tokens = provider.complete(
        system=_SYSTEM,
        user=text,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    raw_items = _parse_llm_json(raw_response)

    suggestions: list[EditSuggestion] = []
    rejected_lock = 0
    rejected_not_found = 0
    norm_text = _normalise_ws(text)

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        original = item.get("original", "").strip()
        revised = item.get("revised", "").strip()
        reason = item.get("reason", "").strip() or "unspecified"

        if not original or not revised or original == revised:
            continue

        # Verify the original sentence actually appears in the input text
        if original not in text and _normalise_ws(original) not in norm_text:
            rejected_not_found += 1
            continue

        # Citation lock: reject if any citation was dropped, altered, or added
        ok, _ = verify_citations_preserved(original, revised)
        if not ok:
            rejected_lock += 1
            continue

        ratio = _change_ratio(original, revised)
        edit_type = "heavy" if ratio > HEAVY_EDIT_THRESHOLD else "light"

        suggestions.append(EditSuggestion(
            original=original,
            revised=revised,
            reason=reason,
            edit_type=edit_type,
            change_ratio=round(ratio, 3),
        ))

    return Module1Result(
        suggestions=suggestions,
        rejected_by_citation_lock=rejected_lock,
        rejected_sentence_not_found=rejected_not_found,
        model_used=provider.model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        word_count=word_count,
    )
