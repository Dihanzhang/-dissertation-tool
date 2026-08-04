# Button Interactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give all actionable controls a consistent hover, pressed, keyboard-focus, and disabled response.

**Architecture:** Define three reusable CSS utility classes in `frontend/app/globals.css`: a shared interaction base, a blue primary action, and a neutral secondary action. Apply those classes to existing button and button-like link elements without changing application logic, routes, or copy.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4.

## Global Constraints

- Use a 150ms transition, a small hover lift, a small active press, and a visible blue keyboard focus ring.
- Preserve existing blue, green, amber, red, and neutral semantic colours.
- Disabled buttons must not lift and must use a default cursor.
- Do not alter checkout, authentication, review, or feedback behaviour.

---

### Task 1: Add shared button interaction utilities

**Files:**
- Modify: `frontend/app/globals.css`
- Test: `frontend/app/globals.css`

**Interfaces:**
- Produces: `.button-interaction`, `.button-primary`, and `.button-secondary` CSS classes for all page components.

- [ ] **Step 1: Write the failing style contract check**

Run this command before editing CSS:

```powershell
rg -n "button-interaction|focus-visible:ring-2|active:translate-y-0" frontend/app/globals.css
```

Expected: no matches, because shared interaction utilities do not yet exist.

- [ ] **Step 2: Add the minimal shared utilities**

Add these classes after the `body` rule:

```css
.button-interaction {
  @apply inline-flex items-center justify-center transition duration-150 ease-out motion-reduce:transform-none hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-default disabled:transform-none disabled:shadow-none;
}

.button-primary {
  @apply button-interaction bg-blue-700 text-white hover:bg-blue-800;
}

.button-secondary {
  @apply button-interaction border border-slate-300 bg-white text-slate-800 hover:border-slate-400 hover:bg-slate-50;
}
```

- [ ] **Step 3: Verify the style contract passes**

Run:

```powershell
rg -n "button-interaction|focus-visible:ring-2|active:translate-y-0" frontend/app/globals.css
```

Expected: all three shared utilities and interaction states are present.

- [ ] **Step 4: Commit the utility layer**

```powershell
git add frontend/app/globals.css
git commit -m "feat: add responsive button interaction utilities"
```

### Task 2: Apply shared classes to product actions

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/account/page.tsx`
- Modify: `frontend/app/checkout/success/page.tsx`
- Modify: `frontend/app/checkout/cancel/page.tsx`
- Modify: `frontend/app/review/page.tsx`
- Test: `frontend` production build

**Interfaces:**
- Consumes: `.button-primary`, `.button-secondary`, and `.button-interaction` from `frontend/app/globals.css`.
- Produces: visually consistent interactive controls across all customer-facing pages.

- [ ] **Step 1: Write the failing adoption check**

Run:

```powershell
rg -n "button-primary|button-secondary|button-interaction" frontend/app -g "*.tsx"
```

Expected: no component usage, because the shared classes have not yet been adopted.

- [ ] **Step 2: Apply the classes without changing behaviour**

Replace existing blue action styles with `button-primary` plus their existing spacing and shape classes. Replace outline/white secondary styles with `button-secondary` plus their existing spacing and shape classes. For green, amber, red, and dark review actions, keep their existing colour classes and add `button-interaction`.

Examples:

```tsx
<Link href="/account" className="button-primary rounded-lg px-6 py-3 font-semibold">
  Get Submission Pass — AU$14.95
</Link>

<button disabled={sending} className="button-primary rounded-md px-5 py-3 font-semibold disabled:opacity-60">
  {sending ? "Sending…" : "Email me a sign-in link"}
</button>

<button onClick={() => onDecide("accepted")} className="button-interaction rounded bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700">
  Accept
</button>
```

- [ ] **Step 3: Verify shared-class adoption**

Run:

```powershell
rg -n "button-primary|button-secondary|button-interaction" frontend/app -g "*.tsx"
```

Expected: landing, account, checkout, and review pages each use at least one shared class.

- [ ] **Step 4: Run the production build**

Run:

```powershell
npm run build
```

Expected: exit code 0 and generated routes include `/`, `/account`, `/checkout/success`, `/checkout/cancel`, and `/review`.

- [ ] **Step 5: Commit the component adoption**

```powershell
git add frontend/app/page.tsx frontend/app/account/page.tsx frontend/app/checkout/success/page.tsx frontend/app/checkout/cancel/page.tsx frontend/app/review/page.tsx
git commit -m "feat: add responsive button states across product pages"
```

### Task 3: Verify deployed interaction states

**Files:**
- Test: `https://dissertation-tool.netlify.app/`
- Test: `https://dissertation-tool.netlify.app/account`
- Test: `https://dissertation-tool.netlify.app/checkout/success`
- Test: `https://dissertation-tool.netlify.app/review`

**Interfaces:**
- Consumes: deployed frontend from Tasks 1 and 2.
- Produces: evidence that buttons have working hover, press, focus, and disabled states.

- [ ] **Step 1: Check an enabled primary button**

On the landing page, hover over “Get Submission Pass — AU$14.95”, press and hold it, then release without navigating. Confirm it lifts on hover and compresses on press.

- [ ] **Step 2: Check a secondary button**

Hover over “How it works”. Confirm its border and background change, with the same lift and press response.

- [ ] **Step 3: Check keyboard focus and disabled state**

Use Tab to focus a primary action and confirm the blue focus ring. On the account page, submit a sign-in request and confirm the temporarily disabled button does not lift or show a pointer cursor.

- [ ] **Step 4: Commit only if verification required a corrective code change**

If no corrective change is needed, do not create another commit.
