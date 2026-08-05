# Beta Redirect Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route an invited beta member from a root-page Supabase magic-link return to `/beta` so their invitation can be redeemed.

**Architecture:** The landing page already detects a Supabase access token in the URL hash. Add one branch that checks the existing browser-only `beta-redemption-pending` marker before choosing the destination. Beta sign-ins go to `/beta`; other sign-ins retain the existing `/account` destination.

**Tech Stack:** Next.js client component, TypeScript, Node built-in test runner, npm lint/build.

## Global Constraints

- Preserve the URL hash when redirecting so the beta page can redeem the Supabase session.
- Do not change Stripe checkout, entitlement logic, or the public landing-page copy.
- Do not redirect when no Supabase access token is present.

---

### Task 1: Add a regression test for the redirect choice

**Files:**
- Create: `frontend/tests/landing-beta-redirect.test.mjs`
- Test: `frontend/tests/landing-beta-redirect.test.mjs`

**Interfaces:**
- Consumes: the source text in `frontend/app/page.tsx`.
- Produces: a regression check that requires both the pending-beta branch and the existing account fallback.

- [ ] **Step 1: Write the failing test**

```js
assert.match(source, /beta-redemption-pending/);
assert.match(source, /window\\.location\\.replace\\(`\\/beta\\$\\{window\\.location\\.hash\\}`\\)/);
assert.match(source, /window\\.location\\.replace\\(`\\/account\\$\\{window\\.location\\.hash\\}`\\)/);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/landing-beta-redirect.test.mjs`

Expected: FAIL because the landing page only redirects to `/account`.

### Task 2: Route pending beta sign-ins to the activation page

**Files:**
- Modify: `frontend/app/page.tsx:10-14`
- Test: `frontend/tests/landing-beta-redirect.test.mjs`

**Interfaces:**
- Consumes: `window.location.hash` and `localStorage.getItem("beta-redemption-pending")`.
- Produces: a redirect to `/beta` for pending beta sessions and `/account` otherwise.

- [ ] **Step 1: Write the minimal implementation**

```ts
if (window.location.hash.includes("access_token=")) {
  const destination = localStorage.getItem("beta-redemption-pending") === "true" ? "/beta" : "/account";
  window.location.replace(`${destination}${window.location.hash}`);
}
```

- [ ] **Step 2: Run the regression test**

Run: `node --test tests/landing-beta-redirect.test.mjs`

Expected: PASS.

- [ ] **Step 3: Run frontend checks**

Run: `npm run lint && npm run build`

Expected: both commands exit successfully.
