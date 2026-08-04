from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx

from .feedback import Feedback

Request = Callable[..., Awaitable[tuple[int, Any]]]


async def _request(method: str, url: str, **kwargs) -> tuple[int, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(method, url, **kwargs)
    return response.status_code, response.json() if response.content else None


class SupabasePassRepository:
    """Server-only storage adapter. It always uses the Supabase service-role key."""

    def __init__(self, supabase_url: str, service_role_key: str, request: Request = _request):
        self._base_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._request = request
        self._headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    async def find_active_pass(self, user_id: str, at: datetime) -> dict | None:
        response_status, payload = await self._request(
            "GET",
            f"{self._base_url}/submission_passes",
            headers=self._headers,
            params={
                "select": "expires_at",
                "user_id": f"eq.{user_id}",
                "status": "eq.active",
                "starts_at": f"lte.{at.isoformat()}",
                "expires_at": f"gt.{at.isoformat()}",
                "limit": "1",
            },
        )
        if response_status != 200:
            raise RuntimeError("Could not read Submission Pass access.")
        return payload[0] if payload else None

    async def save_feedback(self, feedback: Feedback) -> None:
        response_status, _ = await self._request(
            "POST",
            f"{self._base_url}/feedback",
            headers={**self._headers, "Prefer": "return=minimal"},
            json={"name": feedback.name, "contact": feedback.contact, "message": feedback.message},
        )
        if response_status not in (200, 201):
            raise RuntimeError("Could not save feedback.")

    async def fulfil_submission_pass(
        self,
        *,
        event_id: str,
        user_id: str,
        checkout_session_id: str,
        payment_intent_id: str | None,
        starts_at: datetime,
        expires_at: datetime,
    ) -> bool:
        response_status, payload = await self._request(
            "POST",
            f"{self._base_url}/rpc/fulfil_submission_pass",
            headers=self._headers,
            json={
                "p_stripe_event_id": event_id,
                "p_event_type": "checkout.session.completed",
                "p_user_id": user_id,
                "p_checkout_session_id": checkout_session_id,
                "p_payment_intent_id": payment_intent_id,
                "p_starts_at": starts_at.isoformat(),
                "p_expires_at": expires_at.isoformat(),
            },
        )
        if response_status != 200:
            raise RuntimeError("Could not activate Submission Pass access.")
        return bool(payload)
