import path from "node:path";

import { test as base, expect, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL } from "../playwright.config";

export const PASSWORD = "demo-password";
export const USERS = {
  member: "member@northwind.test",
  reviewer: "reviewer@northwind.test",
  admin: "admin@northwind.test",
  otherTenant: "member@globex.test",
} as const;
export type Persona = keyof typeof USERS;

export const SAMPLES = path.resolve(__dirname, "../../samples");
export const sample = (file: string) => path.join(SAMPLES, file);

/** Vendor names must be unique per tenant, and tests share one database. */
export function uniqueName(prefix: string): string {
  return `${prefix} ${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

async function tokenFor(request: APIRequestContext, persona: Persona): Promise<string> {
  const response = await request.post(`${API_URL}/api/auth/login`, {
    data: { email: USERS[persona], password: PASSWORD },
  });
  expect(response.status(), `sign in as ${persona}`).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

interface Fixtures {
  /** API client authenticated as a seeded persona, e.g. `await apiAs("reviewer")`. */
  apiAs: (persona: Persona) => Promise<APIRequestContext>;
  /** Signs the browser in by setting the session cookie, skipping the sign-in form. */
  signIn: (persona: Persona) => Promise<void>;
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
    await use(async (persona) => {
      // Through the web origin so the cookie lands on the domain the browser uses.
      const response = await page.request.post("/api/auth/login", {
        data: { email: USERS[persona], password: PASSWORD },
      });
      expect(response.status(), `sign in as ${persona}`).toBe(200);
    });
  },
});

export { expect };
export type { Page };
