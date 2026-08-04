create table public.beta_invites (
  id uuid primary key default gen_random_uuid(),
  email text not null unique check (email = lower(trim(email))),
  duration_days integer not null check (duration_days > 0),
  status text not null default 'active' check (status in ('active', 'redeemed', 'revoked')),
  invite_expires_at timestamptz,
  redeemed_by_user_id uuid,
  redeemed_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.beta_invites enable row level security;

revoke all on table public.beta_invites from public, anon, authenticated;
grant all on table public.beta_invites to service_role;

create or replace function public.redeem_beta_invite(
  p_user_id uuid,
  p_email text,
  p_now timestamptz
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  invite public.beta_invites;
  pass_expires_at timestamptz;
begin
  select * into invite
  from public.beta_invites
  where email = lower(trim(p_email))
    and status = 'active'
    and (invite_expires_at is null or invite_expires_at > p_now)
  for update;

  if not found then
    return jsonb_build_object('redeemed', false);
  end if;

  pass_expires_at := p_now + make_interval(days => invite.duration_days);

  update public.beta_invites
  set status = 'redeemed',
      redeemed_by_user_id = p_user_id,
      redeemed_at = p_now
  where id = invite.id;

  insert into public.submission_passes (
    user_id,
    stripe_checkout_session_id,
    starts_at,
    expires_at,
    status
  ) values (
    p_user_id,
    'beta:' || invite.id::text,
    p_now,
    pass_expires_at,
    'active'
  );

  return jsonb_build_object(
    'redeemed', true,
    'expires_at', pass_expires_at
  );
end;
$$;

revoke all on function public.redeem_beta_invite(uuid, text, timestamptz)
from public, anon, authenticated;
grant execute on function public.redeem_beta_invite(uuid, text, timestamptz)
to service_role;
