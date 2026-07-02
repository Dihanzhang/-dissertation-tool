# APA Rule Audit Before Beta Testing

Date: 2026-07-02

## Scope

Reviewed deterministic APA rules against the local APA source text in `backend/apa_ch4.txt`, `backend/apa_ch6.txt`, `backend/apa_ch7.txt`, `backend/apa_ch8.txt`, and `backend/apa_ch9.txt`.

This was a rule-quality audit, focused on false positives, section accuracy, and severity calibration. It was not a legal/copyright validation of the source text.

## Sections Rechecked

- Paragraph length and single-sentence paragraphs: APA 4.6
- Active/passive voice and style guidance: APA 4.13-4.23
- Em dashes, hyphenation, capitalization, numbers, units, lists, and statistics: APA 6.6, 6.12, 6.19, 6.27-6.28, 6.32-6.39, 6.43-6.44, 6.51-6.52
- Tables and figures: APA 7.2, 7.10, 7.19, 7.24-7.26
- In-text citations and group authors: APA 8.10, 8.13, 8.17-8.19, 8.21, 8.23-8.25, 8.30
- Reference list formatting: APA 9.8, 9.14, 9.17, 9.25, 9.29, 9.34-9.35, 9.39, 9.41, 9.43-9.44, 9.47, 9.50

## Corrections Made

- Corrected em dash rule citation from APA 6.7 to APA 6.6.
- Corrected `-ly` adverb hyphenation citation from APA 6.9 to APA 6.12.
- Narrowed subtable letter-suffix rule to tables only; APA allows labeled figure panels.
- Added group-author guards so organization names containing `and` or `&` are not mistaken for multi-author citation punctuation errors.
- Calibrated subjective style guidance to `Suggestion` severity instead of `Warning`.
- Kept mechanics, citation, reference, heading, and table/figure format violations as `Warning` or `Error` depending on likely action required.
- Confirmed previous fixes for comma-grouped numbers, list-item paragraph handling, and DOCX first-line indentation.

## Remaining Risk

Some checks are heuristic because DOCX and plain text do not expose all APA-relevant intent. The beta should still ask testers to report false positives, especially for organization names, complex references, custom Word templates, and manually formatted headings.
