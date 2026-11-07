import { test, expect } from "@playwright/test";

import { expectAuthenticatedShell } from "../helpers/adapters/sso";
import { dismissRunningTourOrHint } from "../helpers/dismissGuidedTour";

test.describe("smoke app-shell", () => {
  test("главная, задачи и чаты открываются без login loop", async ({ page }) => {
    test.info().annotations.push({ type: "tc", description: "TC-004" });
    test.info().annotations.push({ type: "tc", description: "TC-005" });
    test.info().annotations.push({ type: "tc", description: "TC-010" });

    await page.goto("/");
    await expectAuthenticatedShell(page);
    await dismissRunningTourOrHint(page);
    await expect(page.getByRole("link", { name: "Главная", exact: true })).toBeVisible();

    await page.locator('a[href="/tasks"]').first().click();
    await expect(page).toHaveURL(/\/tasks/);
    await expectAuthenticatedShell(page);
    await dismissRunningTourOrHint(page);

    // href: у «Чаты» может быть бейдж непрочитанных → accessible name ≠ «Чаты»
    await page.locator('a[href="/chats"]').first().click();
    await expect(page).toHaveURL(/\/chats/);
    await expectAuthenticatedShell(page);
  });
});
