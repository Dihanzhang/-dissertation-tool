from __future__ import annotations

import pytest


def test_live_stripe_requires_webhook_secret(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_example")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET"):
        Settings.from_env()


def test_settings_loads_supabase_server_configuration(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")

    settings = Settings.from_env()

    assert settings.supabase_url == "https://project.supabase.co"
    assert settings.supabase_anon_key == "anon-key"
    assert settings.supabase_service_role_key == "service-role-key"


def test_production_rejects_wildcard_cors(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings.from_env()


def test_public_site_origin_is_always_allowed(monkeypatch):
    """The live domain must reach its own API even if CORS_ORIGINS predates it."""
    from app.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", "https://dissertation-tool.netlify.app")
    monkeypatch.setenv("SITE_URL", "https://apa7.aithrival.com")
    monkeypatch.setenv("ENVIRONMENT", "production")

    origins = Settings.from_env().cors_origins

    assert "https://apa7.aithrival.com" in origins
    assert "https://dissertation-tool.netlify.app" in origins
    assert len(origins) == len(set(origins))
