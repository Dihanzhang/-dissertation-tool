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

-- These records are only accessed by the backend using Supabase's service-role
-- key. They must never be readable or writable from the browser.
alter table public.submission_passes enable row level security;
alter table public.payment_events enable row level security;
alter table public.access_audit enable row level security;
alter table public.feedback enable row level security;

-- A Stripe event may be delivered more than once. This function records the
-- event and creates the pass in one database transaction, so only the first
-- delivery can create access.
create or replace function public.fulfil_submission_pass(
  p_stripe_event_id text,
  p_event_type text,
  p_user_id uuid,
  p_checkout_session_id text,
  p_payment_intent_id text,
  p_starts_at timestamptz,
  p_expires_at timestamptz
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  event_row_count bigint;
begin
  insert into public.payment_events (stripe_event_id, event_type)
  values (p_stripe_event_id, p_event_type)
  on conflict (stripe_event_id) do nothing;

  get diagnostics event_row_count = row_count;
  if event_row_count = 0 then
    return false;
  end if;

  insert into public.submission_passes (
    user_id,
    stripe_checkout_session_id,
    stripe_payment_intent_id,
    starts_at,
    expires_at,
    status
  ) values (
    p_user_id,
    p_checkout_session_id,
    p_payment_intent_id,
    p_starts_at,
    p_expires_at,
    'active'
  );

  return true;
end;
$$;
