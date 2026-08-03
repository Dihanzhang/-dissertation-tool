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
