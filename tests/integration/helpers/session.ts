import type { Page } from "@playwright/test";

import { expectAuthenticatedShell, loginViaStandSso } from "./adapters/sso";

/** Открыть портал с уже сохранённой сессией (storageState из setup). */
export async function openAuthenticatedShell(page: Page): Promise<void> {
  await page.goto("/");
  await expectAuthenticatedShell(page);
}

export async function ensureLoggedIn(page: Page): Promise<void> {
  await loginViaStandSso(page);
  await expectAuthenticatedShell(page);
}
