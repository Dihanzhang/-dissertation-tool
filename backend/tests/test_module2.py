"""
Test suite for Module 2 — APA 7 Rule Checker (168-rule rewrite).
Rule IDs follow the new scheme: MEC, BFL, STY, HED, CIT, REF, TBL, PRF.
"""

import pytest
from app.modules.prose_extractor import ProseParagraph, QUOTE_MASK
from app.modules.module2_apa_checker import check_paragraphs, Severity, Finding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_para(
    text: str,
    index: int = 0,
    heading_level=None,
    is_ref: bool = False,
) -> ProseParagraph:
    import re
    masked = re.sub(r'"[^"]*?"|"[^"]*?"', QUOTE_MASK, text)
    return ProseParagraph(
        index=index,
        style_name="Normal",
        raw_text=text,
        masked_text=masked,
        heading_level=heading_level,
        is_reference_entry=is_ref,
    )


DEFAULT_PROSE_CFG = {
    "min_sentences_per_paragraph": 3,
    "numeral_threshold": 10,
    "flag_repeated_narrative_citations": True,
    "flag_first_person_pronouns": False,
}

DEFAULT_HEADING_CFG = {
    "flag_heading_without_body": True,
    "flag_skipped_heading_levels": True,
}


def rule_ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


def has_rule(findings, rule_id: str) -> bool:
    return any(f.rule_id == rule_id for f in findings)


def run(text: str, cfg=None, heading_cfg=None, heading_level=None, is_ref=False):
    paras = [make_para(text, heading_level=heading_level, is_ref=is_ref)]
    return check_paragraphs(paras, cfg or DEFAULT_PROSE_CFG, heading_cfg or DEFAULT_HEADING_CFG)


# ===========================================================================
# MEC001 — Double space after period  §6.1
# ===========================================================================

class TestMEC001:
    def test_double_space_flagged(self):
        findings = run("The study found X.  The results were significant.")
        assert has_rule(findings, "MEC001")

    def test_single_space_not_flagged(self):
        findings = run("The study found X. The results were significant.")
        assert not has_rule(findings, "MEC001")


# ===========================================================================
# MEC002 — Sentence-starting numeral  §6.33
# ===========================================================================

class TestMEC002:
    def test_numeral_at_start_flagged(self):
        findings = run("15 participants completed the survey. The response rate was high.")
        assert has_rule(findings, "MEC002"), "Expected MEC002 for sentence-starting '15'"

    def test_word_at_start_not_flagged(self):
        findings = run("Fifteen participants completed the survey.")
        assert not has_rule(findings, "MEC002")


# ===========================================================================
# MEC003 — Small numeral 1–9 in prose  §6.33
# ===========================================================================

class TestMEC003:
    def test_small_numeral_flagged(self):
        findings = run("The analysis revealed 3 themes in the data.")
        assert has_rule(findings, "MEC003"), "Expected MEC003 for '3 themes'"

    def test_number_with_unit_not_flagged(self):
        findings = run("The study lasted 6 months and included 4 weeks of training.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0, f"MEC003 fired on numbers with units: {[f.excerpt for f in n]}"

    def test_percentage_not_flagged(self):
        findings = run("Approximately 7% of participants reported adverse effects.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0

    def test_n_equals_not_flagged(self):
        findings = run("The sample included N = 8 participants from three organisations.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0

    def test_ratio_not_flagged(self):
        findings = run("Seven out of 15 participants agreed with the statement.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0

    def test_numbered_series_not_flagged(self):
        findings = run("This is discussed in Chapter 3 of the manual and in Step 2 of the process.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0, f"MEC003 fired on numbered series: {[f.excerpt for f in n]}"

    def test_apa_version_not_flagged(self):
        findings = run("This study follows APA 7 guidelines for citation formatting.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0, f"MEC003 fired on 'APA 7': {[f.excerpt for f in n]}"

    def test_decimal_not_flagged(self):
        findings = run("The mean score was 361.5 points.")
        n = [f for f in findings if f.rule_id == "MEC003"]
        assert len(n) == 0, f"MEC003 fired on decimal digit: {[f.excerpt for f in n]}"


# ===========================================================================
# MEC006 — "N percent" → "N%"  §6.44
# ===========================================================================

class TestMEC006:
    def test_n_percent_spelled_flagged(self):
        findings = run("The response rate was 78 percent of the total sample.")
        assert has_rule(findings, "MEC006"), "Expected MEC006 for '78 percent'"

    def test_percent_symbol_not_flagged(self):
        findings = run("The response rate was 78% of the total sample.")
        assert not has_rule(findings, "MEC006")


# ===========================================================================
# MEC007 — p value leading zero  §6.36
# ===========================================================================

class TestMEC007:
    def test_p_zero_flagged(self):
        findings = run("The result was significant (p = 0.031).")
        assert has_rule(findings, "MEC007"), "Expected MEC007 for 'p = 0.031'"

    def test_p_no_zero_not_flagged(self):
        findings = run("The result was significant (p = .031).")
        assert not has_rule(findings, "MEC007")


# ===========================================================================
# MEC009 — p value threshold-only  §6.43
# ===========================================================================

class TestMEC009:
    def test_p_threshold_flagged(self):
        findings = run("The result was significant (p < .05).")
        assert has_rule(findings, "MEC009"), "Expected MEC009 for 'p < .05'"

    def test_p_exact_not_flagged(self):
        findings = run("The result was significant (p = .031).")
        assert not has_rule(findings, "MEC009")


# ===========================================================================
# MEC011 — Apostrophe in number plural  §6.39
# ===========================================================================

class TestMEC011:
    def test_apostrophe_plural_flagged(self):
        findings = run("Popular culture in the 1960's was transformative.")
        assert has_rule(findings, "MEC011"), "Expected MEC011 for \"1960's\""

    def test_no_apostrophe_not_flagged(self):
        findings = run("Popular culture in the 1960s was transformative.")
        assert not has_rule(findings, "MEC011")


# ===========================================================================
# MEC012 — Spaced em dash  §6.7
# ===========================================================================

class TestMEC012:
    def test_spaced_emdash_flagged(self):
        findings = run("The finding — which was unexpected — changed the discussion.")
        assert has_rule(findings, "MEC012"), "Expected MEC012 for spaced em dash"

    def test_no_space_not_flagged(self):
        findings = run("The finding—which was unexpected—changed the discussion.")
        assert not has_rule(findings, "MEC012")


# ===========================================================================
# MEC013 — -ly adverb hyphenation  §6.9
# ===========================================================================

class TestMEC013:
    def test_ly_hyphen_flagged(self):
        findings = run("This was a highly-significant finding in the literature.")
        assert has_rule(findings, "MEC013"), "Expected MEC013 for 'highly-significant'"

    def test_no_ly_hyphen_not_flagged(self):
        findings = run("This was a highly significant finding in the literature.")
        assert not has_rule(findings, "MEC013")


# ===========================================================================
# MEC018 — Series noun uncapitalized  §6.19
# ===========================================================================

class TestMEC018:
    def test_lowercase_table_flagged(self):
        findings = run("Results are shown in table 3 and figure 2.")
        assert has_rule(findings, "MEC018"), "Expected MEC018 for 'table 3'"

    def test_capitalized_not_flagged(self):
        findings = run("Results are shown in Table 3 and Figure 2.")
        assert not has_rule(findings, "MEC018")


# ===========================================================================
# MEC019 — "Page/Paragraph" capitalized before numeral  §6.19
# ===========================================================================

class TestMEC019:
    def test_page_capital_flagged(self):
        findings = run("See the discussion on Page 45 of the manual.")
        assert has_rule(findings, "MEC019"), "Expected MEC019 for 'Page 45'"

    def test_page_lowercase_not_flagged(self):
        findings = run("See the discussion on page 45 of the manual.")
        assert not has_rule(findings, "MEC019")


# ===========================================================================
# STY008 — Third-person self-reference  §4.16
# ===========================================================================

class TestSTY008:
    def test_the_researcher_flagged(self):
        findings = run("The researcher conducted semi-structured interviews with eight participants.")
        assert has_rule(findings, "STY008"), "Expected STY008 for 'the researcher'"

    def test_the_present_author_flagged(self):
        findings = run("The present author identified three overarching themes.")
        assert has_rule(findings, "STY008")

    def test_legitimate_reference_not_flagged(self):
        findings = run("Smith (2020) argues that leadership is contextual.")
        assert not has_rule(findings, "STY008")


# ===========================================================================
# STY009 — Contractions  §4.7
# ===========================================================================

class TestSTY009:
    @pytest.mark.parametrize("text", [
        "This doesn't address the root cause of resistance.",
        "We can't assume that all participants understood the instructions.",
        "It's important to consider the limitations of this study.",
        "The data weren't collected using a random sample.",
    ])
    def test_contraction_in_prose_flagged(self, text):
        findings = run(text)
        assert has_rule(findings, "STY009"), f"Expected STY009 for: {text!r}"

    def test_contraction_inside_quote_not_flagged(self):
        text = 'The participant stated, "I don\'t think I was heard."'
        findings = run(text)
        con = [f for f in findings if f.rule_id == "STY009"]
        assert len(con) == 0, f"STY009 fired on quoted contraction: {[f.excerpt for f in con]}"

    def test_possessive_not_flagged(self):
        findings = run("Smith's (2021) framework addresses three dimensions of change.")
        assert not has_rule(findings, "STY009")


# ===========================================================================
# STY010 — Bare demonstrative as subject  §4.11
# ===========================================================================

class TestSTY010:
    @pytest.mark.parametrize("text", [
        "This study examined the relationship between leadership and trust.",
        "This approach allows for nuanced interpretation of the data.",
        "This section outlines the theoretical framework.",
        "This research contributes to the field of organisational change.",
        "This framework provides a useful lens for analysis.",
        "This analysis reveals three emergent themes.",
        "This chapter reviews relevant literature on change management.",
    ])
    def test_noun_after_demonstrative_not_flagged(self, text):
        findings = run(text)
        assert not has_rule(findings, "STY010"), f"Falsely flagged as STY010: {text!r}"

    @pytest.mark.parametrize("text", [
        "This shows that the intervention was effective.",
        "This is consistent with prior research on organisational learning.",
        "These are the main findings of the study.",
        "That suggests a need for further investigation.",
    ])
    def test_bare_demonstrative_flagged(self, text):
        findings = run(text)
        assert has_rule(findings, "STY010"), f"Expected STY010 but not found: {text!r}"


# ===========================================================================
# STY011 — Latin abbreviations in running text  §6.29
# ===========================================================================

class TestSTY011:
    def test_eg_in_running_text_flagged(self):
        findings = run("Several factors were identified, e.g., leadership style and communication.")
        assert has_rule(findings, "STY011"), "Expected STY011 for 'e.g.' in running text"

    def test_ie_in_running_text_flagged(self):
        findings = run("The interviews were semi-structured, i.e., guided by an interview protocol.")
        assert has_rule(findings, "STY011")

    def test_eg_in_parentheses_not_flagged(self):
        findings = run("Participants reported various challenges (e.g., time constraints, workload).")
        lat = [f for f in findings if f.rule_id == "STY011"]
        assert len(lat) == 0, f"STY011 fired inside parentheses: {[f.excerpt for f in lat]}"

    def test_ie_in_parentheses_not_flagged(self):
        findings = run("All interviews were recorded (i.e., audio-recorded with consent).")
        assert not has_rule(findings, "STY011")


# ===========================================================================
# STY012 — ibid.  §8.16
# ===========================================================================

class TestSTY012:
    def test_ibid_flagged(self):
        findings = run("Change is disruptive (Smith, 2021). Ibid. notes that resistance is common.")
        assert has_rule(findings, "STY012"), "Expected STY012 for 'Ibid.'"

    def test_ibid_lowercase_flagged(self):
        findings = run("Leadership is central (Jones, 2019; ibid.).")
        assert has_rule(findings, "STY012")


# ===========================================================================
# STY013 — Hedging "would"  §4.14
# ===========================================================================

class TestSTY013:
    def test_it_would_appear_flagged(self):
        findings = run("It would appear that organisational change requires strong leadership.")
        assert has_rule(findings, "STY013"), "Expected STY013 for 'it would appear'"

    def test_it_would_seem_flagged(self):
        findings = run("It would seem that the intervention had limited impact on staff morale.")
        assert has_rule(findings, "STY013")

    def test_indicative_not_flagged(self):
        findings = run("It appears that organisational change requires strong leadership.")
        assert not has_rule(findings, "STY013")


# ===========================================================================
# STY015 — Anthropomorphism  §4.11
# ===========================================================================

class TestSTY015:
    def test_verb_inside_quote_not_flagged(self):
        text = 'The participant noted, "we found the process overwhelming."'
        findings = run(text)
        ev = [f for f in findings if f.rule_id == "STY015"]
        assert len(ev) == 0, f"STY015 fired on quoted text: {[f.excerpt for f in ev]}"

    def test_nonhuman_subject_found_not_flagged(self):
        # APA §4.11 explicitly permits "the study found" — not anthropomorphism
        findings = run("The study found significant differences between groups.")
        ev = [f for f in findings if f.rule_id == "STY015"]
        assert len(ev) == 0, f"STY015 should not fire on 'the study found' (APA §4.11): {[f.excerpt for f in ev]}"

    def test_first_person_found_not_flagged(self):
        findings = run(
            "I found that leadership behaviours shifted significantly after the intervention."
        )
        ev = [f for f in findings if f.rule_id == "STY015"]
        assert len(ev) == 0, f"STY015 should not fire on 'I found': {[f.excerpt for f in ev]}"

    def test_reference_entry_not_flagged(self):
        findings = run("Smith, J. (2021). Explored perspectives on change. Journal X.", is_ref=True)
        assert not has_rule(findings, "STY015")

    def test_the_study_concludes_flagged(self):
        findings = run("The study concludes that leadership is central to change.")
        assert has_rule(findings, "STY015")


# ===========================================================================
# HED001 — Skipped heading levels  §2.27
# ===========================================================================

class TestHED001:
    def test_skipped_heading_level_flagged(self):
        paras = [
            make_para("Introduction", heading_level=1, index=0),
            make_para("Some text here.", index=1),
            make_para("Subsection Detail", heading_level=3, index=2),
        ]
        findings = check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)
        assert has_rule(findings, "HED001"), "Expected HED001 for skipped heading level"

    def test_sequential_headings_not_flagged(self):
        paras = [
            make_para("Introduction", heading_level=1, index=0),
            make_para("Some text here.", index=1),
            make_para("Background", heading_level=2, index=2),
        ]
        findings = check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)
        assert not has_rule(findings, "HED001")


# ===========================================================================
# HED002 — Heading without body text  §2.27
# ===========================================================================

class TestHED002:
    def test_heading_followed_by_heading_same_level_flagged(self):
        # Two Level-2 headings with no body text between them → genuine HED002.
        paras = [
            make_para("Background", heading_level=2, index=0),
            make_para("Literature Review", heading_level=2, index=1),
        ]
        findings = check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)
        assert has_rule(findings, "HED002")

    def test_level1_followed_by_level2_not_flagged(self):
        # Level 1 immediately followed by Level 2 is valid APA subheading structure.
        paras = [
            make_para("Introduction", heading_level=1, index=0),
            make_para("The Problem", heading_level=2, index=1),
        ]
        findings = check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)
        assert not has_rule(findings, "HED002")

    def test_heading_with_body_not_flagged(self):
        paras = [
            make_para("Chapter 1", heading_level=1, index=0),
            make_para(
                "This chapter introduces the study. It provides context. The structure follows.",
                index=1
            ),
            make_para("Introduction", heading_level=2, index=2),
        ]
        findings = check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)
        assert not has_rule(findings, "HED002")


# ===========================================================================
# CIT001 — "and" in parenthetical citation  §8.13
# ===========================================================================

class TestCIT001:
    def test_and_in_paren_flagged(self):
        findings = run("Change is complex (Smith and Jones, 2021).")
        assert has_rule(findings, "CIT001"), "Expected CIT001 for 'and' in parenthetical"

    def test_amp_in_paren_not_flagged(self):
        findings = run("Change is complex (Smith & Jones, 2021).")
        assert not has_rule(findings, "CIT001")


# ===========================================================================
# CIT002 — "&" in narrative citation  §8.13
# ===========================================================================

class TestCIT002:
    def test_amp_in_narrative_flagged(self):
        findings = run("Smith & Jones (2021) argued that change is complex.")
        assert has_rule(findings, "CIT002"), "Expected CIT002 for '&' in narrative"

    def test_and_in_narrative_not_flagged(self):
        findings = run("Smith and Jones (2021) argued that change is complex.")
        assert not has_rule(findings, "CIT002")


# ===========================================================================
# CIT003 — Three+ authors not using et al.  §8.17
# ===========================================================================

class TestCIT003:
    def test_three_authors_expanded_flagged(self):
        findings = run("Leadership is complex (Smith, Jones, & Brown, 2021).")
        assert has_rule(findings, "CIT003"), "Expected CIT003 for three expanded authors"

    def test_et_al_not_flagged(self):
        findings = run("Leadership is complex (Smith et al., 2021).")
        assert not has_rule(findings, "CIT003")


# ===========================================================================
# CIT004 — Multiple citations not alphabetical  §8.19
# ===========================================================================

class TestCIT004:
    def test_out_of_order_flagged(self):
        findings = run("Change is complex (Smith, 2021; Adams, 2019).")
        assert has_rule(findings, "CIT004"), "Expected CIT004 for out-of-order citations"

    def test_alphabetical_not_flagged(self):
        findings = run("Change is complex (Adams, 2019; Smith, 2021).")
        assert not has_rule(findings, "CIT004")


# ===========================================================================
# CIT005 — Wrong et al. format  §8.18
# ===========================================================================

class TestCIT005:
    def test_et_al_no_period_flagged(self):
        findings = run("This is consistent with Smith et al (2021).")
        assert has_rule(findings, "CIT005"), "Expected CIT005 for 'et al' without period"

    def test_etal_no_space_flagged(self):
        findings = run("Smith etal. (2021) showed that leadership matters.")
        assert has_rule(findings, "CIT005")

    def test_correct_et_al_not_flagged(self):
        findings = run("Smith et al. (2021) showed that leadership matters.")
        assert not has_rule(findings, "CIT005")


# ===========================================================================
# CIT011 — Repeated narrative citation  §8.16
# ===========================================================================

class TestCIT011:
    def test_same_source_twice_flagged(self):
        text = (
            "Smith (2021) argued that change requires leadership. "
            "Furthermore, Smith (2021) noted that resistance is common. "
            "This is consistent with prior research."
        )
        findings = run(text)
        assert has_rule(findings, "CIT011"), "Expected CIT011 for repeated narrative citation"

    def test_parenthetical_not_flagged(self):
        text = (
            "Leadership is central to change (Smith, 2021; Jones, 2019). "
            "Resistance is common (Smith, 2021). Both factors matter (Jones, 2019)."
        )
        findings = run(text)
        c = [f for f in findings if f.rule_id == "CIT011"]
        assert len(c) == 0, f"CIT011 incorrectly fired on parenthetical citations: {c}"


# ===========================================================================
# PRF001 — Paragraph too short  §4.6
# ===========================================================================

class TestPRF001:
    def test_short_paragraph_flagged(self):
        findings = run("This section presents the findings.")
        assert has_rule(findings, "PRF001"), "Expected PRF001 for 1-sentence paragraph"

    def test_adequate_paragraph_not_flagged(self):
        text = (
            "This section presents the findings. "
            "Three major themes emerged from the data. "
            "These are discussed in detail below."
        )
        findings = run(text)
        assert not has_rule(findings, "PRF001")


# ===========================================================================
# PRF003 — First-person pronouns  §4.16 (off by default)
# ===========================================================================

class TestPRF003:
    def test_first_person_not_flagged_by_default(self):
        findings = run("In our study, we examined the role of communication in change.")
        pr = [f for f in findings if f.rule_id == "PRF003"]
        assert len(pr) == 0, "PRF003 should not fire by default — APA endorses first person"

    def test_first_person_flagged_when_enabled(self):
        cfg = {**DEFAULT_PROSE_CFG, "flag_first_person_pronouns": True}
        findings = run("In our study, we examined the role of communication in change.", cfg=cfg)
        pr = [f for f in findings if f.rule_id == "PRF003"]
        assert len(pr) >= 1, "Expected PRF003 when flag_first_person_pronouns=True"

    def test_pronouns_inside_quotes_not_flagged(self):
        cfg = {**DEFAULT_PROSE_CFG, "flag_first_person_pronouns": True}
        text = 'Participants described: "we found the process overwhelming."'
        findings = run(text, cfg=cfg)
        pr = [f for f in findings if f.rule_id == "PRF003"]
        assert len(pr) == 0, f"PRF003 fired on quoted pronouns: {[f.excerpt for f in pr]}"


# ===========================================================================
# BFL rules — sample tests for Bias-Free Language  §5
# ===========================================================================

class TestBFL:
    def test_bfl001_seniors_flagged(self):
        findings = run("The sample consisted of seniors aged 65 and above.")
        assert has_rule(findings, "BFL001"), "Expected BFL001 for 'seniors'"

    def test_bfl001_severity_is_suggestion(self):
        findings = run("The sample consisted of seniors aged 65 and above.")
        bfl = [f for f in findings if f.rule_id == "BFL001"]
        assert all(f.severity == Severity.SUGGESTION for f in bfl)

    def test_bfl006_wheelchair_bound_flagged(self):
        findings = run("Three participants were wheelchair-bound.")
        assert has_rule(findings, "BFL006"), "Expected BFL006 for 'wheelchair-bound'"

    def test_bfl017_she_flagged(self):
        findings = run("Each participant was asked about (s)he preferences.")
        assert has_rule(findings, "BFL017"), "Expected BFL017 for '(s)he'"

    def test_bfl018_he_or_she_flagged(self):
        findings = run("The researcher asked he or she to complete the survey.")
        assert has_rule(findings, "BFL018"), "Expected BFL018 for 'he or she'"

    def test_bfl031_hyphenated_asian_american_flagged(self):
        findings = run("Asian-American participants reported higher levels of engagement.")
        assert has_rule(findings, "BFL031"), "Expected BFL031 for 'Asian-American'"

    def test_bfl_in_quotes_not_flagged(self):
        findings = run('The article described "the elderly" as a homogeneous group.')
        bfl = [f for f in findings if f.rule_id.startswith("BFL")]
        assert len(bfl) == 0, f"BFL fired inside quoted text: {[f.rule_id for f in bfl]}"


# ===========================================================================
# REF rules — reference list  §9
# ===========================================================================

class TestREF:
    def _ref_para(self, text: str, index: int = 0) -> ProseParagraph:
        return make_para(text, index=index, is_ref=True)

    def _run_ref(self, entries: list[str]) -> list[Finding]:
        paras = [self._ref_para(t, i) for i, t in enumerate(entries)]
        return check_paragraphs(paras, DEFAULT_PROSE_CFG, DEFAULT_HEADING_CFG)

    def test_ref001_old_doi_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Leadership. Journal, 5(1), 1–10. http://dx.doi.org/10.1111/abc"
        ])
        assert has_rule(findings, "REF001"), "Expected REF001 for old DOI format"

    def test_ref003_retrieved_from_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Leadership. Retrieved from https://example.com/article"
        ])
        assert has_rule(findings, "REF003"), "Expected REF003 for 'Retrieved from'"

    def test_ref005_period_after_url_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Leadership. https://example.com/article."
        ])
        assert has_rule(findings, "REF005"), "Expected REF005 for period after URL"

    def test_ref006_wrong_nd_format_flagged(self):
        findings = self._run_ref([
            "Smith, J. (no date). Leadership. Journal."
        ])
        assert has_rule(findings, "REF006"), "Expected REF006 for '(no date)'"

    def test_ref007_and_between_authors_flagged(self):
        findings = self._run_ref([
            "Smith, J. A. and Jones, B. C. (2020). Leadership. Journal, 5(1), 1–10."
        ])
        assert has_rule(findings, "REF007"), "Expected REF007 for 'and' between authors"

    def test_ref013_space_before_issue_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Title. Journal Name, 5 (2), 1–10."
        ])
        assert has_rule(findings, "REF013"), "Expected REF013 for space before issue number"

    def test_ref018_out_of_order_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Leadership. Journal.",
            "Adams, B. (2019). Change. Journal.",
        ])
        assert has_rule(findings, "REF018"), "Expected REF018 for out-of-order references"

    def test_ref_correct_doi_not_flagged(self):
        findings = self._run_ref([
            "Smith, J. (2020). Leadership. Journal, 5(1), 1–10. https://doi.org/10.1111/abc123"
        ])
        assert not has_rule(findings, "REF001")
        assert not has_rule(findings, "REF005")


# ===========================================================================
# TBL rules — table references in prose  §7
# ===========================================================================

class TestTBL:
    def test_tbl001_positional_reference_flagged(self):
        findings = run("The results are summarized in the table below.")
        assert has_rule(findings, "TBL001"), "Expected TBL001 for 'table below'"

    def test_tbl001_numbered_reference_not_flagged(self):
        findings = run("The results are summarized in Table 3.")
        assert not has_rule(findings, "TBL001")

    def test_tbl002_roman_numeral_flagged(self):
        findings = run("Results are presented in Table III.")
        assert has_rule(findings, "TBL002"), "Expected TBL002 for Roman numeral table number"

    def test_tbl002_arabic_numeral_not_flagged(self):
        findings = run("Results are presented in Table 3.")
        assert not has_rule(findings, "TBL002")


# ===========================================================================
# Finding data model
# ===========================================================================

class TestFindingModel:
    def test_finding_has_category_field(self):
        findings = run("The analysis revealed 3 themes in the data.")
        mec = [f for f in findings if f.rule_id == "MEC003"]
        assert len(mec) > 0
        assert mec[0].category == "mechanics"

    def test_finding_has_chapter_field(self):
        findings = run("The analysis revealed 3 themes in the data.")
        mec = [f for f in findings if f.rule_id == "MEC003"]
        assert mec[0].chapter == "§6.33"

    def test_bfl_finding_severity_is_suggestion(self):
        findings = run("The study included elderly participants.")
        bfl = [f for f in findings if f.rule_id.startswith("BFL")]
        assert len(bfl) > 0
        assert all(f.severity == Severity.SUGGESTION for f in bfl)

    def test_reference_entries_not_prose_checked(self):
        text = "The researcher conducted semi-structured interviews."
        findings = run(text, is_ref=True)
        # STY008 applies to prose, not reference entries
        assert not has_rule(findings, "STY008")
