from __future__ import annotations

import pytest


def test_honeypot_feedback_is_rejected():
    from app.services.feedback import FeedbackInput, validate_feedback

    with pytest.raises(ValueError, match="Unable to accept feedback"):
        validate_feedback(FeedbackInput(message="Useful review.", website="bot"))


def test_valid_feedback_is_trimmed_and_accepted():
    from app.services.feedback import FeedbackInput, validate_feedback

    feedback = validate_feedback(FeedbackInput(
        name=" Ava ", contact=" ", message="  The comments were clear and useful.  ", website=""
    ))

    assert feedback.name == "Ava"
    assert feedback.contact is None
    assert feedback.message == "The comments were clear and useful."
