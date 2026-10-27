import { PASSWORD, USERS, expect, test } from "../fixtures";

test("member signs in with the form and lands on vendors", async ({ page }) => {
  // Arrange
  await page.goto("/login");

  // Act
  await page.getByLabel("Email").fill(USERS.member);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  // Assert
  await expect(page).toHaveURL(/\/vendors$/);
  await expect(page.getByRole("heading", { name: "Vendors", level: 1 })).toBeVisible();
  await expect(page.getByText("Morgan Member")).toBeVisible();
});

test("wrong password shows an error and stays on sign in", async ({ page }) => {
  // Arrange
  await page.goto("/login");

  // Act
  await page.getByLabel("Email").fill(USERS.member);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  // Assert
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Email or password is incorrect");
  await expect(page).toHaveURL(/\/login/);
});

test("signed-out visitors are sent to sign in and returned afterwards", async ({ page }) => {
  // Act
  await page.goto("/vendors/new");

  // Assert
  await expect(page).toHaveURL(/\/login\?next=%2Fvendors%2Fnew/);
  await page.getByRole("button", { name: "Fill in member" }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "New vendor" })).toBeVisible();
});

test("signing out ends the session", async ({ page, signIn }) => {
  // Arrange
  await signIn("member");
  await page.goto("/vendors");

  // Act
  await page.getByRole("button", { name: "Sign out" }).click();

  // Assert
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/vendors");
  await expect(page).toHaveURL(/\/login\?next=/);
});
