from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str


@dataclass(frozen=True)
class Entitlement:
    can_submit: bool
    status: str
    expires_at: datetime | None


class PassRepository(Protocol):
    def find_active_pass(self, user_id: str, at: datetime) -> dict | None: ...

    async def find_active_beta_link(self, token_hash: str, at: datetime) -> dict | None: ...


def entitlement_for(user: CurrentUser, repo: PassRepository, at: datetime) -> Entitlement:
    active_pass = repo.find_active_pass(user.id, at)
    if active_pass is None:
        return Entitlement(can_submit=False, status="none", expires_at=None)
    return Entitlement(can_submit=True, status="active", expires_at=active_pass["expires_at"])
