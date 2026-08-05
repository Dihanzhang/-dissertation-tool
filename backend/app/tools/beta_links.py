"""Local admin utility for private beta links. Never exposed over HTTP.

Run from the backend/ directory with the service-role key available in .env:

    python -m app.tools.beta_links create --label tester-a
    python -m app.tools.beta_links list
    python -m app.tools.beta_links revoke --id <link id>

`create` prints the private URL once. It cannot be recovered afterwards,
because only its hash is stored.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

from ..config import Settings
from ..services.beta_links import beta_link_expiry, generate_beta_token, hash_beta_token
from ..services.supabase import SupabasePassRepository


def _repository(settings: Settings) -> SupabasePassRepository:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env first.")
    return SupabasePassRepository(settings.supabase_url, settings.supabase_service_role_key)


async def _create(settings: Settings, label: str | None, site_url: str) -> None:
    token = generate_beta_token()
    now = datetime.now(UTC)
    link = await _repository(settings).create_beta_access_link(
        token_hash=hash_beta_token(token),
        expires_at=beta_link_expiry(now),
        label=label,
    )
    print("Private beta link (shown once — copy it now, it is not recoverable):")
    print(f"  {site_url.rstrip('/')}/beta/{token}")
    print()
    print(f"  link id:    {link['id']}        (use this to revoke)")
    print(f"  label:      {link.get('label') or '-'}")
    print(f"  expires at: {link['expires_at']}")
    print()
    print("Send it privately. Do not paste it into email drafts you keep, tickets, or chat history.")


async def _list(settings: Settings) -> None:
    links = await _repository(settings).list_beta_access_links()
    if not links:
        print("No beta links yet.")
        return
    print(f"{'link id':38} {'status':8} {'label':16} expires at")
    for link in links:
        print(
            f"{link['id']:38} {link['status']:8} {(link.get('label') or '-'):16} {link['expires_at']}"
        )


async def _revoke(settings: Settings, link_id: str) -> None:
    revoked = await _repository(settings).revoke_beta_access_link(
        link_id=link_id, at=datetime.now(UTC)
    )
    print(f"Revoked {link_id}." if revoked else f"No beta link found with id {link_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage private beta access links.")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a link and print it once.")
    create.add_argument("--label", help="Short non-identifying note, e.g. tester-a. No email addresses.")
    create.add_argument("--site", help="Public site URL. Defaults to SITE_URL from the environment.")

    commands.add_parser("list", help="List links without revealing any secret.")

    revoke = commands.add_parser("revoke", help="Revoke a link immediately.")
    revoke.add_argument("--id", required=True, help="The link id shown by create or list.")

    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "create":
        if args.label and "@" in args.label:
            raise SystemExit("Labels must not contain email addresses.")
        asyncio.run(_create(settings, args.label, args.site or settings.site_url))
    elif args.command == "list":
        asyncio.run(_list(settings))
    else:
        asyncio.run(_revoke(settings, args.id))


if __name__ == "__main__":
    main()
