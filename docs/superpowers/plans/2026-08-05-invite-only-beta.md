# Invite-only beta access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give invited beta members a free 30-day Submission Pass without publishing a public free offer or weakening the paid Stripe flow.

**Architecture:** A public `/beta` page only starts passwordless email sign-in. Once the member is authenticated, the frontend calls a protected server endpoint. That endpoint uses a service-role-only Supabase function to atomically redeem one active email-bound invitation and create a normal active Submission Pass. The review page checks entitlement before offering an upload.

**Tech Stack:** Next.js App Router and TypeScript frontend; FastAPI backend; Supabase Auth/Postgres/RLS; Stripe Checkout (unchanged); pytest and Next production build.

## Global Constraints

- Do not add a public free-check route, discount code, or client-side invitation list.
- The initial recipient email is entered directly in Supabase after deployment, never committed to source control.
- A forwarded `/beta` link grants nothing: the signed-in email must match an unused active invitation.
- Paid Stripe checkout, webhook fulfilment, and current paid account screen must continue to work unchanged.
- Keep the existing 30-day product language. Beta access is an internal entitlement, not a Stripe payment.

---

## 1. Add a secure invitation and redemption migration

**Files:**
- Create: `backend/migrations/002_beta_invites.sql`
- Test: `backend/tests/test_submission_pass_migration.py`

- [ ] Create `public.beta_invites` with a unique normalised email, a positive `duration_days`, an invitation status, optional invitation expiry, redemption user/timestamp fields, and audit timestamps.
- [ ] Enable RLS and revoke browser access. Only `service_role` may use the table or redemption function.
- [ ] Create `public.redeem_beta_invite(p_user_id uuid, p_email text, p_now timestamptz)` as `security definer`. It must lock the matching invitation with `FOR UPDATE`, only accept an active non-expired invitation, mark it redeemed, and insert exactly one active pass.
- [ ] Use an internal unique reference in the form `beta:` followed by the invite UUID in the existing required `submission_passes.stripe_checkout_session_id` field. Leave `stripe_payment_intent_id` null. This preserves the existing table contract without fabricating a Stripe transaction.
- [ ] Return a small JSON object from the function so the API can distinguish an accepted redemption from a non-invited, expired, revoked, or already-redeemed request.

Example function shape:

```sql
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
  set status = 'redeemed', redeemed_by_user_id = p_user_id, redeemed_at = p_now
  where id = invite.id;

  insert into public.submission_passes (
    user_id, stripe_checkout_session_id, starts_at, expires_at, status
  ) values (
    p_user_id, 'beta:' || invite.id::text, p_now, pass_expires_at, 'active'
  );

  return jsonb_build_object('redeemed', true, 'expires_at', pass_expires_at);
end;
$$;
```

- [ ] Extend the migration test to assert the new table has RLS, the function locks rows, and public/authenticated roles are denied while `service_role` is granted access.
- [ ] Run: `pytest backend/tests/test_submission_pass_migration.py -q`

## 2. Add backend redemption service and API endpoint

**Files:**
- Modify: `backend/app/services/access.py`
- Modify: `backend/app/services/supabase.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_access.py`
- Test: `backend/tests/test_account_api.py`
- Test: `backend/tests/test_supabase_repository.py`

- [ ] Add a small typed `BetaRedemption` result with `redeemed: bool` and `expires_at: datetime | None`.
- [ ] Extend the repository interface with an async `redeem_beta_invite(user_id, email, now)` operation. Normalise the email before calling Supabase.
- [ ] Implement the operation in `SupabasePassRepository` by POSTing to `/rest/v1/rpc/redeem_beta_invite` with the existing service-role headers. Parse the returned JSON into `BetaRedemption`.
- [ ] Add `POST /api/beta/redeem` in `backend/app/main.py`. It must use the existing `get_current_user` dependency, call the repository, return the pass expiry on success, and return HTTP 403 with a clear invitation-only message when no invitation is redeemable.
- [ ] Do not accept an email address in the endpoint request body: the verified Supabase user email is the sole identity source.
- [ ] Add focused tests for a valid redemption, a non-invited user, an expired/revoked/already-redeemed result, and service-role RPC parsing.

Endpoint contract:

```python
@app.post("/api/beta/redeem")
async def redeem_beta_invitation(
    user: CurrentUser = Depends(get_current_user),
    repository: PassRepository = Depends(_pass_repository),
) -> BetaRedemptionResponse:
    redemption = await repository.redeem_beta_invite(
        user_id=user.id,
        email=user.email,
        now=datetime.now(timezone.utc),
    )
    if not redemption.redeemed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email does not have an active beta invitation.",
        )
    return BetaRedemptionResponse(expires_at=redemption.expires_at)
```

- [ ] Run: `pytest backend/tests/test_access.py backend/tests/test_account_api.py backend/tests/test_supabase_repository.py -q`

## 3. Build the invitation-only beta page

**Files:**
- Create: `frontend/app/beta/page.tsx`
- Modify: `frontend/app/account/page.tsx` only if shared sign-in token utilities need to be extracted
- Modify: `frontend/app/globals.css` only for styles used by the beta page

- [ ] Follow the project’s existing Supabase client and token-storage pattern; do not introduce a second authentication system.
- [ ] Create `/beta` with a concise explanation: private beta access is available only to invited members, and the recipient must sign in with the invited email.
- [ ] On email submission, call Supabase `signInWithOtp` and visibly change the button/message to confirm that the sign-in email was requested. Preserve the earlier improved feedback behaviour.
- [ ] After the magic link returns to `/beta`, capture the access token using the same hash/token approach as `/account`, store it in the existing `submission-pass-token` storage key, then call `POST /api/beta/redeem` with an `Authorization: Bearer` header containing that token.
- [ ] On success, show a brief confirmation and send the member to `/review`.
- [ ] On an unmatched or invalid invitation, show: “This email does not have an active beta invitation. Please use the email that received the invitation or contact support.” Do not expose invitation records or whether another email is invited.
- [ ] Configure Supabase Authentication redirect URLs to allow `https://apa7.aithrival.com/beta` before testing live magic links. Retain the existing `/account` URL for paid sign-in.

## 4. Prevent unauthorised review uploads in the frontend

**Files:**
- Modify: `frontend/app/review/page.tsx`
- Test: add or extend the project’s existing frontend test setup if present; otherwise verify through the production build and live flow.

- [ ] On page load, require a stored sign-in token and request `/api/account/entitlement` before displaying the review upload controls.
- [ ] If the visitor is signed out or has no active pass, redirect them to `/account`; the server-side checks remain the source of truth.
- [ ] While checking access, render a small “Checking your access…” state instead of a functional-looking upload form.
- [ ] Keep request-time auth headers and backend 402 protection intact for defence in depth.

## 5. Verify the complete application locally

**Files:**
- Review: all files changed above

- [ ] Run focused backend tests:

```powershell
pytest backend/tests/test_access.py backend/tests/test_account_api.py backend/tests/test_supabase_repository.py backend/tests/test_submission_pass_migration.py -q
```

- [ ] Run the frontend production build:

```powershell
Set-Location frontend
npm run build
```

- [ ] Inspect `git diff --check` and the final diff to ensure no credentials, recipient email, or unrelated files are included.
- [ ] Commit the implementation in focused commits: migration, backend, frontend, and documentation/configuration notes as appropriate.

## 6. Deploy and create the first invitation

**External steps after the code is merged and Netlify deploys:**

- [ ] Run `backend/migrations/002_beta_invites.sql` in the Supabase SQL editor.
- [ ] Add the first invite directly in Supabase, outside source control:

```sql
insert into public.beta_invites (email, duration_days, status)
values ('the-invited-email@example.edu', 30, 'active');
```

- [ ] In Supabase Authentication → URL Configuration, add `https://apa7.aithrival.com/beta` to Redirect URLs.
- [ ] Send the private link `https://apa7.aithrival.com/beta` to the invited member.
- [ ] Test the invited member’s flow: request email → click newest magic link promptly → beta redemption → review page → run a harmless check.
- [ ] Test a different email: it must receive no beta entitlement and must see the invitation-only message.
- [ ] Test the public paid flow once more: sign in → `/account` → Stripe checkout → entitlement, without creating another real payment in live mode.
