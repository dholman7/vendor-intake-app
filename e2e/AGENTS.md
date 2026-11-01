# Writing tests in e2e/

Rules for anyone adding or changing Playwright tests here, human or agent. They come from the shared [playwright-testing standard](https://github.com/dholman7/agent-dev-skills/blob/main/plugins/agent-dev-skills/skills/playwright-testing/SKILL.md); this file says how each one applies in this repo. Rules marked **lint** fail `npm run lint`, which CI runs.

## What's available

Import everything from `../fixtures` (or `../../fixtures` from a subfolder):

| Fixture | Use it for |
|---|---|
| `factory` | Test data through the API: `vendor()`, `upload()`, `vendorWithDocuments()`, `vendorInReview()`, `extraction()`. Every step checks its response. |
| `apiAs(persona)` | An API client signed in as `member`, `reviewer`, `admin`, or `otherTenant` (another company). |
| `signIn(persona)` | Signs the test's own `page` in. |
| `pageAs(persona)` | A second signed-in browser page with its own page objects, for tests where two roles act. |
| `pages` | Page objects for the test's `page`: `shell`, `signIn`, `vendors`, `newVendor`, `vendor`, `reviewQueue`. |
| `a11y` | `seriousViolations(page?)`: WCAG 2.1 AA serious and critical findings. |
| `expectStatus(response, code)` | Asserts a status with the response body in the failure, and returns the parsed body. |

Also exported: `uniqueName`, `sample`, `USERS`, `PASSWORD`, `DOCUMENT_KINDS`, `KIND_LABELS`, and the types.

## Rules

**PW-1. Spec files hold tests only** (lint). No helper functions at file level. Data setup goes in `fixtures/factory.ts`; UI steps go in a page object in `fixtures/pages.ts`. If a step is missing, add it there so the next test can use it.

**PW-2. Arrange through the API, not the UI.** Use `factory` to build state, then spend the test's own lines on the behavior under test. Drive the UI only for the steps the test is about.

**PW-3. UI goes through page objects** (lint). Use `pages.*` locators and actions, including for assertions, and navigate with a page object's `goto()`. When a screen or control has no page object entry, add one with a role, label, or text locator. Don't write the locator inline in the spec.

**PW-4. No credentials in specs** (lint). Use a persona: `apiAs`, `signIn`, `pageAs`. UI specs never post to `/api/auth/login`. The one exception is a test of signing in itself, which uses `USERS` and `PASSWORD`.

**PW-5. No fixed waits** (lint). Use web-first assertions (`await expect(locator).toBeVisible()`), and `expect.poll` for background work such as document extraction. Never use `waitForTimeout`, `networkidle`, or `force`.

**PW-6. One import** (lint). Everything from the test framework and this suite comes from `../fixtures`, types included; no inline `import("...")` types. Node built-ins such as `node:fs` are fine.

**PW-7. Role, label, and text locators only** (lint). No CSS or XPath. If an element can't be found by role or label, fix its accessibility in the app.

**PW-8. Every assertion runs on every path** (lint). No `if` around `expect`. For table-driven tests, split the rows by expected outcome, one test per outcome, as in `api/generated/KAN-3.spec.ts`.

**PW-9. Status assertions carry the body** (lint). Use `expectStatus(response, 201)`, never a bare `expect(response.status())`.

**PW-10. One behavior per test, in Arrange, Act, Assert order**, each step marked with a comment. A test from a story carries its tag: `test("...", { tag: "@KAN-12" }, ...)`. The exception is a journey test that follows one user flow end to end, across roles if it must, such as the member-to-reviewer flow in `ui/onboarding.spec.ts`: keep one per flow and say so in a comment.

**PW-11. Tests don't share data.** Every test creates what it needs, using `uniqueName` for anything unique such as vendor names. Only the seeded personas may be assumed to exist.

**PW-12. Assert the stored outcome, not just the response.** When a story says something is saved, re-read it (for example `factory.extraction(id)`), because a response can echo a value that was never stored.

**PW-13. Check every setup step** (lint, partly). A request made while arranging a test asserts its status, through `expectStatus` or a `factory` method, which already does. An unchecked failure surfaces later as a confusing one: a wrong row count instead of "vendor creation returned 422". Lint catches a response that's discarded; a response that's kept but never status-checked needs review.

## Layout

```
api/              API tests (no browser); api/generated/ is written by Storywright
ui/               UI tests in Desktop Chrome
fixtures/         index.ts (fixtures), factory.ts, pages.ts, http.ts, users.ts
eslint.config.mjs the lint rules above, by ID
```

Run it: `npm run lint`, `npm run typecheck`, `npx playwright test` (starts both servers on a fresh database).

## Changing these rules

A rule is added when a real gap is found: cite where it was found, add a detector to `eslint.config.mjs` when one is possible, and fix existing tests in the same pull request.
