# Submission Pass Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Ship a paid AU$14.95, 30-day Submission Pass with Stripe checkout, account-bound access, a social-ready landing page, and public experience feedback.

**Architecture:** Keep the Next.js site statically exported to Netlify. Use Supabase Auth in the browser, with FastAPI verifying bearer tokens and using a server-only Supabase service-role key for pass, payment-event, access-audit, and feedback records. Stripe Checkout is the payment surface; a verified Stripe webhook is the sole authority that grants or extends a pass.

**Tech Stack:** Next.js 16 static export, React 19, FastAPI, Supabase Auth/Postgres, Stripe Checkout/webhooks, PyJWT/JWKS, slowapi, pytest, Vitest, Netlify, Render.

## Global Constraints

- Price is exactly \`AUD 14.95\` for one 30-day Submission Pass; no subscriptions, coupons, or recurring billing.
- There is no live trial and no free new check. An active pass is required for every new APA check, annotated DOCX export, and AI review.
- A pass covers normal personal use on one student's own dissertation work; document-size and request-rate limits are enforced server-side.
- Never grant access from a checkout success URL; grant it only from a verified, idempotently processed Stripe webhook.
- Do not persist dissertation text, uploaded DOCX bytes, AI prompts, or AI outputs in the database, logs, audit rows, or feedback rows.
- The landing page must avoid grade guarantees, complete-APA guarantees, supervisor-replacement claims, and institutional-affiliation claims.
- Keep Stripe/Supabase/LLM secrets in backend-only environment variables; no secret appears in Git or the frontend bundle.

## Planned file structure

- \`backend/app/config.py\`: production configuration validation.
- \`backend/app/auth.py\`: Supabase bearer-token verification and \`CurrentUser\`.
- \`backend/app/services/access.py\`: active-pass lookup and minimal access audit.
- \`backend/app/services/billing.py\`: Checkout creation and webhook fulfilment.
- \`backend/app/services/feedback.py\`: feedback validation/storage.
- \`backend/migrations/001_submission_pass.sql\`: pass, payment-event, access-audit, and feedback schema.
- \`backend/tests/test_config.py\`, \`test_access.py\`, \`test_billing.py\`, \`test_feedback.py\`, \`test_api_entitlements.py\`: focused tests.
- \`frontend/lib/supabase.ts\`, \`frontend/lib/api.ts\`: browser auth/API clients.
- \`frontend/components/AuthGate.tsx\`, \`PassStatus.tsx\`, \`FeedbackForm.tsx\`: isolated client UI.
- \`frontend/app/account/page.tsx\`, \`checkout/success/page.tsx\`, \`checkout/cancel/page.tsx\`: purchase/account routes.
- \`frontend/app/privacy/page.tsx\`, \`terms/page.tsx\`, \`refunds/page.tsx\`: approved policy routes.
- \`frontend/public/og-submission-pass.png\`: original 1200×630 social card.

---

### Task 1: Add configuration and the durable pass schema

**Files:**
- Create: \`backend/app/config.py\`
- Create: \`backend/migrations/001_submission_pass.sql\`
- Modify: \`backend/.env.example\`, \`backend/requirements.txt\`
- Test: \`backend/tests/test_config.py\`

**Interfaces:**
- Produces \`Settings.from_env()\` with Supabase, Stripe, site-origin, 30-day, and upload-limit settings.
- Produces tables \`submission_passes\`, \`payment_events\`, \`access_audit\`, and \`feedback\`.

- [ ] **Step 1: Write the failing configuration test**

\`\`\`python
def test_live_stripe_requires_webhook_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_example")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET"):
        Settings.from_env()
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_config.py -v\`

Expected: FAIL because \`Settings\` does not exist.

- [ ] **Step 3: Implement the schema and settings**

\`\`\`sql
create table public.submission_passes (
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  stripe_checkout_session_id text not null unique,
  starts_at timestamptz not null, expires_at timestamptz not null,
  status text not null check (status in ('active','expired','refunded')),
  created_at timestamptz not null default now()
);
create table public.payment_events (
  stripe_event_id text primary key, event_type text not null,
  processed_at timestamptz not null default now()
);
\`\`\`

Set \`PASS_DURATION_DAYS=30\`, \`MAX_UPLOAD_BYTES=10485760\`, and reject live Stripe configuration without a webhook secret and explicit site origin.

- [ ] **Step 4: Verify**

Run: \`python -m pytest backend/tests/test_config.py -v\`

Expected: PASS. Run the migration once in the target Supabase project's SQL editor.

- [ ] **Step 5: Commit**

\`\`\`bash
git add backend/app/config.py backend/migrations/001_submission_pass.sql backend/.env.example backend/requirements.txt backend/tests/test_config.py
git commit -m "feat: add Submission Pass configuration and schema"
\`\`\`

### Task 2: Add account authentication and entitlement state

**Files:**
- Create: \`backend/app/auth.py\`, \`backend/app/services/access.py\`
- Modify: \`backend/app/main.py\`
- Test: \`backend/tests/test_access.py\`

**Interfaces:**
- Consumes: \`Authorization: Bearer <Supabase access token>\`.
- Produces: \`CurrentUser(id, email)\` and \`GET /api/account/entitlement\` returning \`{status: 'active'|'expired'|'none', expires_at: string|null}\`.

- [ ] **Step 1: Write the failing access tests**

\`\`\`python
def test_active_pass_allows_submission(repo, user):
    repo.add_pass(user.id, starts_at=now(), expires_at=now() + timedelta(days=1))
    assert entitlement_for(user, repo).can_submit is True

def test_expired_pass_blocks_submission(repo, user):
    repo.add_pass(user.id, starts_at=now() - timedelta(days=31), expires_at=now())
    assert entitlement_for(user, repo).can_submit is False
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_access.py -v\`

Expected: FAIL because the access service is absent.

- [ ] **Step 3: Implement the minimal secure boundary**

\`\`\`python
async def require_user(authorization: Annotated[str, Header()]) -> CurrentUser: ...
def entitlement_for(user: CurrentUser, repo: PassRepository, at: datetime) -> Entitlement: ...
\`\`\`

Verify JWT signature, issuer, audience, and expiry using Supabase JWKS. Never trust a client \`user_id\`. Query an unexpired active pass and write audit rows containing only user ID, action, decision, and timestamp.

- [ ] **Step 4: Verify**

Run: \`python -m pytest backend/tests/test_access.py backend/tests/test_module1.py -v\`

Expected: PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add backend/app/auth.py backend/app/services/access.py backend/app/main.py backend/tests/test_access.py
git commit -m "feat: add account entitlement checks"
\`\`\`

### Task 3: Add Stripe Checkout and idempotent webhook fulfilment

**Files:**
- Create: \`backend/app/services/billing.py\`
- Modify: \`backend/app/main.py\`, \`backend/requirements.txt\`
- Test: \`backend/tests/test_billing.py\`

**Interfaces:**
- Produces \`POST /api/billing/checkout-session\` for an authenticated user, returning \`{checkout_url: string}\`.
- Produces \`POST /api/billing/webhook\`, accepting Stripe's raw signed body.

- [ ] **Step 1: Write the failing retry test**

\`\`\`python
def test_completed_checkout_creates_one_pass_when_retried(repo, user):
    event = completed_checkout_event("evt_1", "cs_1", user.id)
    fulfil_checkout(event, repo, clock=fixed_clock)
    fulfil_checkout(event, repo, clock=fixed_clock)
    assert repo.pass_count_for(user.id) == 1
    assert repo.event_processed("evt_1") is True
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_billing.py -v\`

Expected: FAIL because checkout fulfilment is absent.

- [ ] **Step 3: Implement payment handling**

\`\`\`python
def create_checkout_session(user, stripe_client, settings):
    return stripe_client.checkout.sessions.create(
        mode="payment",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        client_reference_id=str(user.id),
        customer_email=user.email,
        success_url=f"{settings.site_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.site_url}/checkout/cancel",
    ).url
\`\`\`

Validate signatures with \`stripe.Webhook.construct_event\`. Record the event ID before fulfilment; a duplicate event returns HTTP 200 and grants no second pass. Fulfil only \`checkout.session.completed\`.

- [ ] **Step 4: Verify**

Run: \`python -m pytest backend/tests/test_billing.py -v\`

Expected: PASS. Use Stripe CLI test mode to complete one Checkout and verify one pass and one event row.

- [ ] **Step 5: Commit**

\`\`\`bash
git add backend/app/services/billing.py backend/app/main.py backend/requirements.txt backend/tests/test_billing.py
git commit -m "feat: add Stripe Submission Pass checkout"
\`\`\`

### Task 4: Require a pass for every new check or export

**Files:**
- Modify: \`backend/app/main.py\`, \`backend/.env.example\`
- Delete: \`backend/app/modules/credits.py\`
- Test: \`backend/tests/test_api_entitlements.py\`

**Interfaces:**
- Produces HTTP 402 and \`{"detail":"An active Submission Pass is required to start a new review."}\` for missing/expired access.

- [ ] **Step 1: Write failing endpoint-gate tests**

\`\`\`python
def test_text_check_without_pass_returns_402(client, expired_token):
    response = client.post("/api/check/text", headers=expired_token,
                           json={"body_text": "A complete sentence.", "reference_text": ""})
    assert response.status_code == 402

def test_text_check_with_active_pass_reaches_checker(client, active_token):
    response = client.post("/api/check/text", headers=active_token,
                           json={"body_text": "A complete sentence.", "reference_text": ""})
    assert response.status_code == 200
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_api_entitlements.py -v\`

Expected: FAIL because check endpoints are public.

- [ ] **Step 3: Remove the credit contract and gate before work**

Remove \`user_id\`, \`tier\`, credit balance, and free-trial fields from API models and responses. Require the active-pass dependency at the start of \`/api/check/text\`, \`/api/check/docx\`, \`/api/check/docx/annotated\`, \`/api/review/estimate\`, and \`/api/review\`. Preserve temporary-file cleanup and call the AI provider only after access succeeds.

- [ ] **Step 4: Verify**

Run: \`python -m pytest backend/tests -v\`

Expected: PASS, including existing APA/DOCX regression tests.

- [ ] **Step 5: Commit**

\`\`\`bash
git add backend/app/main.py backend/.env.example backend/tests/test_api_entitlements.py
git rm backend/app/modules/credits.py
git commit -m "feat: require an active Submission Pass for reviews"
\`\`\`

### Task 5: Add spam-resistant public feedback

**Files:**
- Create: \`backend/app/services/feedback.py\`
- Modify: \`backend/app/main.py\`
- Test: \`backend/tests/test_feedback.py\`

**Interfaces:**
- Produces \`POST /api/feedback\` accepting \`{name?: string, contact?: string, message: string, website: string}\`.
- Produces \`201 {"status":"received"}\`, \`400\` for validation/honeypot failure, and \`429\` when rate-limited.

- [ ] **Step 1: Write failing tests**

\`\`\`python
def test_honeypot_feedback_is_rejected(client):
    response = client.post("/api/feedback", json={"message": "Useful review.", "website": "bot"})
    assert response.status_code == 400

def test_valid_feedback_is_stored(client, feedback_repo):
    response = client.post("/api/feedback", json={"name": "Ava", "contact": "",
        "message": "The comments were clear.", "website": ""})
    assert response.status_code == 201
    assert feedback_repo.last().message == "The comments were clear."
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_feedback.py -v\`

Expected: FAIL because the endpoint is absent.

- [ ] **Step 3: Implement strict validation**

Require a trimmed message of 10–2,000 characters; cap name at 120 and contact at 254 characters; reject a non-empty \`website\`; and rate-limit source IP to five submissions/hour. Store only validated form fields/timestamp, return generic success, and never echo content.

- [ ] **Step 4: Verify**

Run: \`python -m pytest backend/tests/test_feedback.py -v\`

Expected: PASS, including a sixth test submission returning HTTP 429.

- [ ] **Step 5: Commit**

\`\`\`bash
git add backend/app/services/feedback.py backend/app/main.py backend/tests/test_feedback.py
git commit -m "feat: collect landing page feedback safely"
\`\`\`

### Task 6: Add browser auth, purchase return, and access-aware review UI

**Files:**
- Create: \`frontend/lib/supabase.ts\`, \`frontend/lib/api.ts\`
- Create: \`frontend/components/AuthGate.tsx\`, \`frontend/components/PassStatus.tsx\`
- Create: \`frontend/app/account/page.tsx\`, \`frontend/app/checkout/success/page.tsx\`, \`frontend/app/checkout/cancel/page.tsx\`
- Modify: \`frontend/app/review/page.tsx\`, \`frontend/package.json\`
- Test: \`frontend/components/PassStatus.test.tsx\`

**Interfaces:**
- Consumes \`NEXT_PUBLIC_SUPABASE_URL\`, \`NEXT_PUBLIC_SUPABASE_ANON_KEY\`, \`NEXT_PUBLIC_API_URL\`.
- Produces \`apiFetch(path, options)\`, attaching the Supabase access token and preserving entered content on HTTP 402.

- [ ] **Step 1: Write the failing component test**

\`\`\`tsx
it("shows purchase action for an expired pass", () => {
  render(<PassStatus entitlement={{ status: "expired", expires_at: null }} />);
  expect(screen.getByRole("link", { name: "Get a Submission Pass" })).toBeVisible();
});
\`\`\`

- [ ] **Step 2: Run it**

Run: \`npm test -- --runInBand frontend/components/PassStatus.test.tsx\`

Expected: FAIL because the test runner/component are absent.

- [ ] **Step 3: Implement only the needed browser surface**

Install \`@supabase/supabase-js\`, Vitest, and Testing Library. Keep authentication in the browser because \`output: "export"\` has no Next.js server runtime. Use magic-link sign-in, call entitlement after session creation, and remove anonymous user IDs, tiers, credits, free-check copy, and all trial logic. A 402 shows a purchase action without discarding typed text.

- [ ] **Step 4: Verify**

Run: \`npm run lint && npm test -- --runInBand && npm run build\`

Expected: PASS and \`frontend/out\` contains account and checkout routes.

- [ ] **Step 5: Commit**

\`\`\`bash
git add frontend/package.json frontend/package-lock.json frontend/lib frontend/components frontend/app/account frontend/app/checkout frontend/app/review/page.tsx
git commit -m "feat: add Submission Pass account flow"
\`\`\`

### Task 7: Build the social-ready paid landing page and feedback form

**Files:**
- Create: \`frontend/components/FeedbackForm.tsx\`
- Create: \`frontend/app/privacy/page.tsx\`, \`frontend/app/terms/page.tsx\`, \`frontend/app/refunds/page.tsx\`
- Create: \`frontend/public/og-submission-pass.png\`
- Modify: \`frontend/app/page.tsx\`, \`frontend/app/layout.tsx\`, \`frontend/app/globals.css\`
- Test: \`frontend/app/page.test.tsx\`, \`frontend/components/FeedbackForm.test.tsx\`

**Interfaces:**
- Consumes \`POST /api/feedback\`.
- Produces primary CTA “Get a Submission Pass” and \`og:image=/og-submission-pass.png\`.

- [ ] **Step 1: Write failing landing/feedback tests**

\`\`\`tsx
it("does not advertise a free trial", () => {
  render(<LandingPage />);
  expect(screen.getByText("Submission Pass")).toBeVisible();
  expect(screen.queryByText(/free/i)).not.toBeInTheDocument();
});

it("confirms an experience message", async () => {
  render(<FeedbackForm />);
  await userEvent.type(screen.getByLabelText("Your experience"),
    "The review comments were easy to act on.");
  await userEvent.click(screen.getByRole("button", { name: "Share feedback" }));
  expect(await screen.findByText("Thank you for sharing your experience.")).toBeVisible();
});
\`\`\`

- [ ] **Step 2: Run it**

Run: \`npm test -- --runInBand frontend/app/page.test.tsx frontend/components/FeedbackForm.test.tsx\`

Expected: FAIL because the page/component are absent.

- [ ] **Step 3: Implement the approved public content**

Use the reviewed-document image as a labelled sample, not customer proof. State AU$14.95 / 30 days, normal-personal-use boundary, checks/limits, user approval of edits, verified privacy behaviour, and no guarantee claims. Add fields “Your name”, “Your contact (optional)”, “Your experience”, and hidden “website”; show a clear in-place success/error state. Link approved Privacy, Terms, Refunds, and support routes. Add an original 1200×630 social card with no university logos.

- [ ] **Step 4: Verify**

Run: \`npm run lint && npm test -- --runInBand && npm run build\`

Expected: PASS. Inspect at 390px and 1440px: CTA, sample, feedback controls, footer, no clipped text, and valid social-card dimensions.

- [ ] **Step 5: Commit**

\`\`\`bash
git add frontend/app frontend/components/FeedbackForm.tsx frontend/public/og-submission-pass.png
git commit -m "feat: launch Submission Pass landing page"
\`\`\`

### Task 8: Configure deployment and run the launch gate

**Files:**
- Modify: \`render.yaml\`, \`netlify.toml\`, \`backend/.env.example\`, \`README.md\`
- Create: \`docs/launch-checklist.md\`
- Test: \`backend/tests/test_config.py\`

**Interfaces:**
- Produces documented Netlify public variables, Render private variables, webhook URL \`https://<api-host>/api/billing/webhook\`, and release-owner verification steps.

- [ ] **Step 1: Write the failing production CORS test**

\`\`\`python
def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings.from_env()
\`\`\`

- [ ] **Step 2: Run it**

Run: \`python -m pytest backend/tests/test_config.py::test_production_rejects_wildcard_cors -v\`

Expected: FAIL until production origin validation exists.

- [ ] **Step 3: Make production controls explicit**

Set Render \`TEST_MODE=false\`; require the Netlify production origin in \`CORS_ORIGINS\`; document Stripe test/live settings, Supabase redirect URLs, migration, feedback access through Supabase, and a support inbox. The checklist must include test purchase, webhook retry, expiry, repurchase, invalid DOCX, feedback rate limit, legal-link review, mobile review, social preview, and rollback by disabling the Stripe price/webhook.

- [ ] **Step 4: Run the release gate**

Run: \`python -m pytest backend/tests -v\` and \`npm run lint && npm test -- --runInBand && npm run build\`

Expected: PASS. Then run a deployed Stripe test-mode purchase journey before enabling the live price or buying ads.

- [ ] **Step 5: Commit**

\`\`\`bash
git add render.yaml netlify.toml backend/.env.example README.md docs/launch-checklist.md backend/tests/test_config.py
git commit -m "docs: add Submission Pass launch controls"
\`\`\`

## Plan self-review

- **Spec coverage:** Tasks 1–4 implement durable access, Stripe, idempotency, expiry, and all review gates. Task 5 implements feedback. Tasks 6–7 implement account, landing, social, trust, and feedback UI. Task 8 implements production/launch controls.
- **Scope boundary:** Excludes subscriptions, coupons, teams, affiliates, automated social activity, and unsupported outcome claims.
- **Naming consistency:** The plan consistently uses \`submission_passes\`, \`payment_events\`, \`feedback\`, \`/api/account/entitlement\`, \`/api/billing/checkout-session\`, and \`/api/feedback\`.
- **External authority required:** The owner creates the Stripe product/price and webhook, Supabase project, final legal-policy text, support inbox, and production environment values. The implementation never invents or commits these secrets.
