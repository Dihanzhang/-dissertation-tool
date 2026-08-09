# Public Product Wording Alignment

## Goal

Present the product as an APA 7 review tool for essays, research papers, and dissertations rather than as a dissertation-only tool.

## Scope

Update public-facing text in the frontend, including page metadata, homepage positioning, navigation labels, and the feedback-email subject shown or generated through the review page.

The revised copy will:

- use **APA 7 Review Tool** as the public product name;
- identify essays, research papers, and dissertations as supported document types;
- address students, researchers, and educators where an audience description is useful;
- describe findings as the output of deterministic, rule-based checks;
- state that no large language model generates the review results;
- use neutral terms such as **document**, **paper**, or **writing** outside the explicit audience statement; and
- keep the writer responsible for deciding what to change.

## Explicit Non-Goals

This change will not modify:

- internal filenames, identifiers, component names, or repository structure;
- API routes, request or response formats, or backend code;
- public URLs or application routes;
- pricing, access rules, authentication, storage, or privacy behaviour;
- APA checking logic, document annotation, downloads, or any other feature; or
- layout and styling except where a small text-length adjustment is required to prevent a visible copy problem.

## Implementation Boundary

Only string literals that users or search/social previews can encounter will change. Existing behaviour-focused tests will remain unchanged. A focused copy test will assert the inclusive product name and audience wording and guard against dissertation-only branding in public frontend strings.

## Verification

The change is complete when:

1. Public frontend copy no longer names the product **Dissertation Review** or **Dissertation APA 7 Review Assistant**.
2. The homepage clearly says the tool is for essays, research papers, and dissertations.
3. The deterministic, rule-based and no-LLM wording remains accurate and visible.
4. The frontend copy tests, full frontend test suite, lint, and production build pass.
5. The final diff contains no functional code, API, route, URL, filename, pricing, or feature changes.
