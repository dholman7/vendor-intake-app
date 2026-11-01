// The core journey across both roles: features/documents.feature and features/review.feature.
import { DOCUMENT_KINDS, expect, test, uniqueName } from "../fixtures";

test("member submits a vendor and a reviewer approves it", async ({ page, pages, pageAs, signIn }) => {
  // Arrange: the whole member journey runs through the UI, since it is what this test covers
  await signIn("member");
  const name = uniqueName("Harborline");
  await pages.newVendor.goto();
  await pages.newVendor.create({ name, email: "ops@harborline.example" });
  await expect(pages.vendor.heading(name)).toBeVisible();
  for (const kind of DOCUMENT_KINDS) await pages.vendor.upload(kind);
  await pages.vendor.waitUntilReadyToSubmit();
  const vendorUrl = page.url();

  // Act: member submits
  await pages.vendor.submitButton.click();
  await expect(pages.vendor.status("In review")).toBeVisible();

  // Act: reviewer approves every document
  const reviewer = await pageAs("reviewer");
  await reviewer.reviewQueue.goto();
  for (const kind of DOCUMENT_KINDS) await reviewer.reviewQueue.approve(name, kind);
  await expect(reviewer.reviewQueue.card(name)).toBeHidden();

  // Assert
  await page.goto(vendorUrl);
  await expect(pages.vendor.status("Approved")).toBeVisible();
  await expect(page.getByText("Vendor approved")).toBeVisible();
});

test("low-confidence fields are visible before submitting", async ({ pages, signIn, factory }) => {
  // Arrange
  const { vendor } = await factory.vendorWithDocuments({
    files: { insurance_certificate: "insurance_certificate_unparseable.txt" },
  });
  await signIn("member");

  // Act
  await pages.vendor.goto(vendor.id);

  // Assert
  const insurance = pages.vendor.document("insurance_certificate");
  await expect(insurance.getByRole("meter", { name: "Expires confidence" })).toHaveAttribute("aria-valuenow", "30");
  await expect(insurance.getByText("Not found")).toHaveCount(2);
});

test("a reviewer's requested changes reach the member", async ({ page, pages, pageAs, signIn, factory }) => {
  // Arrange
  const { vendor } = await factory.vendorInReview();
  await signIn("member");

  // Act
  const reviewer = await pageAs("reviewer");
  await reviewer.reviewQueue.goto();
  await reviewer.reviewQueue.requestChanges(vendor.name, "w9", "Tax ID does not match the IRS letter.");
  await expect(reviewer.reviewQueue.card(vendor.name)).toBeHidden();

  // Assert
  await pages.vendor.goto(vendor.id);
  await expect(page.getByText("A reviewer requested changes.")).toBeVisible();
  await expect(page.getByText("Reviewer note: Tax ID does not match the IRS letter.")).toBeVisible();
  await expect(page.getByText("Still needed: W-9")).toBeVisible();
});
