import { defineConfig, devices } from "@playwright/test";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";
export const WEB_URL = process.env.WEB_URL ?? "http://localhost:3000";
const CI = Boolean(process.env.CI);

export default defineConfig({
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: CI ? [["github"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    // Request-level tests against FastAPI; no browser.
    { name: "api", testDir: "./api", use: { baseURL: API_URL } },
    { name: "ui", testDir: "./ui", use: { ...devices["Desktop Chrome"], baseURL: WEB_URL } },
  ],
  // Starts both servers against a fresh seeded database unless they're already running
  // (locally) or URLs point elsewhere (set E2E_EXTERNAL_SERVERS=1).
  webServer: process.env.E2E_EXTERNAL_SERVERS
    ? undefined
    : [
        {
          command: "bash scripts/start-api.sh",
          url: `${API_URL}/api/health`,
          reuseExistingServer: !CI,
          timeout: 120_000,
        },
        {
          command: "bash scripts/start-web.sh",
          url: `${WEB_URL}/login`,
          reuseExistingServer: !CI,
          timeout: 240_000,
        },
      ],
});
