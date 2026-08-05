from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta

BETA_LINK_DURATION_DAYS = 30

# secrets.token_urlsafe(32) is 32 random bytes rendered as 43 base64url characters.
_TOKEN_BYTES = 32
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


def generate_beta_token() -> str:
    """Return a new opaque beta link secret. The caller must show it only once."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def is_beta_token_shaped(token: str) -> bool:
    """Reject malformed values before they reach the database."""
    return bool(_TOKEN_PATTERN.fullmatch(token or ""))


def hash_beta_token(token: str) -> str:
    """Return the value stored in Supabase. The raw secret is never stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def beta_link_expiry(now: datetime) -> datetime:
    return now + timedelta(days=BETA_LINK_DURATION_DAYS)
