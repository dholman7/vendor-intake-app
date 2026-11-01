// The one import for every spec: fixtures, page objects, data factory, and types.
// Conventions for using them are in ../AGENTS.md.
import AxeBuilder from "@axe-core/playwright";
import { test as base, expect, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL } from "../playwright.config";
import { Factory } from "./factory";
import { expectStatus } from "./http";
import { pagesFor, type Pages } from "./pages";
import { PASSWORD, USERS, type Persona } from "./users";

async function tokenFor(request: APIRequestContext, persona: Persona): Promise<string> {
  const response = await request.post(`${API_URL}/api/auth/login`, {
    data: { email: USERS[persona], password: PASSWORD },
  });
  return (await expectStatus<{ access_token: string }>(response, 200)).access_token;
}

/** Signs a browser context in by setting the session cookie, skipping the sign-in form. */
async function signInPage(page: Page, persona: Persona) {
  // Through the web origin so the cookie lands on the domain the browser uses.
  await expectStatus(await page.request.post("/api/auth/login", { data: { email: USERS[persona], password: PASSWORD } }), 200);
}

export type SignedInPage = Pages & { page: Page };

interface Fixtures {
  /** API client authenticated as a seeded persona, e.g. `await apiAs("reviewer")`. */
  apiAs: (persona: Persona) => Promise<APIRequestContext>;
  /** Signs the test's own `page` in as a persona. */
  signIn: (persona: Persona) => Promise<void>;
  /** A separate signed-in browser page, for tests where two roles act, e.g. `await pageAs("reviewer")`. */
  pageAs: (persona: Persona) => Promise<SignedInPage>;
  /** Builds vendors, documents, and reviews through the API. */
  factory: Factory;
  /** Page objects bound to the test's own `page`. */
  pages: Pages;
  /** Accessibility scan: serious and critical WCAG 2.1 AA violations on a page. */
  a11y: { seriousViolations: (page?: Page) => Promise<string[]> };
}

export const test = base.extend<Fixtures>({
  apiAs: async ({ playwright, request }, use) => {
    const contexts: APIRequestContext[] = [];
    await use(async (persona) => {
      const token = await tokenFor(request, persona);
      const context = await playwright.request.newContext({
        baseURL: API_URL,
        extraHTTPHeaders: { Authorization: `Bearer ${token}` },
      });
      contexts.push(context);
      return context;
    });
    await Promise.all(contexts.map((c) => c.dispose()));
  },

  signIn: async ({ page }, use) => {
    await use((persona) => signInPage(page, persona));
  },

  pageAs: async ({ browser }, use) => {
    const contexts: Awaited<ReturnType<typeof browser.newContext>>[] = [];
    await use(async (persona) => {
      const context = await browser.newContext();
      contexts.push(context);
      const page = await context.newPage();
      await signInPage(page, persona);
      return { page, ...pagesFor(page) };
    });
    await Promise.all(contexts.map((c) => c.close()));
  },

  factory: async ({ apiAs }, use) => {
    await use(new Factory(apiAs));
  },

  pages: async ({ page }, use) => {
    await use(pagesFor(page));
  },

  a11y: async ({ page }, use) => {
    await use({
      seriousViolations: async (target = page) => {
        const results = await new AxeBuilder({ page: target }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
        return results.violations
          .filter((v) => v.impact === "serious" || v.impact === "critical")
          .map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`);
      },
    });
  },
});

export { expect, expectStatus, PASSWORD, USERS };
export { DOCUMENT_KINDS, sample, uniqueName } from "./factory";
export type { Document, DocumentKind, Extraction, Vendor } from "./factory";
export { KIND_LABELS } from "./pages";
export type { Pages } from "./pages";
export type { APIRequestContext, Page, Persona };
