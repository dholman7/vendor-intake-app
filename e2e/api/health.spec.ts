import { expect, expectStatus, test } from "../fixtures";

test("health check reports ok", async ({ request }) => {
  // Act
  const response = await request.get("/api/health");

  // Assert
  expect(await expectStatus(response, 200)).toEqual({ status: "ok" });
});
