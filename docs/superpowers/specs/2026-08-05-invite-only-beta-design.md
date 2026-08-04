# Invite-only beta access

## Goal

Give selected beta members a free, time-limited Submission Pass without publishing a public free offer. Each invitation grants 30 days of access.

## Decision

Use an email-bound invitation, not a secret URL or shared discount code. The public beta page is only the entry point; it grants nothing by itself. A member must sign in using the exact invited email address.

## User flow

1. The organiser sends `https://apa7.aithrival.com/beta` privately to a selected member.
2. The page asks the member to sign in using the email that was invited.
3. After magic-link sign-in, the browser sends the authenticated user to a server-only beta-redemption endpoint.
4. The server atomically matches the normalised email to an unused, active beta invitation and creates one active 30-day Submission Pass for that user.
5. The member is sent to `/review`. A non-invited email sees a clear message and cannot receive access.

## Data and security

Add a `beta_invites` table containing a normalised email, duration in days, invitation status, redemption user id, and timestamps. Row-level security remains enabled with no browser policies.

Add a service-role-only SQL function to redeem an invitation. It must atomically: lock the matching unused invitation, mark it redeemed for the authenticated user, and create the corresponding active Submission Pass. The created pass uses a unique internal beta reference rather than pretending to be a Stripe payment. Paid Stripe fulfilment remains unchanged.

The backend verifies the Supabase token before redemption and passes only the verified user id and email to the database function. There is no browser-accessible endpoint for creating invitations.

The initial invitation is added directly in Supabase after the schema is deployed; the recipient email is not committed to the repository.

## Product behaviour

- `/beta` explains that access is invitation-only and provides the email sign-in action.
- `/review` checks entitlement before showing the upload/check workflow. A signed-out or non-entitled visitor is directed to `/account` instead of seeing an upload form that will later fail.
- `/account` continues to show the paid Submission Pass purchase option for people without a paid or beta pass.
- Existing paid users, Stripe checkout, webhook fulfilment, and 30-day expiry behaviour continue unchanged.

## Errors and expiry

- An email that is not invited receives: “This email does not have a beta invitation. Please use the email that was invited.”
- An invitation already redeemed cannot be transferred to a different account.
- An expired or revoked invitation cannot create a pass.
- A beta pass expires normally after its allocated 30 days; the account page then offers the paid Submission Pass.

## Verification

1. Unit-test the redemption function/repository contract for valid, non-invited, expired, and already-redeemed invitations.
2. Test the redemption API with authenticated and unauthenticated requests.
3. Confirm that an invited user receives an active entitlement and a non-invited user does not.
4. Confirm `/review` redirects a user without entitlement.
5. Run backend tests and the frontend production build.
6. Deploy the migration and application, add the first invitation in Supabase, then test the full magic-link-to-review flow with the invited email.
