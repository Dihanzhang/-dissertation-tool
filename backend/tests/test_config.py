from __future__ import annotations

import pytest


def test_live_stripe_requires_webhook_secret(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_example")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET"):
        Settings.from_env()
