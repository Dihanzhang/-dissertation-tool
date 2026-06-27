from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.modules.prose_extractor import extract_prose


def _add_bold_centered(doc: Document, text: str):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(text)
    run.bold = True
    return para


def test_explicit_heading_reclassifies_prior_heuristic_title_page_headings():
    doc = Document()
    _add_bold_centered(doc, "Organizational Change Implementation Plan")
    doc.add_paragraph("Dihan Zhang")
    doc.add_paragraph("University of Southern California")
    doc.add_paragraph("Introduction to the Problem", style="Heading 1")
    doc.add_paragraph(
        "This paragraph introduces the study context. It establishes the problem."
    )

    paragraphs = extract_prose(doc)

    assert paragraphs[0].heading_level == 0
    assert paragraphs[1].heading_level == 0
    assert paragraphs[2].heading_level == 0
    assert paragraphs[3].heading_level == 1
    assert paragraphs[4].heading_level is None


def test_all_manual_document_preserves_first_section_heading_after_preamble():
    doc = Document()
    _add_bold_centered(doc, "Organizational Change Implementation Plan")
    doc.add_paragraph("Dihan Zhang")
    doc.add_paragraph("University of Southern California")
    _add_bold_centered(doc, "Introduction to the Problem")
    doc.add_paragraph(
        "This paragraph introduces the study context. It establishes the problem."
    )

    paragraphs = extract_prose(doc)

    assert paragraphs[0].heading_level == 0
    assert paragraphs[1].heading_level == 0
    assert paragraphs[2].heading_level == 0
    assert paragraphs[3].heading_level == 1
    assert paragraphs[4].heading_level is None
