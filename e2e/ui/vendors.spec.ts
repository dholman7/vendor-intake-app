import { expect, test, uniqueName } from "../fixtures";

test.beforeEach(async ({ signIn }) => {
  await signIn("member");
});

test("create a vendor and land on its page as a draft", async ({ page }) => {
  // Arrange
  const name = uniqueName("Acme Freight");
  await page.goto("/vendors/new");

  // Act
  await page.getByLabel("Vendor name").fill(name);
  await page.getByLabel("Category").selectOption("logistics");
  await page.getByLabel("Contact email").fill("ops@acmefreight.example");
  await page.getByRole("button", { name: "Create vendor" }).click();

  // Assert
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
  await expect(page.getByLabel("Vendor status").getByText("Draft")).toBeVisible();
  await expect(page.getByText("Still needed: W-9, Insurance certificate, Contract")).toBeVisible();
});

test("a duplicate name is reported on the name field", async ({ page, apiAs }) => {
  // Arrange
  const name = uniqueName("Duplicate Co");
  const member = await apiAs("member");
  await member.post("/api/vendors", {
    data: { name, category: "services", contact_email: "a@dup.example" },
  });
  await page.goto("/vendors/new");

  // Act
  await page.getByLabel("Vendor name").fill(name.toLowerCase());
  await page.getByLabel("Contact email").fill("b@dup.example");
  await page.getByRole("button", { name: "Create vendor" }).click();

  // Assert
  await expect(page.getByLabel("Vendor name")).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText(/already exists/)).toBeVisible();
});

test("search narrows the vendor list", async ({ page, apiAs }) => {
  // Arrange
  const name = uniqueName("Zephyr Searchable");
  const member = await apiAs("member");
  await member.post("/api/vendors", {
    data: { name, category: "software", contact_email: "z@zephyr.example" },
  });
  await page.goto("/vendors");

  // Act
  await page.getByLabel("Search vendors").fill(name.split(" ").slice(1).join(" "));

  // Assert
  const rows = page.getByRole("table").getByRole("row");
  await expect(rows).toHaveCount(2); // header + match
  await expect(page.getByRole("link", { name })).toBeVisible();
  await expect(page).toHaveURL(/q=/);
});
