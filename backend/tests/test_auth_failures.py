from __future__ import annotations

import pytest
from fastapi import HTTPException


async def _verify_with_status(status_code: int, payload: dict | None = None):
    from app.auth import SupabaseAuthenticator

    async def get_user(url, headers):
        return status_code, payload if payload is not None else {}

    authenticator = SupabaseAuthenticator("https://project.supabase.co", "anon-key", get_user)
    return await authenticator.verify("a-token")


@pytest.mark.asyncio
async def test_a_rejected_token_asks_the_user_to_sign_in():
    with pytest.raises(HTTPException) as rejected:
        await _verify_with_status(401)

    assert rejected.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("upstream_status", [429, 500, 502, 503, 504])
async def test_a_temporary_supabase_failure_is_not_reported_as_signed_out(upstream_status):
    """A 401 makes the browser discard the session and demand a new emailed code,
    so rate limits and outages must not be reported as a bad sign-in."""
    with pytest.raises(HTTPException) as failure:
        await _verify_with_status(upstream_status)

    assert failure.value.status_code == 503


@pytest.mark.asyncio
async def test_a_valid_token_returns_the_user():
    user = await _verify_with_status(200, {"id": "user-1", "email": "student@example.com"})

    assert user.id == "user-1"
    assert user.email == "student@example.com"
