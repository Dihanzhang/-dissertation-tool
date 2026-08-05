from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

VALID_TOKEN = "t" * 43


def test_generated_token_carries_at_least_32_random_bytes():
    from app.services.beta_links import generate_beta_token, is_beta_token_shaped

    token = generate_beta_token()

    assert len(token) == 43  # 32 random bytes, base64url encoded
    assert is_beta_token_shaped(token)
    assert generate_beta_token() != token


def test_only_the_hash_of_a_token_is_ever_stored():
    from app.services.beta_links import hash_beta_token

    digest = hash_beta_token(VALID_TOKEN)

    assert digest != VALID_TOKEN
    assert VALID_TOKEN not in digest
    assert len(digest) == 64
    assert hash_beta_token(VALID_TOKEN) == digest


def test_malformed_tokens_are_rejected_before_any_lookup():
    from app.services.beta_links import is_beta_token_shaped

    assert not is_beta_token_shaped("")
    assert not is_beta_token_shaped("short")
    assert not is_beta_token_shaped("t" * 42)
    assert not is_beta_token_shaped("t" * 43 + "/")


def test_valid_beta_link_allows_a_check_without_sign_in_or_payment(monkeypatch):
    from app import main
    from app.services.beta_links import hash_beta_token

    class Repo:
        async def find_active_beta_link(self, token_hash, at):
            assert token_hash == hash_beta_token(VALID_TOKEN)
            return {"subject_id": "11111111-1111-1111-1111-111111111111", "expires_at": "2026-09-04T00:00:00+00:00"}

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    response = TestClient(main.app).post(
        "/api/check/text",
        json={"body_text": "A short paragraph."},
        headers={"X-Beta-Access": VALID_TOKEN},
    )

    assert response.status_code == 200


def test_revoked_or_expired_beta_link_is_rejected(monkeypatch):
    from app import main

    class Repo:
        async def find_active_beta_link(self, token_hash, at):
            return None

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    response = TestClient(main.app).post(
        "/api/check/text",
        json={"body_text": "A short paragraph."},
        headers={"X-Beta-Access": VALID_TOKEN},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This private beta link is not valid or has expired."


def test_malformed_beta_token_never_reaches_the_database(monkeypatch):
    from app import main

    class Repo:
        async def find_active_beta_link(self, token_hash, at):
            raise AssertionError("A malformed token must not be looked up.")

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    response = TestClient(main.app).post(
        "/api/check/text",
        json={"body_text": "A short paragraph."},
        headers={"X-Beta-Access": "not-a-real-token"},
    )

    assert response.status_code == 403


def test_beta_access_endpoint_reports_the_expiry_date(monkeypatch):
    from app import main

    class Repo:
        async def find_active_beta_link(self, token_hash, at):
            return {"subject_id": "11111111-1111-1111-1111-111111111111", "expires_at": "2026-09-04T00:00:00+00:00"}

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    response = TestClient(main.app).get("/api/beta/access", headers={"X-Beta-Access": VALID_TOKEN})

    assert response.status_code == 200
    assert response.json() == {"can_submit": True, "status": "active", "expires_at": "2026-09-04T00:00:00+00:00"}


def test_a_beta_link_cannot_open_stripe_checkout(monkeypatch):
    from app import main

    response = TestClient(main.app).post(
        "/api/billing/checkout-session", headers={"X-Beta-Access": VALID_TOKEN}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_beta_link_repository_queries_only_active_unexpired_links():
    from app.services.supabase import SupabasePassRepository

    captured = {}

    async def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = kwargs["params"]
        return 200, [{"subject_id": "sub-1", "expires_at": "2026-09-04T00:00:00+00:00"}]

    repo = SupabasePassRepository("https://project.supabase.co", "service-key", fake_request)
    now = datetime(2026, 8, 5, tzinfo=UTC)

    result = await repo.find_active_beta_link("a-hash", now)

    assert result["subject_id"] == "sub-1"
    assert captured["url"].endswith("/beta_access_links")
    assert captured["params"]["token_hash"] == "eq.a-hash"
    assert captured["params"]["status"] == "eq.active"
    assert captured["params"]["expires_at"] == f"gt.{now.isoformat()}"


def test_migration_stores_no_raw_tokens_and_is_locked_to_service_role():
    migration = (Path(__file__).parents[1] / "migrations" / "003_beta_access_links.sql").read_text()

    assert "create table public.beta_access_links" in migration
    assert "token_hash text not null unique" in migration
    assert "\n  token " not in migration  # the raw link value is never given a column
    assert "subject_id uuid not null" in migration
    assert "expires_at timestamptz not null" in migration
    assert "check (status in ('active', 'revoked', 'expired'))" in migration
    assert "alter table public.beta_access_links enable row level security" in migration
    assert "revoke all on table public.beta_access_links from public, anon, authenticated" in migration
    assert "grant all on table public.beta_access_links to service_role" in migration


def test_sql_link_creator_matches_the_token_format_the_api_accepts():
    """Links made in the Supabase SQL editor must pass is_beta_token_shaped()."""
    migration = (Path(__file__).parents[1] / "migrations" / "003_beta_access_links.sql").read_text()

    assert "create or replace function public.create_beta_access_link" in migration
    # 32 random bytes, base64 with padding stripped, made URL-safe -> 43 chars of [A-Za-z0-9_-]
    assert "gen_random_bytes(32)" in migration
    assert "rtrim(encode(gen_random_bytes(32), 'base64'), '=')" in migration
    assert "'+/', '-_'" in migration
    # stored hashed, never raw, and matching hash_beta_token()
    assert "encode(digest(new_secret, 'sha256'), 'hex')" in migration
    assert "now() + interval '30 days'" in migration
    assert "revoke all on function public.create_beta_access_link(text) from public, anon, authenticated" in migration


def test_beta_link_default_duration_is_thirty_days():
    from app.services.beta_links import beta_link_expiry

    now = datetime(2026, 8, 5, tzinfo=UTC)

    assert beta_link_expiry(now) == now + timedelta(days=30)
