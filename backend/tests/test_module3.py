"""
Test suite for Module 3 — Citation & Reference Matcher.

Covers bug-fix regressions and core matching behaviour.
Each test class is independent; no shared state between tests.
"""

import unittest

from app.modules.module3_citation_matcher import (
    parse_citations,
    parse_references,
    match_citations_to_references,
    run_citation_check,
    normalise_surname,
    _parse_author_string,
)


# ===========================================================================
# Bug 1 — Possessive with ASCII apostrophe: Kotter's (1996)
# ===========================================================================

class TestPossessiveAsciiApostrophe(unittest.TestCase):
    """parse_citations must strip trailing 's from author names (ASCII apostrophe)."""

    def test_possessive_ascii_apostrophe_stripped(self):
        citations = parse_citations("Kotter's (1996) model.")
        self.assertTrue(citations, "Expected at least one citation to be parsed")
        self.assertEqual(citations[0].authors, ["kotter"])

    def test_year_still_parsed(self):
        citations = parse_citations("Kotter's (1996) model.")
        self.assertEqual(citations[0].year, "1996")


# ===========================================================================
# Bug 2 — Possessive with Unicode right single quotation mark (U+2019)
# ===========================================================================

class TestPossessiveUnicodeApostrophe(unittest.TestCase):
    """parse_citations must normalise U+2019 before matching and strip possessive."""

    def test_possessive_unicode_apostrophe_stripped(self):
        # U+2019 right single quotation mark: Kotter’s
        citations = parse_citations("Kotter’s (1996) model.")
        self.assertTrue(citations, "Expected at least one citation with U+2019 apostrophe")
        self.assertEqual(citations[0].authors, ["kotter"])

    def test_year_still_parsed_unicode(self):
        citations = parse_citations("Kotter’s (1996) model.")
        self.assertEqual(citations[0].year, "1996")


# ===========================================================================
# Bug 3 — Reference year with month: (2024, April)
# ===========================================================================

class TestReferenceYearWithMonth(unittest.TestCase):
    """parse_references must extract '2024' from '(2024, April)'."""

    def test_year_extracted_with_month(self):
        refs = parse_references("Allied Market Research. (2024, April). Title.")
        self.assertTrue(refs, "Expected one reference entry")
        self.assertEqual(refs[0].year, "2024")

    def test_first_author_extracted(self):
        refs = parse_references("Allied Market Research. (2024, April). Title.")
        self.assertEqual(refs[0].first_author, "allied market research")


# ===========================================================================
# Bug 4 — Citation + reference year with month: no phantom year mismatch
# ===========================================================================

class TestYearWithMonthNoMismatch(unittest.TestCase):
    """Year '(2026, March)' in a reference must not produce a year mismatch
    against a citation for the same year."""

    BODY = "Gartner (2026) found that AI adoption is accelerating."
    REF = "Gartner. (2026, March). Title."

    def test_no_year_mismatch(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.year_mismatches, [],
                         f"Unexpected year mismatches: {result.year_mismatches}")

    def test_no_missing_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.missing_references, [],
                         f"Unexpected missing references: {result.missing_references}")


# ===========================================================================
# Bug 5 — Group author abbreviation: Stanford HAI → Stanford Institute ...
# ===========================================================================

class TestGroupAuthorAbbreviationMatch(unittest.TestCase):
    """'Stanford HAI (2026)' must match a reference whose first word is 'Stanford'
    and which is a known group author with the same year."""

    BODY = "Stanford HAI (2026) reported significant findings on AI governance."
    REF = "Stanford Institute for Human-Centered Artificial Intelligence. (2026). Title."

    def test_no_missing_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.missing_references, [],
                         f"Unexpected missing references: {result.missing_references}")

    def test_no_uncited_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.uncited_references, [],
                         f"Unexpected uncited references: {result.uncited_references}")


# ===========================================================================
# Bug 6 — Discourse prefix strip: "Meanwhile Allied Market Research (2024)"
# ===========================================================================

class TestDiscoursePrefixStrip(unittest.TestCase):
    """'Meanwhile' must be stripped so the author is 'allied market research',
    not 'meanwhile allied market research'."""

    BODY = "Meanwhile Allied Market Research (2024) found rapid growth in the sector."
    REF = "Allied Market Research. (2024, April). Title."

    def test_parse_citations_strips_meanwhile(self):
        citations = parse_citations(self.BODY)
        self.assertTrue(citations, "Expected at least one citation")
        self.assertEqual(citations[0].authors, ["allied market research"])

    def test_run_no_missing_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.missing_references, [],
                         f"Unexpected missing references: {result.missing_references}")

    def test_run_no_uncited_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.uncited_references, [],
                         f"Unexpected uncited references: {result.uncited_references}")


# ===========================================================================
# Test 7 — Normal year mismatch still fires
# ===========================================================================

class TestYearMismatchStillFires(unittest.TestCase):
    """A genuine year mismatch (Smith cites 2023, reference has 2021) must
    still appear in year_mismatches."""

    BODY = "Smith (2023) argues that change is non-linear."
    REF = "Smith, J. (2021). Title."

    def test_year_mismatch_detected(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertTrue(result.year_mismatches,
                        "Expected year_mismatches to be non-empty for Smith 2023 vs 2021")

    def test_mismatch_references_correct_years(self):
        result = run_citation_check(self.BODY, self.REF)
        mm = result.year_mismatches[0]
        self.assertIn("2021", mm["reference_years"])
        self.assertEqual(mm["cited_year"], "2023")


# ===========================================================================
# Test 8 — Direct group author match (no abbreviation needed)
# ===========================================================================

class TestDirectGroupAuthorMatch(unittest.TestCase):
    """'Allied Market Research (2024)' cited verbatim must match the reference
    directly without needing the abbreviation path."""

    BODY = "Allied Market Research (2024) found rapid growth in the sector."
    REF = "Allied Market Research. (2024, April). Title."

    def test_no_missing_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.missing_references, [],
                         f"Unexpected missing references: {result.missing_references}")

    def test_no_uncited_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.uncited_references, [],
                         f"Unexpected uncited references: {result.uncited_references}")


class TestPublicationAndOrganizationAuthors(unittest.TestCase):
    """Publication and organisation names can be APA group authors in text."""

    def test_gartner_parenthetical_matches_reference(self):
        result = run_citation_check(
            "The market shifted quickly (Gartner, 2024).",
            "Gartner. (2024). Market guide.",
        )
        self.assertEqual(result.missing_references, [])
        self.assertEqual(result.uncited_references, [])

    def test_pwc_narrative_matches_reference(self):
        result = run_citation_check(
            "PwC (2024) reported new workforce patterns.",
            "PwC. (2024). Workforce report.",
        )
        self.assertEqual(result.missing_references, [])
        self.assertEqual(result.uncited_references, [])

    def test_lowercase_pwc_narrative_matches_reference(self):
        result = run_citation_check(
            "pwc (2024) reported new workforce patterns.",
            "PwC. (2024). Workforce report.",
        )
        self.assertEqual(result.missing_references, [])


# ===========================================================================
# Test 9 — Multi-author parenthetical: (Smith & Jones, 2021)
# ===========================================================================

class TestMultiAuthorParenthetical(unittest.TestCase):
    """Parenthetical citation with two authors must yield both normalised surnames."""

    def test_both_authors_parsed(self):
        citations = parse_citations("(Smith & Jones, 2021)")
        self.assertTrue(citations)
        self.assertIn("smith", citations[0].authors)
        self.assertIn("jones", citations[0].authors)

    def test_year_parsed(self):
        citations = parse_citations("(Smith & Jones, 2021)")
        self.assertEqual(citations[0].year, "2021")

    def test_form_is_parenthetical(self):
        citations = parse_citations("(Smith & Jones, 2021)")
        self.assertEqual(citations[0].form, "parenthetical")


# ===========================================================================
# Test 10 — Et al. citation
# ===========================================================================

class TestEtAlCitation(unittest.TestCase):
    """'Smith et al. (2021)' must parse to first author 'smith' only."""

    def test_et_al_narrative_first_author(self):
        citations = parse_citations("Smith et al. (2021) found that change is complex.")
        self.assertTrue(citations)
        self.assertEqual(citations[0].authors, ["smith"])

    def test_et_al_parenthetical_first_author(self):
        citations = parse_citations("(Smith et al., 2021)")
        self.assertTrue(citations)
        self.assertEqual(citations[0].authors, ["smith"])


# ===========================================================================
# Test 11 — Uncited reference detection
# ===========================================================================

class TestUncitedReferenceDetection(unittest.TestCase):
    """A reference that is never cited in the body must appear in uncited_references."""

    BODY = "Jones (2019) discusses organisational learning."
    REF = "Jones, B. (2019). Title One.\nBrown, C. (2020). Title Two."

    def test_uncited_reference_detected(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertTrue(result.uncited_references,
                        "Expected uncited_references to be non-empty for Brown 2020")

    def test_cited_reference_not_in_uncited(self):
        result = run_citation_check(self.BODY, self.REF)
        uncited_raws = [u["reference"] for u in result.uncited_references]
        self.assertFalse(
            any("Jones" in r for r in uncited_raws),
            f"Jones 2019 should be cited, not uncited. Uncited: {uncited_raws}",
        )


# ===========================================================================
# Test 12 — Microsoft & LinkedIn compound group author
# ===========================================================================

class TestMicrosoftLinkedInGroupAuthor(unittest.TestCase):
    """'Microsoft & LinkedIn (2024)' must match the reference entry exactly."""

    BODY = "Microsoft & LinkedIn (2024) reports that hybrid work is now mainstream."
    REF = "Microsoft & LinkedIn. (2024). Work Trend Index."

    def test_no_missing_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.missing_references, [],
                         f"Unexpected missing references: {result.missing_references}")

    def test_no_uncited_references(self):
        result = run_citation_check(self.BODY, self.REF)
        self.assertEqual(result.uncited_references, [],
                         f"Unexpected uncited references: {result.uncited_references}")


# ===========================================================================
# Retained from original test_module3.py — spelling mismatch (Levenshtein)
# ===========================================================================

class TestSpellingMismatch(unittest.TestCase):
    """
    Spec: "Perng & Hwang (2021)" vs reference "Peng & Hwang (2021)"
          -> spelling-mismatch flag (distance 1, shared year), surfaced not auto-fixed.
    """

    def test_one_character_mismatch_same_year_flagged(self):
        body = "Perng and Hwang (2021) found that collaborative learning improved outcomes."
        refs = "Peng, H., & Hwang, G. (2021). Collaborative learning. Journal X, 5(2), 1-20."

        result = run_citation_check(body, refs, levenshtein_threshold=2)
        self.assertGreaterEqual(len(result.spelling_mismatches), 1,
                                "Expected spelling mismatch for Perng/Peng (distance 1).")
        msg = result.spelling_mismatches[0]["message"]
        self.assertIn("mismatch", msg.lower())

    def test_exact_match_no_spelling_flag(self):
        body = "Peng and Hwang (2021) examined collaborative learning."
        refs = "Peng, H., & Hwang, G. (2021). Collaborative learning. Journal X."

        result = run_citation_check(body, refs)
        self.assertEqual(len(result.spelling_mismatches), 0)


# ===========================================================================
# Retained — substring and co-author false-positive guards
# ===========================================================================

class TestSubstringGuard(unittest.TestCase):
    """
    Spec: "Berger" present only inside "Lichtenberger" -> NOT a reference match.
           "Davis" present only as co-author "Venkatesh & Davis" -> co-author-only soft flag.
    """

    def test_berger_not_matched_as_lichtenberger_substring(self):
        body = "This aligns with Berger (2020)."
        refs = "Lichtenberger, A. (2020). Measurement theory. Publisher."

        result = run_citation_check(body, refs)
        self.assertGreaterEqual(len(result.missing_references), 1,
                                "Berger should be reported as missing, not matched to Lichtenberger.")

    def test_davis_as_coauthor_only_soft_flag(self):
        body = "This is consistent with Davis (1989)."
        refs = "Venkatesh, V., & Davis, F. D. (1989). A model of the antecedents. MIS Q."

        result = run_citation_check(body, refs)
        self.assertGreaterEqual(len(result.co_author_only_matches), 1,
                                "Davis as co-author only should produce a soft co-author flag.")
        hard_missing = [
            m for m in result.missing_references
            if m.get("severity") == "error" and "davis" in m["citation"].lower()
        ]
        self.assertEqual(len(hard_missing), 0,
                         "Davis co-author match should be a soft flag, not a hard error.")


# ===========================================================================
# Retained — compound / multi-word surname parsing
# ===========================================================================

class TestSurnameParsing(unittest.TestCase):
    """
    Spec: "Al Abri, M. H." -> first-author surname parses as "Al Abri", not "al".
    """

    def test_al_abri_parsed_correctly(self):
        ref_text = "Al Abri, M. H. (2011). Managing change. International Journal of Innovation."
        refs = parse_references(ref_text)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].first_author, "al abri",
                         f"Expected 'al abri', got '{refs[0].first_author}'")

    def test_group_author_parsed(self):
        ref_text = "American Psychological Association. (2020). Publication manual (7th ed.)."
        refs = parse_references(ref_text)
        self.assertEqual(len(refs), 1)
        self.assertIn("american psychological association", refs[0].first_author.lower())

    def test_van_surname(self):
        ref_text = "Van den Berg, S. (2018). Organisational resilience. Publisher."
        refs = parse_references(ref_text)
        self.assertEqual(len(refs), 1)
        self.assertTrue(refs[0].first_author.startswith("van"),
                        f"Compound surname 'Van den Berg' — expected 'van...', got '{refs[0].first_author}'")


# ===========================================================================
# Retained — citation parsing forms and normalisation
# ===========================================================================

class TestCitationParsing(unittest.TestCase):
    def test_narrative_citation_parsed(self):
        text = "Smith (2021) argued that organisational change requires leadership."
        cites = parse_citations(text)
        self.assertGreaterEqual(len(cites), 1)
        self.assertEqual(cites[0].form, "narrative")
        self.assertEqual(cites[0].year, "2021")

    def test_parenthetical_citation_parsed(self):
        text = "Organisational change requires leadership (Smith, 2021)."
        cites = parse_citations(text)
        self.assertGreaterEqual(len(cites), 1)
        self.assertEqual(cites[0].form, "parenthetical")
        self.assertEqual(cites[0].year, "2021")

    def test_et_al_parsed(self):
        text = "Prior research (Jones et al., 2019) supports this view."
        cites = parse_citations(text)
        self.assertGreaterEqual(len(cites), 1)
        self.assertEqual(cites[0].year, "2019")

    def test_year_suffix_parsed(self):
        text = "Elliot (2006a) first proposed this framework."
        cites = parse_citations(text)
        self.assertGreaterEqual(len(cites), 1)
        self.assertEqual(cites[0].year, "2006a")

    def test_ampersand_in_narrative(self):
        text = "Venkatesh and Davis (1989) proposed the technology acceptance model."
        cites = parse_citations(text)
        self.assertGreaterEqual(len(cites), 1)
        self.assertIn("venkatesh", [a.lower() for a in cites[0].authors])

    def test_normalise_trailing_comma(self):
        text1 = "Elliot (2006) proposed this."
        c1 = parse_citations(text1)
        self.assertTrue(any("elliot" in str(c.authors).lower() for c in c1))


# ===========================================================================
# Retained — full integration: missing and uncited
# ===========================================================================

class TestMissingAndUncited(unittest.TestCase):
    def test_cited_with_matching_reference(self):
        body = "Leadership is central to change (Smith, 2021)."
        refs = "Smith, J. (2021). Leadership and change. Oxford University Press."
        result = run_citation_check(body, refs)
        self.assertEqual(len(result.missing_references), 0)
        self.assertEqual(len(result.uncited_references), 0)

    def test_citation_not_in_references(self):
        body = "Change is complex (Jones, 2020)."
        refs = "Smith, J. (2021). Leadership and change. Oxford University Press."
        result = run_citation_check(body, refs)
        self.assertGreaterEqual(len(result.missing_references), 1)

    def test_reference_not_cited(self):
        body = "Change is complex (Smith, 2021)."
        refs = (
            "Smith, J. (2021). Leadership and change. Oxford University Press.\n"
            "Jones, K. (2020). Organisational learning. Cambridge Press."
        )
        result = run_citation_check(body, refs)
        self.assertGreaterEqual(len(result.uncited_references), 1)
        self.assertTrue(any("Jones" in u["reference"] for u in result.uncited_references))

    def test_year_mismatch_detected(self):
        body = "Prior research (Smith, 2018) supports this finding."
        refs = "Smith, J. (2021). Leadership and change. Oxford University Press."
        result = run_citation_check(body, refs)
        self.assertGreaterEqual(len(result.year_mismatches), 1)


# ===========================================================================
# Additional parse_references edge cases
# ===========================================================================

class TestParseReferencesEdgeCases(unittest.TestCase):
    """Miscellaneous reference parsing sanity checks."""

    def test_standard_author_year(self):
        refs = parse_references("Smith, J. (2021). Title of work.")
        self.assertTrue(refs)
        self.assertEqual(refs[0].first_author, "smith")
        self.assertEqual(refs[0].year, "2021")

    def test_year_suffix_preserved(self):
        refs = parse_references("Smith, J. (2021a). Title.")
        self.assertTrue(refs)
        self.assertEqual(refs[0].year, "2021a")

    def test_references_heading_skipped(self):
        text = "References\nSmith, J. (2021). Title."
        refs = parse_references(text)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].first_author, "smith")


if __name__ == "__main__":
    unittest.main()
