import { expect, test, uniqueName } from "../fixtures";

test.beforeEach(async ({ signIn }) => {
  await signIn("member");
});

test("create a vendor and land on its page as a draft", async ({ pages }) => {
  // Arrange
  const name = uniqueName("Acme Freight");
  await pages.newVendor.goto();

  // Act
  await pages.newVendor.create({ name, email: "ops@acmefreight.example", category: "logistics" });

  // Assert
  await expect(pages.vendor.heading(name)).toBeVisible();
  await expect(pages.vendor.status("Draft")).toBeVisible();
  await expect(pages.vendor.stillNeeded(["w9", "insurance_certificate", "contract"])).toBeVisible();
});

test("a duplicate name is reported on the name field", async ({ pages, factory }) => {
  // Arrange
  const { name } = await factory.vendor({ name: uniqueName("Duplicate Co") });
  await pages.newVendor.goto();

  // Act
  await pages.newVendor.create({ name: name.toLowerCase(), email: "b@dup.example" });

  // Assert
  await expect(pages.newVendor.name).toHaveAttribute("aria-invalid", "true");
  await expect(pages.newVendor.name).toHaveAccessibleDescription(/already exists/);
});

test("search narrows the vendor list", async ({ page, pages, factory }) => {
  // Arrange
  const { name } = await factory.vendor({ name: uniqueName("Zephyr Searchable"), category: "software" });
  await pages.vendors.goto();

  // Act
  await pages.vendors.search.fill(name.split(" ").slice(1).join(" "));

  // Assert
  await expect(pages.vendors.rows).toHaveCount(2); // header + match
  await expect(pages.vendors.link(name)).toBeVisible();
  await expect(page).toHaveURL(/q=/);
});
