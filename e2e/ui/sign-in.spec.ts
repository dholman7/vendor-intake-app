import { PASSWORD, USERS, expect, test } from "../fixtures";

test("member signs in with the form and lands on vendors", async ({ page, pages }) => {
  // Arrange
  await pages.signIn.goto();

  // Act
  await pages.signIn.signIn(USERS.member, PASSWORD);

  // Assert
  await expect(page).toHaveURL(/\/vendors$/);
  await expect(pages.vendors.heading).toBeVisible();
  await expect(page.getByText("Morgan Member")).toBeVisible();
});

test("wrong password shows an error and stays on sign in", async ({ page, pages }) => {
  // Arrange
  await pages.signIn.goto();

  // Act
  await pages.signIn.signIn(USERS.member, "wrong-password");

  // Assert
  await expect(pages.signIn.error).toHaveText("Email or password is incorrect");
  await expect(page).toHaveURL(/\/login/);
});

test("signed-out visitors are sent to sign in and returned afterwards", async ({ page, pages }) => {
  // Act
  await pages.newVendor.goto();

  // Assert
  await expect(page).toHaveURL(/\/login\?next=%2Fvendors%2Fnew/);
  await pages.signIn.fillDemoAccount("member");
  await pages.signIn.submitButton.click();
  await expect(pages.newVendor.heading).toBeVisible();
});

test("signing out ends the session", async ({ page, pages, signIn }) => {
  // Arrange
  await signIn("member");
  await pages.vendors.goto();

  // Act
  await pages.shell.signOutButton.click();

  // Assert
  await expect(page).toHaveURL(/\/login$/);
  await pages.vendors.goto();
  await expect(page).toHaveURL(/\/login\?next=/);
});
