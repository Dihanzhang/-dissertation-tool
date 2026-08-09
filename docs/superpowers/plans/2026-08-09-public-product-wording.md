# Public Product Wording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update public frontend wording so the product clearly serves essays, research papers, and dissertations without changing its behaviour.

**Architecture:** Keep the existing Next.js pages, routes, components, and interactions intact. Add source-level copy assertions, then replace only public string literals in the root metadata and existing frontend pages.

**Tech Stack:** Next.js 16, React 19, TypeScript, Node.js test runner, ESLint

## Global Constraints

- Use **APA 7 Review Tool** as the public product name.
- Identify essays, research papers, and dissertations as supported document types.
- Address students, researchers, and educators only where an audience description is useful.
- Preserve the deterministic, rule-based and no-large-language-model explanation.
- Do not modify internal filenames, identifiers, component names, repository structure, APIs, routes, URLs, pricing, access rules, authentication, storage, checking logic, document annotation, downloads, features, or behaviour.
- Change styling only if text length creates a visible copy problem.

---

### Task 1: Lock the Inclusive Public Positioning in Tests

**Files:**
- Modify: `frontend/tests/deterministic-review-copy.test.mjs`

**Interfaces:**
- Consumes: public string literals in `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/account/page.tsx`, `frontend/app/beta/page.tsx`, and `frontend/app/review/page.tsx`
- Produces: source-level regression assertions for inclusive branding and deterministic-review wording

- [ ] **Step 1: Extend the copy test with the exact public contract**

Add readers for the layout, account, and beta page sources. Assert that the combined public frontend source contains `APA 7 Review Tool`, `essay, research paper or dissertation`, `deterministic, rule-based`, and `No large language model generates the review results`. Assert that it does not contain `Dissertation Review`, `Dissertation APA 7 Review Assistant`, or `APA 7 dissertation review`.

```js
const layout = () => readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
const account = () => readFile(new URL("../app/account/page.tsx", import.meta.url), "utf8");
const beta = () => readFile(new URL("../app/beta/page.tsx", import.meta.url), "utf8");

test("public product wording includes essays, research papers, and dissertations", async () => {
  const sources = await Promise.all([landing(), layout(), review(), account(), beta()]);
  const publicCopy = sources.join("\n");

  assert.match(publicCopy, /APA 7 Review Tool/);
  assert.match(publicCopy, /essay, research paper or dissertation/i);
  assert.match(publicCopy, /deterministic, rule-based/i);
  assert.match(publicCopy, /No large language model generates the review results/);
  assert.doesNotMatch(publicCopy, /Dissertation Review|Dissertation APA 7 Review Assistant|APA 7 dissertation review/i);
});
```

- [ ] **Step 2: Run the focused test and verify the new contract fails**

Run: `npm test -- --test-name-pattern="public product wording"`

Working directory: `frontend`

Expected: FAIL because the current metadata and navigation still use dissertation-only branding and the homepage does not name all three document types.

- [ ] **Step 3: Commit the failing copy contract**

```bash
git add frontend/tests/deterministic-review-copy.test.mjs
git commit -m "test: define inclusive APA tool wording"
```

### Task 2: Update Public String Literals Only

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/account/page.tsx`
- Modify: `frontend/app/beta/page.tsx`
- Modify: `frontend/app/review/page.tsx`
- Test: `frontend/tests/deterministic-review-copy.test.mjs`

**Interfaces:**
- Consumes: the copy contract introduced in Task 1
- Produces: inclusive product wording in page metadata, homepage positioning, navigation labels, and the review-feedback email subject

- [ ] **Step 1: Replace the root metadata strings**

In `frontend/app/layout.tsx`, set:

```ts
title: "APA 7 Review Tool",
description: "Rule-based APA 7 checks for essays, research papers and dissertations.",
```

- [ ] **Step 2: Update the homepage positioning**

In `frontend/app/page.tsx`, replace the dissertation-only eyebrow and supporting paragraph with:

```tsx
<p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-blue-700">APA 7 Review Tool</p>
<h1 className="text-3xl font-bold tracking-tight sm:text-4xl">A careful review before you submit.</h1>
<p className="mx-auto mt-4 max-w-2xl leading-7 text-slate-600">
  If you’re writing an essay, research paper or dissertation, check APA 7 alignment, citations, references and writing rules through deterministic, rule-based checks, then decide what to change.
</p>
```

Keep the existing pricing, pass details, calls to action, layout, classes, and event handling unchanged.

- [ ] **Step 3: Update dissertation-only navigation labels**

In `frontend/app/account/page.tsx` and `frontend/app/beta/page.tsx`, replace only the visible link label `Dissertation Review` with `APA 7 Review Tool`. Keep each `href`, class name, component, and surrounding logic unchanged.

- [ ] **Step 4: Update the feedback-email subject**

In `frontend/app/review/page.tsx`, replace:

```ts
`Dissertation Review beta feedback - ${BETA_VERSION}`
```

with:

```ts
`APA 7 Review Tool beta feedback - ${BETA_VERSION}`
```

Do not change the email address, body, feedback template, review logic, upload logic, or download logic.

- [ ] **Step 5: Run the focused copy test**

Run: `npm test -- --test-name-pattern="public product wording|deterministic review results"`

Working directory: `frontend`

Expected: PASS.

- [ ] **Step 6: Review the diff for copy-only scope**

Run: `git diff -- frontend/app frontend/tests/deterministic-review-copy.test.mjs`

Expected: only test assertions and user-visible string literals change; no imports, functions, JSX structure, props, routes, URLs, styles, API calls, or logic change.

- [ ] **Step 7: Commit the public copy update**

```bash
git add frontend/app/layout.tsx frontend/app/page.tsx frontend/app/account/page.tsx frontend/app/beta/page.tsx frontend/app/review/page.tsx
git commit -m "Update public APA tool positioning"
```

### Task 3: Verify and Deploy the Copy-Only Change

**Files:**
- Verify: `frontend/app/layout.tsx`
- Verify: `frontend/app/page.tsx`
- Verify: `frontend/app/account/page.tsx`
- Verify: `frontend/app/beta/page.tsx`
- Verify: `frontend/app/review/page.tsx`
- Verify: `frontend/tests/deterministic-review-copy.test.mjs`

**Interfaces:**
- Consumes: the committed public-copy update from Task 2
- Produces: test, lint, build, diff, and deployment evidence

- [ ] **Step 1: Run the complete frontend test suite**

Run: `npm test`

Working directory: `frontend`

Expected: all tests pass.

- [ ] **Step 2: Run lint**

Run: `npm run lint`

Working directory: `frontend`

Expected: exit code 0 with no errors.

- [ ] **Step 3: Run the production build**

Run: `npm run build`

Working directory: `frontend`

Expected: Next.js completes the production build successfully.

- [ ] **Step 4: Confirm forbidden scope did not change**

Run: `git diff 90e2d1d..HEAD --name-only`

Expected: only the plan, copy test, and five existing frontend page files are listed.

Run: `git diff 90e2d1d..HEAD -- frontend/app | rg "^[+-].*(fetch\(|href=|router\.|API_BASE|function |const [A-Za-z].*=|className=)"`

Expected: no functional, URL, route, API, or styling changes; any reported `const` line is the feedback subject string only.

- [ ] **Step 5: Push the current branch to trigger the existing deployment**

Run: `git push`

Expected: the push succeeds and the existing hosting integration starts a deployment. Do not alter hosting configuration.

- [ ] **Step 6: Verify the deployed homepage**

Open `https://apa7.aithrival.com` after deployment and confirm that the rendered page contains `APA 7 Review Tool` and `essay, research paper or dissertation`, while the purchase and review routes still open normally.
