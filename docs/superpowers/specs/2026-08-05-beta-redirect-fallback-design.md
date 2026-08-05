# Beta Redirect Fallback Design

## Goal

Ensure an invited beta member who returns from a Supabase sign-in email to the landing page is sent to the beta activation flow instead of seeing the paid offer.

## Decision

The landing page will only redirect to `/beta` when both conditions are true:

1. The URL hash contains a Supabase `access_token`.
2. The browser has the `beta-redemption-pending` marker set by the beta sign-in form.

All other magic-link sign-ins continue to redirect to `/account`, and ordinary landing-page visitors do not redirect anywhere.

## Data flow

1. An invited person opens `/beta` and requests a sign-in email.
2. The beta form stores `beta-redemption-pending` in local storage.
3. Supabase may return the email link to the site root because its redirect allow-list does not yet include `/beta`.
4. The landing page detects the pending beta marker and token hash, then redirects to `/beta` while preserving the hash.
5. The beta page redeems the email-bound invitation and opens `/review`.

## Safety and testing

The change is client-side only. It does not create passes, alter payment logic, or affect users without the beta marker. A focused source-level regression test will assert the beta route and the normal account route are both present.
