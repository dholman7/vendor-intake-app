import { expect, test, uniqueName } from "../fixtures";

test("members don't see the review queue", async ({ page, signIn }) => {
  // Arrange
  await signIn("member");

  // Act
  await page.goto("/review");

  // Assert
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Only reviewers and admins can review vendors.");
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Review queue" })).toHaveCount(0);
});

test("reviewers see the review queue link", async ({ page, signIn }) => {
  // Arrange
  await signIn("reviewer");

  // Act
  await page.goto("/vendors");

  // Assert
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Review queue" })).toBeVisible();
});

test("a vendor from another tenant can't be opened", async ({ page, signIn, apiAs }) => {
  // Arrange
  const other = await apiAs("otherTenant");
  const created = await other.post("/api/vendors", {
    data: { name: uniqueName("Globex Only"), category: "other", contact_email: "x@globex.example" },
  });
  const { id } = (await created.json()) as { id: string };
  await signIn("member");

  // Act
  await page.goto(`/vendors/${id}`);

  // Assert
  await expect(page.getByRole("main").getByRole("alert")).toHaveText(
    "This vendor doesn't exist or belongs to another team.",
  );
});
