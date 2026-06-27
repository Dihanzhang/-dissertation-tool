"""
Tests for Module 1 — citation lock, text splitter, edit classification, mocked LLM.
"""

from __future__ import annotations

import pytest
import math

from app.modules.citation_lock import extract_citation_spans, verify_citations_preserved
from app.modules.text_splitter import count_words, split_into_chunks, estimate_chunks
from app.modules.module1_editor import run_module1, _change_ratio, HEAVY_EDIT_THRESHOLD


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

class MockProvider:
    """Returns a fixed JSON payload as if from the LLM."""

    def __init__(self, suggestions: list[dict] | str):
        import json
        self._response = suggestions if isinstance(suggestions, str) else json.dumps(suggestions)
        self._model = "mock-model"

    @property
    def model_id(self) -> str:
        return self._model

    def complete(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 4096):
        return self._response, 100, 50


# ---------------------------------------------------------------------------
# Citation lock tests
# ---------------------------------------------------------------------------

class TestCitationLock:
    def test_citations_preserved(self):
        original = "Smith (2021) argued that change requires leadership."
        revised = "Smith (2021) contended that change demands leadership."
        ok, problems = verify_citations_preserved(original, revised)
        assert ok, problems

    def test_citation_dropped_rejected(self):
        original = "Leadership is central (Smith, 2021)."
        revised = "Leadership is central."
        ok, problems = verify_citations_preserved(original, revised)
        assert not ok
        assert any("dropped" in p for p in problems)

    def test_citation_added_rejected(self):
        original = "Leadership is central to change."
        revised = "Leadership is central to change (Jones, 2020)."
        ok, problems = verify_citations_preserved(original, revised)
        assert not ok
        assert any("added" in p for p in problems)

    def test_citation_altered_rejected(self):
        original = "Change is complex (Smith, 2021)."
        revised = "Change is complex (Smith, 2022)."  # year changed
        ok, problems = verify_citations_preserved(original, revised)
        assert not ok

    def test_no_citations_passes(self):
        original = "Change is a complex and multifaceted process."
        revised = "Change is a complex, multifaceted process."
        ok, problems = verify_citations_preserved(original, revised)
        assert ok, problems

    def test_multiple_citations_all_preserved(self):
        original = "Smith (2021) and Jones (2019) both argue that leadership matters (Brown, 2020)."
        revised = "Smith (2021) and Jones (2019) both contend that leadership is significant (Brown, 2020)."
        ok, problems = verify_citations_preserved(original, revised)
        assert ok, problems


# ---------------------------------------------------------------------------
# Text splitter tests
# ---------------------------------------------------------------------------

class TestTextSplitter:
    def test_short_text_single_chunk(self):
        text = "This is a short paragraph. It has only a few words."
        chunks = split_into_chunks(text, word_cap=100)
        assert chunks == [text]

    def test_splits_at_paragraph_boundary(self):
        para1 = " ".join(["word"] * 60)
        para2 = " ".join(["word"] * 60)
        text = para1 + "\n\n" + para2
        chunks = split_into_chunks(text, word_cap=70)
        assert len(chunks) == 2
        assert all(count_words(c) <= 70 for c in chunks)

    def test_never_splits_inside_citation(self):
        # Narrative citation: Smith (2021) — split must not cut between "Smith" and "(2021)"
        before = " ".join(["word"] * 50)
        after = "This is discussed by Smith (2021) in detail. Further analysis shows the pattern."
        text = before + " " + after
        chunks = split_into_chunks(text, word_cap=55)
        # Citation must appear whole in exactly one chunk
        full = "\n\n".join(chunks)
        assert "Smith (2021)" in full
        for chunk in chunks:
            # If "Smith" appears, "(2021)" must be in the same chunk
            if "Smith (" in chunk:
                assert "2021)" in chunk, f"Citation split across chunks: '{chunk}'"

    def test_estimate_chunks(self):
        text = " ".join(["word"] * 12500)
        n = estimate_chunks(text, word_cap=5000)
        assert n == 3   # ceil(12500/5000) = 3

    def test_empty_paragraphs_skipped(self):
        text = "First paragraph text.\n\n\n\nSecond paragraph text."
        chunks = split_into_chunks(text, word_cap=100)
        assert len(chunks) == 1  # fits in one chunk


# ---------------------------------------------------------------------------
# Edit-distance classification
# ---------------------------------------------------------------------------

class TestEditClassification:
    def test_identical_sentences_zero_ratio(self):
        s = "The data were analysed using thematic analysis."
        assert _change_ratio(s, s) == 0.0

    def test_light_edit_small_ratio(self):
        original = "The data was analyzed using thematic analysis."
        revised = "The data were analysed using thematic analysis."
        ratio = _change_ratio(original, revised)
        assert ratio < HEAVY_EDIT_THRESHOLD

    def test_heavy_rewrite_large_ratio(self):
        original = "This was done."
        revised = "The researchers employed a systematic approach to accomplish this task."
        ratio = _change_ratio(original, revised)
        assert ratio > HEAVY_EDIT_THRESHOLD


# ---------------------------------------------------------------------------
# Module 1 with mocked provider
# ---------------------------------------------------------------------------

class TestModule1WithMock:
    def test_returns_suggestions(self):
        suggestions = [
            {
                "original": "The data was analyzed using thematic analysis.",
                "revised": "The data were analysed using thematic analysis.",
                "reason": "register",
            }
        ]
        text = "The data was analyzed using thematic analysis. This approach was chosen deliberately."
        result = run_module1(text, provider=MockProvider(suggestions))
        assert len(result.suggestions) == 1
        assert result.suggestions[0].edit_type == "light"

    def test_citation_lock_rejects_dropped_citation(self):
        suggestions = [
            {
                "original": "Leadership is central to change (Smith, 2021).",
                "revised": "Leadership is central to change.",  # citation dropped
                "reason": "conciseness",
            }
        ]
        text = "Leadership is central to change (Smith, 2021). This is well established."
        result = run_module1(text, provider=MockProvider(suggestions))
        assert len(result.suggestions) == 0
        assert result.rejected_by_citation_lock == 1

    def test_sentence_not_in_text_rejected(self):
        suggestions = [
            {
                "original": "A sentence that does not appear in the input text.",
                "revised": "A sentence that was invented by the LLM.",
                "reason": "clarity",
            }
        ]
        text = "The study examined leadership. Change is complex."
        result = run_module1(text, provider=MockProvider(suggestions))
        assert len(result.suggestions) == 0
        assert result.rejected_sentence_not_found == 1

    def test_heavy_edit_classified_correctly(self):
        suggestions = [
            {
                "original": "It was done.",
                "revised": "The research team systematically implemented the intervention across all four sites.",
                "reason": "clarity",
            }
        ]
        text = "It was done. Results confirmed the hypothesis."
        result = run_module1(text, provider=MockProvider(suggestions))
        assert len(result.suggestions) == 1
        assert result.suggestions[0].edit_type == "heavy"

    def test_invalid_llm_json_returns_empty(self):
        text = "The study examined leadership. Change is complex."
        result = run_module1(text, provider=MockProvider("not valid json at all"))
        assert len(result.suggestions) == 0
        assert result.error is None  # no crash

    def test_empty_suggestions_array(self):
        text = "The study examined leadership. Change is complex."
        result = run_module1(text, provider=MockProvider([]))
        assert len(result.suggestions) == 0

    def test_model_id_recorded(self):
        text = "Leadership is complex. Change requires effort."
        result = run_module1(text, provider=MockProvider([]))
        assert result.model_used == "mock-model"

    def test_citation_preserved_through_edit(self):
        suggestions = [
            {
                "original": "The passive voice was used in this section by the researcher (Smith, 2021).",
                "revised": "The researcher used the passive voice in this section (Smith, 2021).",
                "reason": "passive voice",
            }
        ]
        text = "The passive voice was used in this section by the researcher (Smith, 2021)."
        result = run_module1(text, provider=MockProvider(suggestions))
        assert len(result.suggestions) == 1
        assert result.rejected_by_citation_lock == 0
