from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


class FakePassRepository:
    def __init__(self):
        self.passes: list[dict] = []

    def add_pass(self, user_id: str, starts_at: datetime, expires_at: datetime) -> None:
        self.passes.append({"user_id": user_id, "starts_at": starts_at, "expires_at": expires_at, "status": "active"})

    def find_active_pass(self, user_id: str, at: datetime):
        return next((item for item in self.passes if item["user_id"] == user_id and item["status"] == "active" and item["starts_at"] <= at < item["expires_at"]), None)


def test_active_pass_allows_submission():
    from app.services.access import CurrentUser, entitlement_for

    now = datetime(2026, 8, 3, tzinfo=UTC)
    repo = FakePassRepository()
    user = CurrentUser(id="user-1", email="student@example.com")
    repo.add_pass(user.id, now, now + timedelta(days=1))

    assert entitlement_for(user, repo, now).can_submit is True


def test_expired_pass_blocks_submission():
    from app.services.access import CurrentUser, entitlement_for

    now = datetime(2026, 8, 3, tzinfo=UTC)
    repo = FakePassRepository()
    user = CurrentUser(id="user-1", email="student@example.com")
    repo.add_pass(user.id, now - timedelta(days=31), now)

    assert entitlement_for(user, repo, now).can_submit is False


@pytest.mark.asyncio
async def test_supabase_authenticator_returns_verified_user():
    from app.auth import SupabaseAuthenticator

    async def fake_get(url: str, headers: dict[str, str]):
        assert url == "https://project.supabase.co/auth/v1/user"
        assert headers["Authorization"] == "Bearer valid-token"
        return 200, {"id": "user-1", "email": "student@example.com"}

    authenticator = SupabaseAuthenticator("https://project.supabase.co", "anon-key", fake_get)

    user = await authenticator.verify("valid-token")

    assert user.id == "user-1"
    assert user.email == "student@example.com"
