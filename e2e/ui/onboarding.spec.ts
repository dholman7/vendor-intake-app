// The core journey across both roles: features/documents.feature and features/review.feature.
import { expect, sample, test, uniqueName, type Page } from "../fixtures";

async function createVendorWithDocuments(page: Page, insuranceFile = "insurance_certificate.txt") {
  const name = uniqueName("Harborline");
  await page.goto("/vendors/new");
  await page.getByLabel("Vendor name").fill(name);
  await page.getByLabel("Contact email").fill("ops@harborline.example");
  await page.getByRole("button", { name: "Create vendor" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();

  await page.getByLabel("Upload W-9").setInputFiles(sample("w9.txt"));
  await page.getByLabel("Upload Insurance certificate").setInputFiles(sample(insuranceFile));
  await page.getByLabel("Upload Contract").setInputFiles(sample("contract.txt"));
  // Extraction runs in the background; the page polls until every document is extracted.
  await expect(page.getByRole("button", { name: "Submit for review" })).toBeEnabled({ timeout: 15_000 });
  return name;
}

test("member submits a vendor and a reviewer approves it", async ({ browser, page, signIn }) => {
  // Arrange
  await signIn("member");
  const name = await createVendorWithDocuments(page);
  const vendorUrl = page.url();

  // Act: member submits
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.getByLabel("Vendor status").getByText("In review")).toBeVisible();

  // Act: reviewer approves every document
  const reviewerContext = await browser.newContext();
  const reviewer = await reviewerContext.newPage();
  await reviewer.request.post("/api/auth/login", {
    data: { email: "reviewer@northwind.test", password: "demo-password" },
  });
  await reviewer.goto("/review");
  const card = reviewer.getByRole("article", { name });
  for (const kind of ["W-9", "Insurance certificate", "Contract"]) {
    await card.getByRole("button", { name: `Approve ${kind}` }).click();
    await expect(card.getByRole("button", { name: `Approve ${kind}` })).toBeHidden();
  }
  await expect(card).toBeHidden();
  await reviewerContext.close();

  // Assert
  await page.goto(vendorUrl);
  await expect(page.getByLabel("Vendor status").getByText("Approved")).toBeVisible();
  await expect(page.getByText("Vendor approved")).toBeVisible();
});

test("low-confidence fields are visible before submitting", async ({ page, signIn }) => {
  // Arrange
  await signIn("member");

  // Act
  await createVendorWithDocuments(page, "insurance_certificate_unparseable.txt");

  // Assert
  const insurance = page.getByRole("region", { name: "Insurance certificate" });
  await expect(insurance.getByRole("meter", { name: "Expires confidence" })).toHaveAttribute("aria-valuenow", "30");
  await expect(insurance.getByText("Not found")).toHaveCount(2);
});

test("a reviewer's requested changes reach the member", async ({ browser, page, signIn }) => {
  // Arrange
  await signIn("member");
  const name = await createVendorWithDocuments(page);
  const vendorUrl = page.url();
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.getByLabel("Vendor status").getByText("In review")).toBeVisible();

  // Act
  const reviewerContext = await browser.newContext();
  const reviewer = await reviewerContext.newPage();
  await reviewer.request.post("/api/auth/login", {
    data: { email: "reviewer@northwind.test", password: "demo-password" },
  });
  await reviewer.goto("/review");
  const card = reviewer.getByRole("article", { name });
  await card.getByRole("button", { name: "Request changes to W-9" }).click();
  await card.getByLabel("What should the member fix?").fill("Tax ID does not match the IRS letter.");
  await card.getByRole("button", { name: "Send back to member" }).click();
  await expect(card).toBeHidden();
  await reviewerContext.close();

  // Assert
  await page.goto(vendorUrl);
  await expect(page.getByText("A reviewer requested changes.")).toBeVisible();
  await expect(page.getByText("Reviewer note: Tax ID does not match the IRS letter.")).toBeVisible();
  await expect(page.getByText("Still needed: W-9")).toBeVisible();
});
