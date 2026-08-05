from __future__ import annotations

import os
from dataclasses import dataclass


PUBLIC_SITE_ORIGINS = ("https://apa7.aithrival.com", "https://www.apa7.aithrival.com")


@dataclass(frozen=True)
class Settings:
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_id: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    site_url: str
    cors_origins: tuple[str, ...]
    pass_duration_days: int
    max_upload_bytes: int

    @classmethod
    def from_env(cls) -> "Settings":
        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        if stripe_secret_key.startswith("sk_live_") and not stripe_webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is required with a live Stripe key.")
        configured_origins = [
            origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
        ]
        if os.getenv("ENVIRONMENT", "").lower() == "production" and "*" in configured_origins:
            raise ValueError("CORS_ORIGINS cannot use * in production.")
        # The public site must always be able to call its own API, even if
        # CORS_ORIGINS was configured before the custom domain existed.
        site_url = os.getenv("SITE_URL", "http://localhost:3000").rstrip("/")
        cors_origins = tuple(
            dict.fromkeys([*configured_origins, site_url, *PUBLIC_SITE_ORIGINS])
        )

        return cls(
            stripe_secret_key=stripe_secret_key,
            stripe_webhook_secret=stripe_webhook_secret,
            stripe_price_id=os.getenv("STRIPE_PRICE_ID", ""),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            site_url=os.getenv("SITE_URL", "http://localhost:3000").rstrip("/"),
            cors_origins=cors_origins,
            pass_duration_days=int(os.getenv("PASS_DURATION_DAYS", "30")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", "10485760")),
        )
