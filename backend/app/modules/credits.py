"""
Credit store — in-memory implementation for Build Step 2.
Build Step 4 replaces this with a Supabase-backed implementation.

TEST_MODE=true (env var) grants unlimited credits, bypassing all checks.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass

TEST_MODE = os.getenv("TEST_MODE", "false").lower() in ("true", "1", "yes")
WORD_CAP_PER_CREDIT = int(os.getenv("WORD_CAP_PER_CREDIT", "5000"))
FREE_TRIAL_WORD_CAP = int(os.getenv("FREE_TRIAL_WORD_CAP", "3000"))

_mu = threading.Lock()
_credits: dict[str, int] = {}
_used_trial: set[str] = set()
_seen_request_ids: set[str] = set()


@dataclass
class CreditCheck:
    allowed: bool
    reason: str
    credits_remaining: int
    is_free_trial: bool


def check(
    user_id: str,
    request_id: str,
    word_count: int,
    is_trial: bool = False,
) -> CreditCheck:
    """
    Return whether this request is allowed.
    Does NOT decrement — call commit() on success.
    """
    if TEST_MODE:
        return CreditCheck(allowed=True, reason="test_mode", credits_remaining=999, is_free_trial=is_trial)

    with _mu:
        if request_id in _seen_request_ids:
            return CreditCheck(
                allowed=False,
                reason="duplicate_request_id",
                credits_remaining=_credits.get(user_id, 0),
                is_free_trial=is_trial,
            )

        if is_trial:
            if user_id in _used_trial:
                return CreditCheck(allowed=False, reason="trial_already_used", credits_remaining=0, is_free_trial=True)
            if word_count > FREE_TRIAL_WORD_CAP:
                return CreditCheck(
                    allowed=False,
                    reason=f"trial_word_cap_exceeded",
                    credits_remaining=0,
                    is_free_trial=True,
                )
            return CreditCheck(allowed=True, reason="trial_ok", credits_remaining=0, is_free_trial=True)

        remaining = _credits.get(user_id, 0)
        if remaining <= 0:
            return CreditCheck(allowed=False, reason="no_credits", credits_remaining=0, is_free_trial=False)
        if word_count > WORD_CAP_PER_CREDIT:
            return CreditCheck(
                allowed=False,
                reason="word_cap_exceeded",
                credits_remaining=remaining,
                is_free_trial=False,
            )
        return CreditCheck(allowed=True, reason="ok", credits_remaining=remaining, is_free_trial=False)


def commit(user_id: str, request_id: str, is_trial: bool = False) -> None:
    """Decrement credit (or mark trial used) after a successful LLM call."""
    if TEST_MODE:
        return
    with _mu:
        _seen_request_ids.add(request_id)
        if is_trial:
            _used_trial.add(user_id)
        else:
            _credits[user_id] = max(0, _credits.get(user_id, 0) - 1)


def add_credits(user_id: str, amount: int) -> int:
    """Add credits to a user account. Returns new balance."""
    with _mu:
        _credits[user_id] = _credits.get(user_id, 0) + amount
        return _credits[user_id]


def get_balance(user_id: str) -> int:
    if TEST_MODE:
        return 999
    return _credits.get(user_id, 0)
