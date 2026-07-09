"""
APA 7 Bias-Free Language Rules — Chapter 5.
All 32 rules surface as SUGGESTION with an explicit recommended replacement.

This module is import-safe: it has no dependency on Finding or Severity.
The caller (module2_apa_checker) iterates BFL_RULES and creates Findings.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class BFLRule(NamedTuple):
    rule_id: str
    pattern: re.Pattern
    message: str
    replacement: str   # recommended replacement text
    chapter: str


# ---------------------------------------------------------------------------
# Age (§5.3)
# ---------------------------------------------------------------------------

BFL_RULES: list[BFLRule] = [

    BFLRule(
        "BFL001",
        re.compile(r'\bseniors\b', re.IGNORECASE),
        "APA §5.3 (Bias-Free Language — Age): 'seniors' is vague. "
        "Prefer 'older adults' or a specific age range (e.g., 'adults 65 years and older').",
        "older adults",
        "§5.3",
    ),

    BFLRule(
        "BFL002",
        re.compile(r'\bthe\s+elderly\b', re.IGNORECASE),
        "APA §5.3: 'the elderly' uses an adjective as a noun and implies homogeneity. "
        "Use 'older adults' or specify the age group.",
        "older adults",
        "§5.3",
    ),

    BFLRule(
        "BFL003",
        re.compile(r'\belderly\s+(?:people|individuals|adults|participants|subjects|men|women|persons|population)\b',
                   re.IGNORECASE),
        "APA §5.3: 'elderly [noun]' is an outdated modifier. "
        "Use 'older adults' or a specific age range.",
        "older adults",
        "§5.3",
    ),

    BFLRule(
        "BFL004",
        re.compile(r'\bthe\s+aged\b', re.IGNORECASE),
        "APA §5.3: 'the aged' uses an adjective as a noun. Use 'older adults'.",
        "older adults",
        "§5.3",
    ),

    BFLRule(
        "BFL005",
        re.compile(r'\baging\s+dependents\b', re.IGNORECASE),
        "APA §5.3: 'aging dependents' is stigmatizing. "
        "Use 'adults who require care' or specify the population.",
        "adults who require care",
        "§5.3",
    ),

    # ---------------------------------------------------------------------------
    # Disability (§5.4)
    # ---------------------------------------------------------------------------

    BFLRule(
        "BFL006",
        re.compile(r'\bwheelchair[- ]bound\b', re.IGNORECASE),
        "APA §5.4 (Disability Language): 'wheelchair-bound' is deficit-framing. "
        "Use 'wheelchair user' or 'uses a wheelchair'.",
        "wheelchair user",
        "§5.4",
    ),

    BFLRule(
        "BFL007",
        re.compile(r'\bconfined\s+to\s+a\s+wheelchair\b', re.IGNORECASE),
        "APA §5.4: 'confined to a wheelchair' is deficit-framing. "
        "Use 'uses a wheelchair'.",
        "uses a wheelchair",
        "§5.4",
    ),

    BFLRule(
        "BFL008",
        re.compile(r'\bAIDS\s+victim\b', re.IGNORECASE),
        "APA §5.4: 'AIDS victim' is pejorative. Use 'person with AIDS'.",
        "person with AIDS",
        "§5.4",
    ),

    BFLRule(
        "BFL009",
        re.compile(r'\bbrain[- ]damaged\b', re.IGNORECASE),
        "APA §5.4: 'brain-damaged' uses a deficit label. "
        "Use 'person with a traumatic brain injury' or the specific diagnosis.",
        "person with a traumatic brain injury",
        "§5.4",
    ),

    BFLRule(
        "BFL010",
        re.compile(r'\bhandicapped\b', re.IGNORECASE),
        "APA §5.4: 'handicapped' is an outdated term. "
        "Use 'person with a disability' or identity-first language if the individual prefers.",
        "person with a disability",
        "§5.4",
    ),

    BFLRule(
        "BFL011",
        re.compile(r'\bthe\s+disabled\b', re.IGNORECASE),
        "APA §5.4: 'the disabled' uses an adjective as a collective noun. "
        "Use 'people with disabilities' or 'disabled people' (person-first or identity-first as appropriate).",
        "people with disabilities",
        "§5.4",
    ),

    BFLRule(
        "BFL012",
        re.compile(r'\bthe\s+blind\b', re.IGNORECASE),
        "APA §5.4: 'the blind' uses an adjective as a collective noun. "
        "Use 'people who are blind' or 'people with visual impairments'.",
        "people who are blind",
        "§5.4",
    ),

    BFLRule(
        "BFL013",
        re.compile(r'\bthe\s+deaf\b', re.IGNORECASE),
        "APA §5.4: 'the deaf' uses an adjective as a collective noun. "
        "Use 'people who are deaf' or 'Deaf community' (capitalized when referring to the cultural group).",
        "people who are deaf",
        "§5.4",
    ),

    BFLRule(
        "BFL014",
        re.compile(r'\bthe\s+mentally\s+ill\b', re.IGNORECASE),
        "APA §5.4: 'the mentally ill' is a collective deficit label. "
        "Use 'people with mental illness' or name the specific condition.",
        "people with mental illness",
        "§5.4",
    ),

    BFLRule(
        "BFL015",
        re.compile(r'\bcripple(?:d|s)?\b', re.IGNORECASE),
        "APA §5.4: 'cripple/crippled' is a slur when applied to people. "
        "Use 'person with a physical disability' or the specific diagnosis.",
        "person with a physical disability",
        "§5.4",
    ),

    BFLRule(
        "BFL016",
        re.compile(r'\bschizophrenic\b(?!\s+disorder)', re.IGNORECASE),
        "APA §5.4: Using a diagnosis as a noun label ('a schizophrenic') is discouraged. "
        "Use 'person with schizophrenia' (person-first language).",
        "person with schizophrenia",
        "§5.4",
    ),

    # ---------------------------------------------------------------------------
    # Gender / Sex (§5.5)
    # ---------------------------------------------------------------------------

    BFLRule(
        "BFL017",
        re.compile(r'\(s\)he\b|s/he\b', re.IGNORECASE),
        "APA §5.5 (Gender Language): '(s)he' and 's/he' are not accepted constructions. "
        "Use singular 'they' as a gender-neutral third-person pronoun.",
        "they",
        "§5.5",
    ),

    BFLRule(
        "BFL018",
        re.compile(r'\bhe\s+or\s+she\b|\bshe\s+or\s+he\b', re.IGNORECASE),
        "APA §5.5: 'he or she' / 'she or he' as generic pronouns is discouraged. "
        "Use singular 'they' instead.",
        "they",
        "§5.5",
    ),

    BFLRule(
        "BFL018A",
        re.compile(r'\b(?:a|an|the|each|every)\s+(?:consultant|participant|practitioner|student|employee|worker|leader|manager|respondent|person|individual)\b[^.!?]{0,120}\bhis\b',
                   re.IGNORECASE),
        "APA §5.5: Generic masculine pronouns such as 'his' are discouraged when referring "
        "to people of unspecified gender. Use singular 'they' or reword the sentence.",
        "their",
        "§5.5",
    ),

    BFLRule(
        "BFL019",
        re.compile(r'\bbirth\s+sex\b|\bnatal\s+sex\b', re.IGNORECASE),
        "APA §5.5: 'birth sex' and 'natal sex' are not preferred. "
        "Use 'sex assigned at birth'.",
        "sex assigned at birth",
        "§5.5",
    ),

    BFLRule(
        "BFL020",
        re.compile(r'\bpreferred\s+pronouns?\b', re.IGNORECASE),
        "APA §5.5: 'preferred pronouns' implies pronouns are optional. "
        "Use 'pronouns' or 'identified pronouns'.",
        "pronouns",
        "§5.5",
    ),

    BFLRule(
        "BFL021",
        re.compile(r'\bpoliceman\b', re.IGNORECASE),
        "APA §5.5: 'policeman' is gender-specific. "
        "Use the gender-neutral 'police officer'.",
        "police officer",
        "§5.5",
    ),

    BFLRule(
        "BFL022",
        re.compile(r'\bfireman\b', re.IGNORECASE),
        "APA §5.5: 'fireman' is gender-specific. Use 'firefighter'.",
        "firefighter",
        "§5.5",
    ),

    BFLRule(
        "BFL023",
        re.compile(r'\bstewardess\b', re.IGNORECASE),
        "APA §5.5: 'stewardess' is gender-specific. Use 'flight attendant'.",
        "flight attendant",
        "§5.5",
    ),

    BFLRule(
        "BFL024",
        re.compile(r'\bmailman\b', re.IGNORECASE),
        "APA §5.5: 'mailman' is gender-specific. Use 'mail carrier'.",
        "mail carrier",
        "§5.5",
    ),

    BFLRule(
        "BFL025",
        re.compile(r'\bmankind\b', re.IGNORECASE),
        "APA §5.5: 'mankind' is gender-specific. Use 'humankind', 'humanity', or 'people'.",
        "humankind",
        "§5.5",
    ),

    BFLRule(
        "BFL026",
        re.compile(r'\bchairman\b', re.IGNORECASE),
        "APA §5.5: 'chairman' is gender-specific. Use 'chair' or 'chairperson'.",
        "chair",
        "§5.5",
    ),

    BFLRule(
        "BFL026A",
        re.compile(r'\bmanpower\b', re.IGNORECASE),
        "APA §5.5: 'manpower' is gendered language. Use a gender-neutral term such as "
        "'workforce', 'staffing', or 'personnel'.",
        "workforce / staffing / personnel",
        "§5.5",
    ),

    # ---------------------------------------------------------------------------
    # Race and Ethnicity (§5.7)
    # ---------------------------------------------------------------------------

    BFLRule(
        "BFL027",
        re.compile(r'\bNegro\b'),
        "APA §5.7 (Racial and Ethnic Identity): 'Negro' is an outdated and offensive term. "
        "Use 'Black' or 'African American'.",
        "Black or African American",
        "§5.7",
    ),

    BFLRule(
        "BFL028",
        re.compile(r'\bAfro[-\s]American\b', re.IGNORECASE),
        "APA §5.7: 'Afro-American' is an outdated term. Use 'African American'.",
        "African American",
        "§5.7",
    ),

    BFLRule(
        "BFL029",
        re.compile(r'\bOriental\b', re.IGNORECASE),
        "APA §5.7: 'Oriental' is an outdated, offensive term when referring to people. "
        "Use 'Asian' or specify the national/ethnic group (e.g., 'Chinese American', 'Korean').",
        "Asian (or specify national/ethnic group)",
        "§5.7",
    ),

    BFLRule(
        "BFL030",
        re.compile(r'\bEskimo\b', re.IGNORECASE),
        "APA §5.7: 'Eskimo' is generally considered offensive. "
        "Use 'Inuit', 'Yupik', or the specific group name.",
        "Inuit or Yupik (specify group)",
        "§5.7",
    ),

    BFLRule(
        "BFL031",
        re.compile(r'\bAsian[-]American\b', re.IGNORECASE),
        "APA §5.7: Do not hyphenate multiword group names used as nouns or adjectives. "
        "Use 'Asian American' (no hyphen).",
        "Asian American",
        "§5.7",
    ),

    BFLRule(
        "BFL032",
        re.compile(r'\bAfrican[-]American\b', re.IGNORECASE),
        "APA §5.7: Do not hyphenate multiword group names. "
        "Use 'African American' (no hyphen).",
        "African American",
        "§5.7",
    ),

    # ---------------------------------------------------------------------------
    # Sexual Orientation (§5.8)
    # ---------------------------------------------------------------------------

    BFLRule(
        "BFL033",
        re.compile(r'\bCaucasian\b'),
        "APA §5.7: 'Caucasian' is discouraged as an alternative to 'White' or 'European' "
        "because of its historical racial classification origins. Use 'White', 'European American', "
        "or specify the national/regional origin.",
        "White or European American (or specify origin)",
        "§5.7",
    ),

    BFLRule(
        "BFL034",
        re.compile(r'\b(?:birth\s+sex|natal\s+sex)\b', re.IGNORECASE),
        "APA §5.5: 'birth sex' and 'natal sex' imply sex is immutable and lack sociocultural context. "
        "Use 'sex assigned at birth' or 'assigned sex' instead.",
        "sex assigned at birth",
        "§5.5",
    ),

    BFLRule(
        "BFL035",
        re.compile(r'\bopposite\s+(?:sex|gender)\b', re.IGNORECASE),
        "APA §5.5: 'opposite sex' or 'opposite gender' implies only two genders and strong differences. "
        "Use 'another sex' or 'another gender' to be more inclusive.",
        "another sex / another gender",
        "§5.5",
    ),

    # ---------------------------------------------------------------------------
    # Sexual Orientation (§5.8)
    # ---------------------------------------------------------------------------

    BFLRule(
        "BFL_SO1",
        re.compile(r'\bsexual\s+preference\b', re.IGNORECASE),
        "APA §5.8 (Sexual Orientation): 'sexual preference' implies choice; use 'sexual orientation'.",
        "sexual orientation",
        "§5.8",
    ),

    BFLRule(
        "BFL_SO2",
        re.compile(r'\bhomosexual(?:s|ity|ism)?\b', re.IGNORECASE),
        "APA §5.8: 'homosexual' is a clinical term that many find offensive. "
        "Use 'gay', 'lesbian', or 'bisexual' as appropriate.",
        "gay, lesbian, or bisexual (as appropriate)",
        "§5.8",
    ),
]
