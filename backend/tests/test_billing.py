from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


class FakeCheckoutSessions:
    def __init__(self):
        self.params = None

    def create(self, params):
        self.params = params
        return type("Session", (), {"url": "https://checkout.stripe.test/session"})()


class FakeStripeClient:
    def __init__(self):
        self.checkout = type("Checkout", (), {"sessions": FakeCheckoutSessions()})()


def test_checkout_uses_one_time_submission_pass_price():
    from app.services.access import CurrentUser
    from app.services.billing import create_checkout_session

    stripe_client = FakeStripeClient()
    user = CurrentUser(id="user-1", email="student@example.com")

    url = create_checkout_session(
        user=user,
        stripe_client=stripe_client,
        price_id="price_1U0EGA1hGDXgltDgofSJbFBS",
        site_url="https://dissertation-tool.netlify.app",
    )

    assert url == "https://checkout.stripe.test/session"
    assert stripe_client.checkout.sessions.params["mode"] == "payment"
    assert stripe_client.checkout.sessions.params["line_items"] == [
        {"price": "price_1U0EGA1hGDXgltDgofSJbFBS", "quantity": 1}
    ]
    assert stripe_client.checkout.sessions.params["client_reference_id"] == "user-1"


@pytest.mark.asyncio
async def test_completed_checkout_activates_a_thirty_day_pass_once():
    from app.services.billing import fulfil_completed_checkout

    class Repo:
        def __init__(self):
            self.kwargs = None

        async def fulfil_submission_pass(self, **kwargs):
            self.kwargs = kwargs
            return True

    now = datetime(2026, 8, 3, tzinfo=UTC)
    repo = Repo()
    activated = await fulfil_completed_checkout(
        event_id="evt_1",
        checkout_session={
            "id": "cs_1",
            "client_reference_id": "00000000-0000-0000-0000-000000000001",
            "payment_intent": "pi_1",
            "payment_status": "paid",
        },
        repository=repo,
        now=now,
        pass_duration_days=30,
    )

    assert activated is True
    assert repo.kwargs["expires_at"] == now + timedelta(days=30)


@pytest.mark.asyncio
async def test_unpaid_checkout_does_not_activate_a_pass():
    from app.services.billing import fulfil_completed_checkout

    with pytest.raises(ValueError, match="not paid"):
        await fulfil_completed_checkout(
            event_id="evt_1",
            checkout_session={"id": "cs_1", "client_reference_id": "user-1", "payment_status": "unpaid"},
            repository=object(),
            now=datetime(2026, 8, 3, tzinfo=UTC),
            pass_duration_days=30,
        )
