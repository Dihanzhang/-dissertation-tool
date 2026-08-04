from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from .access import CurrentUser


class StripeClient(Protocol):
    checkout: object


class PaymentRepository(Protocol):
    async def fulfil_submission_pass(self, **kwargs) -> bool: ...


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


async def fulfil_completed_checkout(
    *,
    event_id: str,
    checkout_session: dict,
    repository: PaymentRepository,
    now: datetime,
    pass_duration_days: int,
) -> bool:
    if checkout_session.get("payment_status") != "paid":
        raise ValueError("Checkout session is not paid.")
    user_id = checkout_session.get("client_reference_id")
    session_id = checkout_session.get("id")
    if not user_id or not session_id:
        raise ValueError("Checkout session is missing its account reference.")
    payment_intent = checkout_session.get("payment_intent")
    return await repository.fulfil_submission_pass(
        event_id=event_id,
        user_id=str(user_id),
        checkout_session_id=str(session_id),
        payment_intent_id=str(payment_intent) if payment_intent else None,
        starts_at=now,
        expires_at=now + timedelta(days=pass_duration_days),
    )
