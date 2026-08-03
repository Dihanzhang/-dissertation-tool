from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedbackInput:
    message: str
    name: str = ""
    contact: str = ""
    website: str = ""


@dataclass(frozen=True)
class Feedback:
    message: str
    name: str | None
    contact: str | None


def validate_feedback(submission: FeedbackInput) -> Feedback:
    if submission.website.strip():
        raise ValueError("Unable to accept feedback.")

    message = submission.message.strip()
    name = submission.name.strip()
    contact = submission.contact.strip()
    if not 10 <= len(message) <= 2000:
        raise ValueError("Feedback must be between 10 and 2,000 characters.")
    if len(name) > 120 or len(contact) > 254:
        raise ValueError("Feedback details are too long.")

    return Feedback(message=message, name=name or None, contact=contact or None)
