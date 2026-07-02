from docx import Document

from app.main import _highlight_runs


def test_highlight_runs_splits_single_run_to_target_phrase_only():
    doc = Document()
    para = doc.add_paragraph("The initiative is delivered by four coordinated teams.")

    anchor_runs = _highlight_runs(para, "is delivered", "SUGGESTION")

    assert para.text == "The initiative is delivered by four coordinated teams."
    assert [run.text for run in anchor_runs] == ["is delivered"]

    highlighted = [run.text for run in para.runs if run.font.highlight_color is not None]
    assert highlighted == ["is delivered"]


def test_highlight_runs_falls_back_to_one_sentence_not_whole_paragraph():
    doc = Document()
    para = doc.add_paragraph(
        "The first sentence should be marked. The second sentence should remain plain."
    )

    anchor_runs = _highlight_runs(para, "missing target", "WARNING")

    assert para.text == "The first sentence should be marked. The second sentence should remain plain."
    assert [run.text for run in anchor_runs] == ["The first sentence should be marked."]

    highlighted = [run.text for run in para.runs if run.font.highlight_color is not None]
    assert highlighted == ["The first sentence should be marked."]
