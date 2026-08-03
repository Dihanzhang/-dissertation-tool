create table public.submission_passes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  stripe_checkout_session_id text not null unique,
  stripe_payment_intent_id text,
  starts_at timestamptz not null,
  expires_at timestamptz not null,
  status text not null check (status in ('active', 'expired', 'refunded')),
  created_at timestamptz not null default now()
);

create index submission_passes_active_idx
  on public.submission_passes (user_id, expires_at)
  where status = 'active';

create table public.payment_events (
  stripe_event_id text primary key,
  event_type text not null,
  processed_at timestamptz not null default now()
);

create table public.access_audit (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  action text not null,
  decision text not null,
  created_at timestamptz not null default now()
);

create table public.feedback (
  id bigint generated always as identity primary key,
  name text,
  contact text,
  message text not null,
  status text not null default 'received',
  created_at timestamptz not null default now()
);
