from __future__ import annotations

from datetime import UTC, datetime


class FakeCheckoutSessions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
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
    assert stripe_client.checkout.sessions.kwargs["mode"] == "payment"
    assert stripe_client.checkout.sessions.kwargs["line_items"] == [
        {"price": "price_1U0EGA1hGDXgltDgofSJbFBS", "quantity": 1}
    ]
    assert stripe_client.checkout.sessions.kwargs["client_reference_id"] == "user-1"
