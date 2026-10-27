// features/auth.feature (a starting point; most API coverage is left for generated tests)
import { PASSWORD, USERS, expect, test } from "../fixtures";

test.describe("sign in", () => {
  test("returns a token and an HttpOnly session cookie", async ({ request }) => {
    // Act
    const response = await request.post("/api/auth/login", {
      data: { email: USERS.member, password: PASSWORD },
    });

    // Assert
    expect(response.status()).toBe(200);
    expect((await response.json()).access_token).toBeTruthy();
    const cookie = response.headersArray().find((h) => h.name.toLowerCase() === "set-cookie");
    expect(cookie?.value).toMatch(/^session=/);
    expect(cookie?.value.toLowerCase()).toContain("httponly");
  });

  test("rejects a wrong password with invalid_credentials", async ({ request }) => {
    // Act
    const response = await request.post("/api/auth/login", {
      data: { email: USERS.member, password: "wrong-password" },
    });

    // Assert
    expect(response.status()).toBe(401);
    expect((await response.json()).error.code).toBe("invalid_credentials");
  });
});

test("profile shows the signed-in user's role and tenant", async ({ apiAs }) => {
  // Arrange
  const member = await apiAs("member");

  // Act
  const response = await member.get("/api/me");

  // Assert
  expect(response.status()).toBe(200);
  const profile = await response.json();
  expect(profile.role).toBe("member");
  expect(profile.tenant.name).toBe("Northwind Supply");
});
