# Submission Pass launch design

## Goal

Turn the Dissertation APA 7 Review Assistant into a trustworthy, paid product
that can be promoted through a shareable landing page and paid social ads.

## Product definition

The public landing page explains the service, offers one APA-only trial, and
converts eligible visitors to the paid product.

The paid product is the **Submission Pass**:

- AU$14.95, paid once per pass.
- Active for 30 calendar days from successful payment.
- Covers unlimited normal personal rechecks of one student's own dissertation
  work, including APA checks and AI-powered review/rechecks.
- Each request remains subject to documented document-size and rate limits.
- It is not a bulk-processing, editing-service, resale, or multi-user licence.

The free APA check is available once per account. When a pass expires, both
new APA checks and AI reviews lock. Previously delivered results remain
visible, and the account presents a clear purchase-again action. A new pass
does not restore a free trial.

## Customer journey

1. A visitor arrives from a social post, ad, or shared link.
2. The landing page explains the scope, demonstrates output, and offers one
   APA-only trial.
3. A visitor creates or signs into an account to use the trial.
4. A trial user reaches a transparent paywall offering the Submission Pass.
5. Stripe Checkout collects payment and supplies the receipt.
6. A verified Stripe webhook creates or extends the 30-day pass.
7. The customer returns to a success page and can immediately review and
   recheck their document.
8. The account displays pass status and expiry. Expired users see an honest
   repurchase path.

Checkout success-page parameters never grant access on their own. The backend
only grants a pass after it validates a Stripe webhook event.

## Architecture

### Frontend

Add a launch-ready landing page with a single primary call to action, a product
explanation, annotated-output sample, pricing, privacy and academic-integrity
trust content, FAQ, and Open Graph metadata/image for social sharing. Add
account, checkout-return, and billing-status views.

The review UI reads a server-provided entitlement state before allowing a new
APA or AI review request. It explains whether the account has a trial,
active pass, or expired pass without exposing payment implementation details.

### Backend

Replace the in-memory credit model with durable records for users, trial use,
Submission Passes, and payment/webhook events. Use Stripe-hosted Checkout for
the fixed price. Add authenticated endpoints to create a checkout session,
report entitlement state, and receive Stripe webhooks.

Webhook processing must validate Stripe signatures and be idempotent. A
processed-event record prevents duplicated passes when Stripe retries an event.
Every review request checks the active pass at the server before calling the
AI provider.

### Data model

- `users`: stable account identifier and verified email.
- `trial_uses`: one APA-only trial per user, with completion timestamp.
- `submission_passes`: user, Stripe payment/session references, start/end
  times, status, and audit timestamps.
- `payment_events`: Stripe event ID, type, verification/processing status, and
  processed timestamp for idempotency.
- `access_audit`: minimal non-document-content record of significant access
  decisions and failures for support and abuse investigation.

Document text is not stored in these records.

## Operational and trust requirements

- Use a managed production database, provider secret management, and HTTPS.
- Validate uploaded DOCX files and enforce documented size/request limits.
- Rate-limit account and upload endpoints; do not rely on client-side limits.
- Publish Privacy Policy, Terms of Use, Refund Policy, and a contact/support
  path before checkout is enabled.
- State accurately how uploads, outputs, account data, and payment data are
  handled and retained. Do not claim deletion until the production behaviour
  verifies it.
- State that the tool is a second pair of eyes, not a grade guarantee, a
  supervisor substitute, or institutional endorsement. Users approve all
  suggested edits.
- Send transactional purchase and expiry emails, and offer a recovery path for
  interrupted checkout or lost device access.

## Analytics and marketing

Record privacy-conscious funnel events: landing-page view, trial started,
trial completed, checkout started, purchase confirmed, first paid review, and
pass expiry. Do not automate follows, DMs, comments, scraping, fake
engagement, or bulk social activity.

Ads and landing-page copy must not claim guaranteed APA compliance, grade
improvement, or affiliation with a university. Pilot the offer with a small
group before scaling paid acquisition, using conversion and support evidence
to validate the price and product wording.

## Error handling

- Payment cancelled or incomplete: retain no entitlement; explain how to retry.
- Webhook delayed: show pending confirmation and poll entitlement state;
  support can reconcile using a payment reference.
- Duplicate/retried webhook: acknowledge safely without issuing another pass.
- Expired/absent pass: block new checks before provider calls and show the
  repurchase action.
- Invalid/oversized upload or rate limit: give a precise, actionable message;
  do not charge a pass for a rejected request.
- Provider failure: do not consume access unfairly; record the event without
  persisting dissertation content.

## Verification and launch gates

1. Unit tests cover trial enforcement, active/expired entitlement checks,
   checkout-session authorisation, webhook signature failure, and idempotent
   webhook retries.
2. Integration tests exercise Stripe test-mode purchase, cancellation, delayed
   webhook, and pass expiry.
3. Frontend tests cover each account state and paid/free paywalls.
4. Render the landing page at mobile and desktop sizes; inspect social preview
   metadata and image.
5. Test one complete production-like purchase with Stripe test credentials,
   receipt email, access grant, review, expiry handling, and repurchase.
6. Complete a privacy/security and copy review before enabling live Stripe
   payments or paid ads.

## Explicit non-goals for this release

- Subscription plans, recurring billing, coupons, affiliates, teams, and
  institutional licensing.
- Automated social posting or engagement.
- A promise that every APA issue is detected or that use changes academic
  outcomes.
