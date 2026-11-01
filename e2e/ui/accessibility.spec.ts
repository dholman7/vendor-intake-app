import { expect, test } from "../fixtures";

test("sign in page has no serious accessibility violations", async ({ pages, a11y }) => {
  // Act
  await pages.signIn.goto();
  await expect(pages.signIn.submitButton).toBeVisible();

  // Assert
  expect(await a11y.seriousViolations()).toEqual([]);
});

test("vendor list has no serious violations", async ({ pages, signIn, factory, a11y }) => {
  // Arrange
  await factory.vendor();
  await signIn("member");

  // Act
  await pages.vendors.goto();
  await expect(pages.vendors.table).toBeVisible();

  // Assert
  expect(await a11y.seriousViolations()).toEqual([]);
});

test("new vendor form has no serious violations", async ({ pages, signIn, a11y }) => {
  // Arrange
  await signIn("member");

  // Act
  await pages.newVendor.goto();
  await expect(pages.newVendor.name).toBeVisible();

  // Assert
  expect(await a11y.seriousViolations()).toEqual([]);
});

test("vendor detail with extracted fields has no serious violations", async ({ pages, signIn, factory, a11y }) => {
  // Arrange: extracted documents, so the boxed form fields are part of the scan
  const { vendor } = await factory.vendorWithDocuments();
  await signIn("member");

  // Act
  await pages.vendor.goto(vendor.id);
  await expect(pages.vendor.confidence("Legal name")).toBeVisible();

  // Assert
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
