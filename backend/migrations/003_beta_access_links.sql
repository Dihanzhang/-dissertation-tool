-- Invite-only beta access by private link.
--
-- Each tester gets one unique URL containing a 32-byte random secret. Only the
-- SHA-256 hash of that secret is stored here, so the database never holds a
-- value that could be used to sign in. Testers are identified by subject_id,
-- never by email address.

create table public.beta_access_links (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null unique default gen_random_uuid(),
  token_hash text not null unique,
  label text check (label is null or label !~ '@'),
  status text not null default 'active' check (status in ('active', 'revoked', 'expired')),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create index beta_access_links_active_idx
  on public.beta_access_links (token_hash)
  where status = 'active';

-- Only the backend may read these rows, and only with the service-role key.
-- A browser must never be able to enumerate or read them.
alter table public.beta_access_links enable row level security;

revoke all on table public.beta_access_links from public, anon, authenticated;
grant all on table public.beta_access_links to service_role;
