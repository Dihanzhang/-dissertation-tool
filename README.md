# Dissertation APA 7 Review Assistant

A deterministic APA 7 rule-checking and AI-assisted writing polish tool built for doctoral dissertation review. Designed for EdD/PhD students at USC and similar institutions. The APA checker is free and runs locally; AI polish is metered via credits.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Running the Application](#3-running-the-application)
4. [Frontend UX](#4-frontend-ux)
5. [Backend — Module Breakdown](#5-backend--module-breakdown)
6. [APA 7 Rules Implemented](#6-apa-7-rules-implemented)
7. [Paragraph Classification System](#7-paragraph-classification-system)
8. [Citation & Reference Matching](#8-citation--reference-matching)
9. [Configuration](#9-configuration)
10. [Test Suite](#10-test-suite)
11. [Known Issues & Pending Fixes](#11-known-issues--pending-fixes)
12. [Development Log](#12-development-log)

---

## 1. Project Overview

### Purpose

This tool checks dissertation drafts for APA 7 compliance and optionally polishes prose for doctoral register. It does not store text, does not train on submissions, and is designed to stay within academic-integrity boundaries: the AI module only suggests changes — the user approves every edit.

### Core Capabilities

| Capability | Module | Cost |
|---|---|---|
| APA 7 rule checking (168 rules, 8 categories) | Module 2 | Free |
| Citation ↔ reference cross-matching | Module 3 | Free |
| AI-assisted clarity/register polish | Module 1 | 1 credit per 5,000 words |

### Intended Users

- EdD/PhD students writing dissertations under APA 7
- Specifically tuned for USC Organizational Change and Leadership program requirements
- Configurable for any institution's additional professor/program rules

---

## 2. Architecture

```
dissertation-tool/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py             # API endpoints
│   │   ├── config/
│   │   │   └── prof_checklist.yaml   # Tunable rule thresholds
│   │   └── modules/
│   │       ├── prose_extractor.py    # .docx parser → ProseParagraph list
│   │       ├── module1_editor.py     # LLM clarity/register polish
│   │       ├── module2_apa_checker.py # Deterministic APA 7 rule engine
│   │       ├── module3_citation_matcher.py  # Citation↔reference cross-check
│   │       ├── apa_ref_rules.py      # REF001–REF023 reference list rules
│   │       ├── apa_bfl_rules.py      # BFL001–BFL034 bias-free language rules
│   │       ├── credits.py            # Credit balance store
│   │       ├── provider.py           # LLM provider abstraction
│   │       ├── text_splitter.py      # Chunk text at paragraph boundaries
│   │       └── citation_lock.py      # Prevent LLM from altering citations
│   └── tests/
│       ├── test_module1.py     # Citation lock, text splitter, LLM mock tests
│       ├── test_module2.py     # APA rule engine unit tests
│       └── test_module3.py     # Citation matching unit tests
└── frontend/                   # Next.js frontend
    └── app/
        ├── page.tsx            # Landing page
        └── review/
            └── page.tsx        # Main review UI
```

### Ports

| Service | Port | Notes |
|---|---|---|
| FastAPI backend | 8001 | Primary; module 2+3 (free) and module 1 (LLM) |
| Next.js frontend | 3001 | Review UI |
| Legacy backend | 8000 | Earlier build step; still running in parallel |

---

## 3. Running the Application

### Backend

```powershell
# From dissertation-tool\backend\
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Important — cache clearing on restart:**
Python bytecode caches (`.pyc` files in `__pycache__`) can serve stale code after edits. When rules are not taking effect after a server restart, clear caches before starting:

```powershell
Remove-Item -Recurse -Force "app\modules\__pycache__" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "app\__pycache__" -ErrorAction SilentlyContinue
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Killing a zombie port:** On Windows, the child multiprocessing spawn process can hold a port even after the parent is killed:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen |
  Select-Object -ExpandProperty OwningProcess |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

### Frontend

```powershell
# From dissertation-tool\frontend\
npm run dev -- -p 3001
```

### Environment Variables

Stored in `backend/.env` (not committed). Copy from `backend/.env.example`:

```env
ANTHROPIC_API_KEY=sk-...          # Required for Module 1 (AI polish)
WORD_CAP_PER_CREDIT=5000          # Words per credit (default 5000)
FREE_TRIAL_WORD_CAP=3000          # Free tier cap
TEST_MODE=false                    # true = bypass credit check in dev
```

### API Health Check

```
GET http://localhost:8001/api/health
→ {"status":"ok","build_step":2,"test_mode":false}
```

---

## 4. Frontend UX

**URL:** `http://localhost:3001`

### Landing Page (`/`)

- Hero section with "Try one section free" CTA
- Feature list of what is checked for free
- Pricing section: $14.99 for 10 AI reviews at 5,000 words each
- Data handling notice: text deleted after processing, not used for training

### Review Page (`/review`)

Two input modes:

**Paste text mode:**
- Single textarea for body + references together
- Auto-splits on a `References` heading line
- Live word count displayed
- On submit: calls `POST /api/check/text`

**Upload .docx mode:**
- Drag-and-drop or click-to-browse file picker
- Accepts `.docx` only
- On submit: calls `POST /api/check/docx` as multipart form
- Heading styles, block quotes, and table cells are handled server-side

### Results Display

**Stats bar:** paragraphs checked · APA findings · citations · references · citation issues

**Two tabs:**

*APA Rules tab* — `FindingCard` components, one per finding:
- Severity badge: ERROR (red) / WARNING (yellow) / INFO (blue)
- Rule ID (e.g. `HED002`, `MEC003`)
- Human-readable message with APA section reference
- Excerpt showing the offending text
- "Find in doc: Para N" location hint
- Suggested fix when available

*Citations tab* — `CitationIssueCard` components:
- Spelling mismatches (Levenshtein ≤ 2)
- Year mismatches
- Missing references (cited but not in reference list)
- Co-author-only matches (soft flag)
- Uncited references (in list but never cited)

### AI Polish Panel (paste mode only)

Appears below APA results. Calls `POST /api/review`:

1. If oversized (>5,000 words): confirmation dialog showing chunk count and credits required
2. On confirm: suggestions returned as `SuggestionCard` grid
3. Each card shows: original | revised | reason | edit type | % changed
4. Accept / Reject / Undo controls per suggestion
5. "Preview with accepted changes" textarea + Copy to clipboard button
6. HEAVY EDIT badge (amber) when `change_ratio > 0.4` — user must review carefully

---

## 5. Backend — Module Breakdown

### Module 2 — APA 7 Rule Engine (`module2_apa_checker.py`)

The core deterministic checker. Takes a `list[ProseParagraph]` and returns `list[Finding]`.

**Entry point:**
```python
findings = check_paragraphs(paragraphs, prose_cfg, heading_cfg)
```

**168 rules across 8 categories:**

| Category | Prefix | Count | APA Section |
|---|---|---|---|
| Mechanics & Formatting | MEC | 22 | §2, §6, §8.25/8.30 |
| Bias-Free Language | BFL | 34 | §5 |
| Style & Grammar | STY | 16 | §4 |
| Heading Structure | HED | 2 | §2.27 |
| In-Text Citations | CIT | 15 | §8 |
| Reference List | REF | 21 | §9 |
| Tables & Figures | TBL | 6 | §7 |
| Program Requirements | PRF | 3 | configurable |

### Module 3 — Citation Matcher (`module3_citation_matcher.py`)

Parses in-text citations and reference list entries independently, then cross-checks them.

**Entry points:**
```python
# From raw text strings
result = run_citation_check(body_text, reference_text, levenshtein_threshold=2)

# From ProseParagraph list (used by docx endpoint)
result = run_citation_check_paragraphs(paragraphs, ref_text, levenshtein_threshold=2)
```

**Output (`CitationMatchResult`):**
- `missing_references`: cited but no matching reference entry
- `uncited_references`: in reference list but never cited
- `year_mismatches`: author matched but year differs
- `spelling_mismatches`: Levenshtein ≤ threshold, same year (soft flag)
- `co_author_only_matches`: matched on co-author surname only

### Module 1 — AI Polish (`module1_editor.py`)

LLM-based clarity and register editor. Sends text to Claude, receives structured JSON with original/revised sentence pairs. Citation lock validates that all citations present in the original appear unchanged in the suggestion.

**Credit flow:**
1. `POST /api/review/estimate` — word count + chunk count preview (no LLM call)
2. `POST /api/review` — if oversized and `confirmed_oversized=False`, returns confirmation
3. On confirm: splits into chunks, calls LLM per chunk, charges one credit per successful chunk
4. Text is not retained after response is sent

### `prose_extractor.py` — Paragraph Classification

The foundation of all rule checking. Converts a `.docx` `Document` into a typed `list[ProseParagraph]`. See [Section 7](#7-paragraph-classification-system) for full details.

### `apa_ref_rules.py` — Reference List Rules (REF001–REF023)

Applied to reference-list entries only. Key rules:
- REF001: DOI format (must be `https://doi.org/10.xxxx/...`)
- REF002: Old DOI formats (`http://` or `dx.doi.org`)
- REF003: "Retrieved from" prefix (not used in APA 7)
- REF006: Wrong `n.d.` format — `(nd)`, `(n.d)`, `(N.D.)`, `(no date)`
- REF010: Publisher business designations (`Ltd.`, `Inc.`, `LLC`) must be omitted
- REF014–REF023: Author formatting, hanging indent, alphabetical order

### `apa_bfl_rules.py` — Bias-Free Language (BFL001–BFL034)

Applied to author prose only (never inside quoted spans). Returns `Severity.SUGGESTION` with explicit replacement text. Covers:
- Preferred identity-first vs person-first language
- Outdated diagnostic/group labels
- Generalised terms replacing specific identities
- Age-related, socioeconomic, and gender-related language

---

## 6. APA 7 Rules Implemented

### Mechanics (MEC)

| Rule | Description |
|---|---|
| MEC001 | Double space between words |
| MEC002 | Sentence starting with a numeral (spell out) |
| MEC003 | Numerals below threshold (zero–nine spelled out; exceptions: units, statistics, %, n=, ratios, decimals, APA version numbers, numbered series) |
| MEC006 | "percent" spelled out when `%` symbol is required after numerals |
| MEC007 | p-value with leading zero (`p = 0.03` should be `p = .03`) |
| MEC009 | p-value expressed as inequality when exact value should be reported |
| MEC011 | Apostrophe used to pluralise acronyms (`EDs` not `ED's`) |
| MEC012 | Spaced em-dash (must be unspaced `—`) |
| MEC013 | Hyphen after `-ly` adverb (`highly-effective` → `highly effective`) |
| MEC018 | Lowercase "table" or "figure" in reference (`Table 1` not `table 1`) |
| MEC019 | Capitalised "Page" abbreviation (`p.` not `P.`) |

### Style & Grammar (STY)

| Rule | Description |
|---|---|
| STY001 | Passive voice (suggestion only) |
| STY008 | Researcher self-reference as third person (`the researcher`, `the present author`) |
| STY009 | Contractions in academic prose |
| STY010 | Bare demonstrative subject (`This shows` — must be `This study shows`) |

### Heading Structure (HED)

| Rule | Description |
|---|---|
| HED001 | Skipped heading level (Level 1 → Level 3 with no Level 2) |
| HED002 | Heading immediately followed by another heading with no body text |

### In-Text Citations (CIT)

| Rule | Description |
|---|---|
| CIT001 | Missing year in parenthetical citation |
| CIT002 | "et al." without prior full citation in same document |
| CIT003 | Repeated narrative citation within same paragraph |
| CIT005 | Multiple citations not in alphabetical order |
| CIT006 | Wrong `n.d.` format in citation |

### Reference List (REF)

See `apa_ref_rules.py` for full list (REF001–REF023).

### Program Requirements (PRF)

| Rule | Description |
|---|---|
| PRF001 | Short paragraph: fewer than `min_sentences_per_paragraph` sentences (default: 2) |
| PRF002 | Long paragraph: exceeds `max_sentences_per_paragraph` (if configured) |
| PRF003 | First-person pronouns (configurable; off by default; APA 7 endorses "I"/"we") |

---

## 7. Paragraph Classification System

### `ProseParagraph` Dataclass

```python
@dataclass
class ProseParagraph:
    index: int              # 0-based paragraph index in the document
    style_name: str         # Word style name, e.g. "Normal", "Heading 1"
    raw_text: str           # Original text
    masked_text: str        # Inline quoted spans replaced with QUOTE_MASK
    heading_level: Optional[int]  # See table below
    is_reference_entry: bool      # True for entries after "References" heading
```

### `heading_level` Values

| Value | Meaning | Rule behaviour |
|---|---|---|
| `1`–`5` | Real APA section heading | HED001/HED002 apply; all prose rules skip |
| `0` | Layout/skip element | All rules skip — not a heading AND not prose |
| `None` | Body prose | All prose rules (MEC/BFL/STY/PRF/CIT/TBL) apply |

### Classification Logic in `_heading_level()` (prose_extractor.py:138)

Steps are evaluated in order; first match wins:

1. **Explicit Word heading style** (`Heading 1`–`Heading 5`) → return `1`–`5`
2. **Known non-prose layout styles** (`Title`, `Subtitle`, `Author`, `Date`, `TOC 1`–`3`, `Caption`, `Header`, `Footer`, `List Paragraph`, etc.) → return `0`
3. **Table/figure label exclusion** (matches `Table N` or `Figure N`) → return `None` (never a heading)
4. **Centered AND all-bold** (≤ 200 chars, not a table label) → return `1`
5. **All-bold** (≤ 200 chars, left-aligned manual heading) → return `1`
6. **ALL-CAPS text-only heuristic** (≤ 200 chars, no list item, no citation year) → return `1`
7. **Title-page fragment** (≤ 8 words, no terminal punctuation `.!?`) → return `0`
8. Fallback → return `None` (body prose)

### Why `heading_level=0` Exists

Many documents place title-page content (author name, institution, degree program, date, subtitle) in Word `Normal` style rather than `Title`/`Author`/`Date` styles. Without a level-0 sentinel:
- PRF001 fires on "Dihan Zhang" (1 sentence, below the 2-sentence minimum)
- HED002 fires when a document-title heading is followed by these elements

The step-7 heuristic catches most of these without misclassifying real APA section headings (which are bold and caught at steps 4–5 before reaching step 7).

### Quote Masking

Before any rule runs, inline quoted text is replaced with `\x00QUOTE\x00`. This prevents BFL, STY, and MEC rules from flagging language that belongs to a quoted source rather than the author. Pattern:
```python
_INLINE_QUOTE_RE = re.compile(r'"[^"]*?"' r'|"[^"]*?"')
```

### Reference Section Detection

`extract_prose()` switches `in_reference_section = True` when it encounters a paragraph whose `heading_level is not None` and text matches `^\s*references?\s*$` (case-insensitive). Subsequent body-prose paragraphs are added with `is_reference_entry=True` instead of being excluded, so Module 3 can read them. Prose rules skip reference entries.

---

## 8. Citation & Reference Matching

### Citation Parsing (`parse_citations()`)

Handles both parenthetical and narrative forms:

**Parenthetical:** `(Author, Year)`, `(Author & Author, Year)`, `(Author et al., Year)`, `(Author, Year; Author, Year)`

**Narrative:** `Author (Year)`, `Authors and Author (Year)`, `Kotter's (1996)` (possessive)

**Normalisation applied:**
- Unicode smart quotes → ASCII (`'`→`'`, `"`→`"`) before parsing
- Discourse prefix stripping: `Meanwhile Allied Market...` → `Allied Market...` (strips "meanwhile", "however", "furthermore", etc.)
- Possessive suffix stripping: `Kotter's` → `Kotter`

### Reference Parsing (`parse_references()`)

Parses entries of the form `Surname, I. (Year)...` or `Organisation Name. (Year)...`

**Year extraction:** `re.search(r'\((\d{4}[a-z]?)(?=[,\s)])', line)` — the lookahead `(?=[,\s)])` correctly handles `(2024, March)` and `(2024a)` formats.

**Group/organisation detection (`is_group_author()`):** Entries where the "surname" contains connective words (`of`, `for`, `and`, `the`) or known acronym patterns are flagged `is_group=True`. The `first_author` field stores the full normalised organisation name rather than splitting on commas.

### Matching Algorithm

1. **Exact surname + year match** (normalised) → matched
2. **`et al.` citation match** — extract all co-author surnames from reference; match if primary citation author is the first surname in the reference
3. **Substring guard** — short citation surname is a substring of a longer reference surname → flag as spelling mismatch, not truly missing
4. **Group-author first-word match** — `Stanford HAI` matches `Stanford Institute for Human-Centered Artificial Intelligence` when `is_group=True`, years agree, and citation is shorter than reference name
5. **Truly missing** → add to `missing_references`
6. **Uncited references** → any reference not matched by any citation → `uncited_references`

### Year Base Normalisation

`year_base()` strips trailing letter suffixes for comparison: `"2021a"` → `"2021"`. Year extraction also handles `(2026, March)` by using the lookahead pattern instead of matching a closing parenthesis directly.

---

## 9. Configuration

`backend/app/config/prof_checklist.yaml` — edit thresholds without touching code:

```yaml
prose_rules:
  min_sentences_per_paragraph: 2     # PRF001 threshold
  numeral_threshold: 10              # MEC003: spell out below this
  flag_first_person_pronouns: false  # PRF003: off by default (APA 7 endorses I/we)
  flag_repeated_narrative_citations: true
  flag_while_contrast: true
  first_person_allowed_in_positionality: true
  positionality_section_keywords:
    - positionality
    - reflexivity
    - limitations

citation_rules:
  spelling_mismatch_threshold: 2     # Levenshtein distance
  require_year_match_for_spelling_mismatch: true

heading_rules:
  flag_heading_without_body: true    # HED002
  flag_skipped_heading_levels: true  # HED001

reference_rules:
  check_hanging_indent: true
  check_alphabetical_order: true
```

---

## 10. Test Suite

**Location:** `backend/tests/`  
**Runner:** `python -m pytest tests/ -q`  
**Current count: 180 tests, all passing in < 1 second**

### test_module2.py — APA Rule Engine

Covers MEC001–MEC019, STY008–STY010, HED001, HED002, CIT003, CIT006, PRF001 and more. Each test creates a minimal `ProseParagraph` directly and asserts the correct `rule_id` fires (or doesn't fire).

Pattern:
```python
def _para(text, level=None):
    return ProseParagraph(0, "Normal", text, text, level, False)

class TestMEC003(unittest.TestCase):
    def test_small_numeral_flagged(self):
        ids = {f.rule_id for f in check_paragraphs([_para("There were 3 participants.")])}
        self.assertIn("MEC003", ids)
```

### test_module3.py — Citation Matching

46 tests across 15 test classes covering all 6 previously identified citation bugs:

| Test Class | Bug Covered |
|---|---|
| `TestYearWithMonthFormat` | `Gartner (2026, March)` — year extraction with comma |
| `TestGroupAuthorAbbreviation` | `Stanford HAI` → `Stanford Institute for Human-Centered AI` |
| `TestDiscoursePrefix` | `Meanwhile Allied Market Research (2024)` |
| `TestPossessiveApostrophe` | `Kotter's (1996)` with Unicode smart-quote apostrophe |
| `TestGroupAuthorUncited` | `Allied Market Research. (2024, April)` reference not flagged uncited |
| `TestGroupAuthorVariantName` | `Stanford Institute...` reference not flagged uncited |

### test_module1.py — LLM + Credit Logic

Covers citation lock (preserved/dropped/added/altered), text splitter (chunk boundaries, paragraph-level splits, citation preservation), edit classification (change ratio), and module 1 integration with a mock LLM provider.

---

## 11. Known Issues & Pending Fixes

### HED002 False Positives on Document-Level Headings

**Status: Fixed as of 2026-06-27**

**Previous symptoms:**
- `HED002` fired on Para 9 "Organizational Change Implementation Plan"
- `HED002` fired on Para 21 "Introduction to the Problem and Proposed Change"
- `HED002` fired on Para 31 "Theory or Model of Change and Vision Statement"

**Root cause:** Bold or centered title-page elements were classified as real APA headings before the title-page fragment heuristic could mark them as layout elements.

**Fix applied:**
- `extract_prose()` now post-processes the title-page / preamble zone and reclassifies heuristic title-page headings as `heading_level=0`.
- Documents with explicit Word `Heading 1`–`Heading 5` styles reclassify heuristic headings before the first explicit heading as layout elements.
- All-manual documents preserve the final real heading immediately before the first body paragraph as the likely first APA section heading, while reclassifying earlier heuristic headings as layout elements.
- `HED002` now scans for body prose before the next real heading instead of using `_HED002_MAX_GAP`.

**Regression coverage:** `backend/tests/test_prose_extractor.py` verifies docx-level preamble classification for both explicit-heading and all-manual documents. `backend/tests/test_module2.py` verifies that level-0 layout elements are neutral for `HED002`.

---

### PRF001 False Positives on Title-Page Elements

**Status: Fix in place as of 2026-06-27 — verify after server restart with cleared cache**

**Symptoms:**
- PRF001 "Short paragraph: 1 sentence detected" fires on:
  - "Dihan Zhang"
  - "University of Southern California"
  - "Organizational Change and Leadership (EdD)"
  - "Implementation Plan"
  - "June 13, 2026"

**Root cause:** These paragraphs use Word `Normal` style without bold formatting. The `_heading_level()` function falls through all checks (not Heading 1–5 style, not in `_SKIP_STYLES`, not bold, not ALL-CAPS) and returns `None` (body prose). PRF001 then fires because each is a single "sentence."

**Fix applied** (`prose_extractor.py:181–187`):
```python
# Step 7: Title-page fragment
if len(text.split()) <= 8 and not re.search(r'[.!?]', text):
    return 0
```
Returns `heading_level=0` → all prose rules skip.

**Caveat:** Real APA section headings (e.g. "Introduction", "Methods") that use `Normal` style without bold would also hit this check. However, real APA headings should always be bold (APA 7 §2.27), so the bold check at step 4/5 catches them before step 7 is reached.

**Remaining risk:** APA Level 5 headings are italic but not bold. They end with a period, so the terminal-punctuation guard in step 7 would NOT classify them as level-0 (they fall through to `return None`). This is a pre-existing limitation.

---

### REF006 / CIT006 — `(n.d.)` False Positives

**Status: Fixed**

**Problem:** `re.IGNORECASE` on `\(N\.D\.\)` also matched the correct `(n.d.)` because N→n and D→d under case-folding.

**Fix:** Split into two patterns:
```python
_ND_WRONG = re.compile(r'\(nd\)|\(n\.d\)|\(no\s+date\)|\(no-date\)', re.IGNORECASE)
_ND_WRONG_CAPS = re.compile(r'\(N\.D\.\)')   # case-sensitive, no IGNORECASE
```
Same pattern applied in both `apa_ref_rules.py` and `module2_apa_checker.py`.

---

### Citation Matching — 6 Bugs Fixed

**Status: All fixed, 46 tests cover each case**

| Bug | Fix |
|---|---|
| `Gartner (2026)` vs `Gartner. (2026, March)` year mismatch | Lookahead in year regex: `(?=[,\s)])` |
| `Stanford HAI` → no reference found | Group-author first-word matching |
| `Meanwhile Allied Market Research (2024)` | Discourse-prefix strip before author parse |
| `Kotter's (1996)` possessive apostrophe (Unicode) | `_normalize_quotes()` at start of `parse_citations()` |
| `Allied Market Research. (2024, April)` uncited | Same year lookahead fix |
| `Stanford Institute...` reference uncited | Group-author `is_group=True` + first-word match |

---

### Edit Tool Smart-Quote Corruption

**Status: Resolved workflow issue — document for future sessions**

When editing Python files with the Edit tool, single-quote string delimiters (`r'...'`) can be converted to Unicode smart quotes (U+2018 `'` / U+2019 `'`), causing `SyntaxError` on import.

**Symptom:** After an Edit tool call to a `.py` file, the server imports fail or regex patterns silently change.

**Fix pattern:** Run a Python script to restore ASCII apostrophes on all lines except those intentionally containing Unicode (e.g., lines with explicit Unicode character literals):
```python
with open("file.py", encoding="utf-8") as f:
    lines = f.readlines()
preserved = {108, 179}  # line numbers with intentional Unicode
for i, line in enumerate(lines, 1):
    if i not in preserved:
        line = line.replace('‘', "'").replace('’', "'")
    out.append(line)
```

---

### Temp Files in Backend Root

**Status: Low priority cleanup**

Several text extraction scripts left intermediate files in `backend/`:
```
apa_ch4.txt through apa_ch11.txt
ch3_jars.txt through ch9_references.txt
CUsersdihanch4_part1.txt
CUsersdihanch5_part1.txt
CUsersdihanapa7_gap_analysis.txt
```
These are source extraction artifacts from APA 7 manual ingestion. Safe to delete or move to a `raw/` directory.

---

## 12. Development Log

### Session 1 (prior)
- Implemented Module 2 APA rule engine with 168 rules
- Implemented Module 3 citation matcher
- Implemented Module 1 LLM polish with credit gate and citation lock
- Built Next.js frontend (landing page + review UI)
- Set up pytest suite

### Session 2 (prior)
- Fixed 6 citation/reference matching errors:
  - Year extraction regex for `(YYYY, Month)` format
  - Group-author abbreviation matching
  - Discourse-prefix stripping on narrative citations
  - Unicode possessive apostrophe normalisation
  - Group-author `is_group` flag and first-word matching
- Added 46 tests covering all 6 bugs (`test_module3.py`)
- Fixed 23 HED002 false positives on tables, figures, and non-section headings
  - Added `heading_level=0` sentinel to `ProseParagraph`
  - Added `_SKIP_STYLES` set to `_heading_level()`
  - Added `_TABLE_FIGURE_LABEL_RE` exclusion
  - Changed bold+centered heuristic to require BOTH conditions

### Session 3 (2026-06-20)
- Fixed REF006: `(n.d.)` flagged as wrong — split `_ND_WRONG` regex into IGNORECASE and case-sensitive patterns
- Fixed CIT006: same IGNORECASE bug + `\|` typo in alternation
- Fixed HED002 proximity guard: `_HED002_MAX_GAP = 5` prevents Para 9→21 (gap=12) and Para 21→31 (gap=10) from firing
- Added step-7 title-page fragment heuristic in `_heading_level()` to classify short non-bold non-punctuated paragraphs as `heading_level=0`
- Identified persistent HED002 false positives on Para 9, 21, 31 — root cause is bold paragraphs immediately adjacent in document index
- Total test count: 175 passing

### Session 4 (2026-06-27)
- Replaced HED002 paragraph-index proximity guard with a body-prose scan between real headings
- Extended `extract_prose()` preamble post-processing for all-manual documents:
  - heuristic title-page headings before the first body paragraph become `heading_level=0`
  - the final heading immediately before body prose is preserved as the likely first section heading
- Added docx-level extractor regression tests for explicit Word headings and all-manual heading formatting
- Added HED002 regression tests for level-0 layout elements between headings
- Total test count: 180 passing

### Pending Next Session
- [ ] Clean up temp `.txt` files in `backend/` root
- [ ] Restrict CORS origins from `"*"` to specific frontend domain before production deployment
- [ ] Wire up payment/Stripe for credit top-up
- [ ] Consider persisting credit balances to a database (currently in-memory via `credits.py`)
