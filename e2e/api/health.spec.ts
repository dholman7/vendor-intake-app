import { expect, test } from "../fixtures";

test("health check reports ok", async ({ request }) => {
  // Act
  const response = await request.get("/api/health");

  // Assert
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ status: "ok" });
});
