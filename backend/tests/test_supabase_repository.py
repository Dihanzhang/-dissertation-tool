from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.mark.asyncio
async def test_repository_reads_only_an_active_unexpired_pass():
    from app.services.supabase import SupabasePassRepository

    received: dict[str, object] = {}

    async def fake_request(method: str, url: str, **kwargs):
        received.update({"method": method, "url": url, **kwargs})
        return 200, [{"expires_at": "2026-09-02T00:00:00+00:00"}]

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    result = await repo.find_active_pass("user-1", datetime(2026, 8, 3, tzinfo=UTC))

    assert result == {"expires_at": "2026-09-02T00:00:00+00:00"}
    assert received["method"] == "GET"
    assert received["headers"]["apikey"] == "service-key"
    assert received["params"]["user_id"] == "eq.user-1"
    assert received["params"]["status"] == "eq.active"


@pytest.mark.asyncio
async def test_repository_stores_validated_feedback_with_service_key():
    from app.services.feedback import Feedback
    from app.services.supabase import SupabasePassRepository

    received: dict[str, object] = {}

    async def fake_request(method: str, url: str, **kwargs):
        received.update({"method": method, "url": url, **kwargs})
        return 201, []

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    await repo.save_feedback(Feedback(name="Dihan", contact=None, message="This review was very helpful."))

    assert received["method"] == "POST"
    assert received["url"] == "https://project.supabase.co/rest/v1/feedback"
    assert received["json"] == {"name": "Dihan", "contact": None, "message": "This review was very helpful."}


@pytest.mark.asyncio
async def test_repository_fulfils_a_payment_through_the_atomic_database_function():
    from app.services.supabase import SupabasePassRepository

    received: dict[str, object] = {}

    async def fake_request(method: str, url: str, **kwargs):
        received.update({"method": method, "url": url, **kwargs})
        return 200, True

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    was_new = await repo.fulfil_submission_pass(
        event_id="evt_1",
        user_id="00000000-0000-0000-0000-000000000001",
        checkout_session_id="cs_1",
        payment_intent_id="pi_1",
        starts_at=datetime(2026, 8, 3, tzinfo=UTC),
        expires_at=datetime(2026, 9, 2, tzinfo=UTC),
    )

    assert was_new is True
    assert received["method"] == "POST"
    assert received["url"] == "https://project.supabase.co/rest/v1/rpc/fulfil_submission_pass"
    assert received["json"]["p_stripe_event_id"] == "evt_1"
    assert received["json"]["p_checkout_session_id"] == "cs_1"


@pytest.mark.asyncio
async def test_repository_creates_a_beta_link_without_sending_the_raw_secret():
    from app.services.supabase import SupabasePassRepository

    received: dict[str, object] = {}

    async def fake_request(method: str, url: str, **kwargs):
        received.update({"method": method, "url": url, **kwargs})
        return 201, [{"id": "link-1", "label": "tester-a", "expires_at": "2026-09-04T00:00:00+00:00"}]

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    link = await repo.create_beta_access_link(
        token_hash="a-sha256-hash",
        expires_at=datetime(2026, 9, 4, tzinfo=UTC),
        label="tester-a",
    )

    assert link["id"] == "link-1"
    assert received["method"] == "POST"
    assert received["url"] == "https://project.supabase.co/rest/v1/beta_access_links"
    assert received["json"] == {
        "token_hash": "a-sha256-hash",
        "expires_at": "2026-09-04T00:00:00+00:00",
        "label": "tester-a",
    }


@pytest.mark.asyncio
async def test_repository_revokes_a_beta_link_by_id():
    from app.services.supabase import SupabasePassRepository

    received: dict[str, object] = {}

    async def fake_request(method: str, url: str, **kwargs):
        received.update({"method": method, "url": url, **kwargs})
        return 200, [{"id": "link-1"}]

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    revoked = await repo.revoke_beta_access_link(
        link_id="link-1", at=datetime(2026, 8, 5, tzinfo=UTC)
    )

    assert revoked is True
    assert received["method"] == "PATCH"
    assert received["params"] == {"id": "eq.link-1"}
    assert received["json"]["status"] == "revoked"
