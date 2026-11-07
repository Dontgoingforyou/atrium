import { mkdir } from "node:fs/promises";
import path from "node:path";

import { test as setup } from "@playwright/test";

import { loginViaStandSso } from "../helpers/adapters/sso";
import { AUTH_STATE_PATH } from "../helpers/authState";

setup("вход SSO и сохранение сессии", async ({ page }) => {
  await loginViaStandSso(page);
  await mkdir(path.dirname(AUTH_STATE_PATH), { recursive: true });
  await page.context().storageState({ path: AUTH_STATE_PATH });
});
