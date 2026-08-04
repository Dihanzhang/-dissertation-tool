from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
from fastapi import HTTPException, status

from .services.access import CurrentUser

UserResponseGetter = Callable[[str, dict[str, str]], Awaitable[tuple[int, dict]]]


async def _get_user(url: str, headers: dict[str, str]) -> tuple[int, dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)
    return response.status_code, response.json() if response.content else {}


class SupabaseAuthenticator:
    def __init__(self, supabase_url: str, anon_key: str, get_user: UserResponseGetter = _get_user):
        self._user_url = f"{supabase_url.rstrip('/')}/auth/v1/user"
        self._anon_key = anon_key
        self._get_user = get_user

    async def verify(self, token: str) -> CurrentUser:
        status_code, payload = await self._get_user(
            self._user_url,
            {"Authorization": f"Bearer {token}", "apikey": self._anon_key},
        )
        if status_code != status.HTTP_200_OK or not payload.get("id") or not payload.get("email"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required.")
        return CurrentUser(id=str(payload["id"]), email=str(payload["email"]))
