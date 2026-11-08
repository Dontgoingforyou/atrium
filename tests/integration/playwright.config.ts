import { defineConfig, devices } from "@playwright/test";

import { AUTH_STATE_PATH } from "./helpers/authState";
import { loadIntegrationEnv } from "./helpers/loadEnv";

loadIntegrationEnv();

const baseURL = (process.env.APP_BASE_URL ?? "http://127.0.0.1:9088").replace(/\/$/, "");

export default defineConfig({
  testDir: "./specs",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["junit", { outputFile: "../reports/junit-integration.xml" }],
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "portal",
      dependencies: ["setup"],
      testIgnore: [/auth\.setup\.ts/, /sso-login\.spec.ts/],
      use: { storageState: AUTH_STATE_PATH },
    },
    {
      name: "login-flow",
      testMatch: /sso-login\.spec.ts/,
      use: { storageState: { cookies: [], origins: [] } },
    },
  ],
});
