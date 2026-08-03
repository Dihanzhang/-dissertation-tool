# Submission Pass launch design

## Goal

Turn the Dissertation APA 7 Review Assistant into a trustworthy, paid product
that can be promoted through a shareable landing page and paid social ads.

## Product definition

The public landing page explains the service, demonstrates its output, and
converts visitors to the paid product. It does not offer a live trial or any
free new checks.

The paid product is the **Submission Pass**:

- AU$14.95, paid once per pass.
- Active for 30 calendar days from successful payment.
- Covers unlimited normal personal rechecks of one student's own dissertation
  work, including APA checks and AI-powered review/rechecks.
- Each request remains subject to documented document-size and rate limits.
- It is not a bulk-processing, editing-service, resale, or multi-user licence.

When a pass expires, both new APA checks and AI reviews lock. Previously
delivered results remain visible, and the account presents a clear
purchase-again action.

## Customer journey

1. A visitor arrives from a social post, ad, or shared link.
2. The landing page explains the scope, demonstrates annotated output, and
   makes the Submission Pass offer clear.
3. A visitor starts checkout and creates or signs into an account as part of
   the purchase flow.
4. Stripe Checkout collects payment and supplies the receipt.
5. A verified Stripe webhook creates or extends the 30-day pass.
6. The customer returns to a success page and can immediately review and
   recheck their document.
7. The account displays pass status and expiry. Expired users see an honest
   repurchase path.

Checkout success-page parameters never grant access on their own. The backend
only grants a pass after it validates a Stripe webhook event.

## Architecture

### Frontend

Add a launch-ready landing page with a single primary call to action, product
explanation, annotated-output sample, a short how-it-works walkthrough,
pricing, privacy and academic-integrity trust content, FAQ, and Open Graph
metadata/image for social sharing. Add account, checkout-return, and
billing-status views.

The landing page also includes a calm "Share your experience" feedback form:
an optional name, optional contact detail for a requested reply, and a required
message box. It explains that contact information is only used to respond when
provided, confirms successful submission in place, and does not interrupt the
purchase flow. Include a hidden honeypot field, server-side validation, and
rate limiting to reduce spam.

The review UI reads a server-provided entitlement state before allowing a new
APA or AI review request. It explains whether the account has an active or
expired pass without exposing payment implementation details.

### Backend

Replace the in-memory credit model with durable records for users, Submission
Passes, and payment/webhook events. Use Stripe-hosted Checkout for the fixed
price. Add authenticated endpoints to create a checkout session, report
entitlement state, receive Stripe webhooks, and accept rate-limited public
feedback submissions.

Webhook processing must validate Stripe signatures and be idempotent. A
processed-event record prevents duplicated passes when Stripe retries an event.
Every review request checks the active pass at the server before calling the
AI provider.

### Data model

- `users`: stable account identifier and verified email.
- `submission_passes`: user, Stripe payment/session references, start/end
  times, status, and audit timestamps.
- `payment_events`: Stripe event ID, type, verification/processing status, and
  processed timestamp for idempotency.
- `access_audit`: minimal non-document-content record of significant access
  decisions and failures for support and abuse investigation.
- `feedback`: optional name/contact, message, submission time, and minimal
  delivery/status fields. It never contains uploaded document text.

Document text is not stored in these records.

## Operational and trust requirements

- Use a managed production database, provider secret management, and HTTPS.
- Validate uploaded DOCX files and enforce documented size/request limits.
- Rate-limit account and upload endpoints; do not rely on client-side limits.
- Rate-limit and validate public feedback submissions; clearly state how
  feedback/contact details are handled in the Privacy Policy.
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
- Include a visible "Need help with your pass?" link in purchase and account
  views. It scrolls to the landing-page message form, where users can provide
  an optional contact detail for a reply.

## Analytics and marketing

Record privacy-conscious funnel events: landing-page view, checkout started,
purchase confirmed, first review, and pass expiry. Do not automate follows,
DMs, comments, scraping, fake engagement, or bulk social activity.

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
- Feedback validation/submission failure: retain no partial message, preserve
  the visitor's typed text in the form, and provide a clear retry message.

## Verification and launch gates

1. Unit tests cover active/expired entitlement checks, checkout-session
   authorisation, webhook signature failure, and idempotent webhook retries.
2. Integration tests exercise Stripe test-mode purchase, cancellation, delayed
   webhook, and pass expiry.
3. Frontend tests cover each account state and the purchase/renewal paywall.
4. Frontend and API tests cover feedback validation, honeypot rejection, rate
   limits, successful confirmation, and failure recovery.
5. Render the landing page at mobile and desktop sizes; inspect social preview
   metadata and image.
6. Test one complete production-like purchase with Stripe test credentials,
   receipt email, access grant, review, expiry handling, and repurchase.
7. Complete a privacy/security and copy review before enabling live Stripe
   payments or paid ads.

## Explicit non-goals for this release

- Subscription plans, recurring billing, coupons, affiliates, teams, and
  institutional licensing.
- Automated social posting or engagement.
- A promise that every APA issue is detected or that use changes academic
  outcomes.
