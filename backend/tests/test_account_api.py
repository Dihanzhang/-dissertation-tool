from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient


def test_entitlement_reports_active_pass(monkeypatch):
    from app import main
    from app.services.access import CurrentUser

    class Repo:
        async def find_active_pass(self, user_id, at):
            assert user_id == "user-1"
            return {"expires_at": "2026-09-02T00:00:00+00:00"}

    async def current_user():
        return CurrentUser(id="user-1", email="student@example.com")

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    main.app.dependency_overrides[main.get_current_user] = current_user
    try:
        response = TestClient(main.app).get("/api/account/entitlement")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "can_submit": True,
        "status": "active",
        "expires_at": "2026-09-02T00:00:00+00:00",
    }


def test_check_is_blocked_without_an_active_pass(monkeypatch):
    from app import main
    from app.services.access import CurrentUser

    class Repo:
        async def find_active_pass(self, user_id, at):
            return None

    async def current_user():
        return CurrentUser(id="user-1", email="student@example.com")

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    main.app.dependency_overrides[main.get_current_user] = current_user
    try:
        response = TestClient(main.app).post("/api/check/text", json={"body_text": "A short paragraph."})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json()["detail"] == "An active Submission Pass is required for new checks."


def test_checkout_requires_sign_in_and_returns_stripe_url(monkeypatch):
    from app import main
    from app.services.access import CurrentUser

    class Sessions:
        def create(self, **kwargs):
            assert kwargs["client_reference_id"] == "user-1"
            return type("Session", (), {"url": "https://checkout.stripe.test/session"})()

    class Client:
        checkout = type("Checkout", (), {"sessions": Sessions()})()

    async def current_user():
        return CurrentUser(id="user-1", email="student@example.com")

    monkeypatch.setattr(main, "_stripe_client", lambda: Client())
    monkeypatch.setattr(main, "_settings", lambda: type("Settings", (), {
        "stripe_price_id": "price_test",
        "site_url": "https://dissertation-tool.netlify.app",
    })())
    main.app.dependency_overrides[main.get_current_user] = current_user
    try:
        response = TestClient(main.app).post("/api/billing/checkout-session")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://checkout.stripe.test/session"}


def test_signed_stripe_webhook_activates_pass(monkeypatch):
    from app import main

    class Repo:
        def __init__(self):
            self.kwargs = None

        async def fulfil_submission_pass(self, **kwargs):
            self.kwargs = kwargs
            return True

    repo = Repo()
    monkeypatch.setattr(main, "_pass_repository", lambda: repo)
    monkeypatch.setattr(main, "_settings", lambda: type("Settings", (), {
        "stripe_webhook_secret": "whsec_test",
        "pass_duration_days": 30,
    })())
    monkeypatch.setattr(main.stripe.Webhook, "construct_event", lambda payload, signature, secret: {
        "id": "evt_1",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_1",
            "client_reference_id": "00000000-0000-0000-0000-000000000001",
            "payment_intent": "pi_1",
            "payment_status": "paid",
        }},
    })

    response = TestClient(main.app).post(
        "/api/billing/webhook", content=b"signed payload", headers={"stripe-signature": "signature"}
    )

    assert response.status_code == 200
    assert response.json() == {"received": True, "activated": True}
    assert repo.kwargs["event_id"] == "evt_1"


def test_feedback_accepts_a_valid_message(monkeypatch):
    from app import main

    saved = []

    class Repo:
        async def save_feedback(self, feedback):
            saved.append(feedback)

    monkeypatch.setattr(main, "_pass_repository", lambda: Repo())
    response = TestClient(main.app).post(
        "/api/feedback",
        json={"name": "Dihan", "contact": "dihan@example.com", "message": "This was very helpful for my reference list.", "website": ""},
    )

    assert response.status_code == 201
    assert response.json() == {"received": True}
    assert saved[0].name == "Dihan"
