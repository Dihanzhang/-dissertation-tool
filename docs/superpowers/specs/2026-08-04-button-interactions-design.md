# Button interaction design

## Goal

Make every actionable control feel responsive while keeping the calm, academic visual style of Dissertation Review.

## Scope

Apply one reusable interaction style to primary, secondary, and semantic action buttons across the landing, account, checkout, and review pages.

## Interaction standard

- Hovered enabled buttons show a pointer cursor, a 150ms transition, a small upward movement, and a slightly stronger shadow.
- Pressed buttons move down slightly and tighten their shadow.
- Keyboard navigation shows a clear blue focus ring.
- Disabled buttons do not move, use a default cursor, and remain visibly muted.
- Existing colours continue to communicate meaning: blue for primary actions, green for acceptance, amber for confirmations, red for removal, and neutral styles for secondary actions.

## Implementation

Create shared utility classes in `frontend/app/globals.css` for primary, secondary, and semantic button states. Replace only existing button and button-like link class strings; do not change copy, routes, payment logic, or form behaviour.

## Verification

- The frontend production build completes successfully.
- The landing, account, checkout success/cancel, and review pages compile with the shared classes.
- Manual visual checks confirm hover, pressed, focus, and disabled states behave as specified.
