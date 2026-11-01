import { expect, test } from "../fixtures";

test("members don't see the review queue", async ({ pages, signIn }) => {
  // Arrange
  await signIn("member");

  // Act
  await pages.reviewQueue.goto();

  // Assert
  await expect(pages.shell.alert).toHaveText("Only reviewers and admins can review vendors.");
  await expect(pages.shell.reviewQueueLink).toHaveCount(0);
});

test("reviewers see the review queue link", async ({ pages, signIn }) => {
  // Arrange
  await signIn("reviewer");

  // Act
  await pages.vendors.goto();

  // Assert
  await expect(pages.shell.reviewQueueLink).toBeVisible();
});

test("a vendor from another tenant can't be opened", async ({ pages, signIn, factory }) => {
  // Arrange
  const other = await factory.vendor({ as: "otherTenant", category: "other" });
  await signIn("member");

  // Act
  await pages.vendor.goto(other.id);

  // Assert
  await expect(pages.shell.alert).toHaveText("This vendor doesn't exist or belongs to another team.");
});
