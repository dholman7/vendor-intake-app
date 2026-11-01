import { expect, test, uniqueName } from "../fixtures";

test("sign in page has no serious accessibility violations", async ({ pages, a11y }) => {
  // Act
  await pages.signIn.goto();
  await expect(pages.signIn.submitButton).toBeVisible();

  // Assert
  expect(await a11y.seriousViolations()).toEqual([]);
});

test("vendor list, new vendor, and vendor detail have no serious violations", async ({ pages, signIn, factory, a11y }) => {
  // Arrange: an extracted document, so the boxed form fields are part of the scan
  const vendor = await factory.vendor({ name: uniqueName("Axe Check") });
  await factory.upload(vendor.id, "w9");
  await signIn("member");

  // Act / Assert
  await pages.vendors.goto();
  await expect(pages.vendors.table).toBeVisible();
  expect(await a11y.seriousViolations()).toEqual([]);

  await pages.newVendor.goto();
  await expect(pages.newVendor.name).toBeVisible();
  expect(await a11y.seriousViolations()).toEqual([]);

  await pages.vendor.goto(vendor.id);
  await expect(pages.vendor.confidence("Legal name")).toBeVisible();
  expect(await a11y.seriousViolations()).toEqual([]);
});

test("review queue has no serious violations", async ({ pages, signIn, a11y }) => {
  // Arrange
  await signIn("reviewer");

  // Act
  await pages.reviewQueue.goto();
  await expect(pages.reviewQueue.heading).toBeVisible();

  // Assert
  expect(await a11y.seriousViolations()).toEqual([]);
});
