from __future__ import annotations

from typing import Protocol

from .access import CurrentUser


class StripeClient(Protocol):
    checkout: object


def create_checkout_session(
    *,
    user: CurrentUser,
    stripe_client: StripeClient,
    price_id: str,
    site_url: str,
) -> str:
    session = stripe_client.checkout.sessions.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=user.id,
        customer_email=user.email,
        success_url=f"{site_url.rstrip('/')}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{site_url.rstrip('/')}/checkout/cancel",
    )
    return session.url
