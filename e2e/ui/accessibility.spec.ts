import { readFileSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";

import { expect, sample, test, uniqueName, type Page } from "../fixtures";

async function seriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  return results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`);
}

test("sign in page has no serious accessibility violations", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  expect(await seriousViolations(page)).toEqual([]);
});

test("vendor list, new vendor, and vendor detail have no serious violations", async ({ page, signIn, apiAs }) => {
  // Arrange
  await signIn("member");
  const member = await apiAs("member");
  const created = await member.post("/api/vendors", {
    data: { name: uniqueName("Axe Check"), category: "services", contact_email: "a@axe.example" },
  });
  const { id } = (await created.json()) as { id: string };
  // An extracted document, so the boxed form fields are part of the scan.
  await member.post(`/api/vendors/${id}/documents`, {
    multipart: {
      kind: "w9",
      file: { name: "w9.txt", mimeType: "text/plain", buffer: readFileSync(sample("w9.txt")) },
    },
  });

  // Act / Assert
  await page.goto("/vendors");
  await expect(page.getByRole("table")).toBeVisible();
  expect(await seriousViolations(page)).toEqual([]);

  await page.goto("/vendors/new");
  await expect(page.getByLabel("Vendor name")).toBeVisible();
  expect(await seriousViolations(page)).toEqual([]);

  await page.goto(`/vendors/${id}`);
  await expect(page.getByRole("meter", { name: "Legal name confidence" })).toBeVisible();
  expect(await seriousViolations(page)).toEqual([]);
});

test("review queue has no serious violations", async ({ page, signIn }) => {
  await signIn("reviewer");
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  expect(await seriousViolations(page)).toEqual([]);
});
