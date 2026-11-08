import { test, expect } from "@playwright/test";

import { expectAuthenticatedShell } from "../helpers/adapters/sso";
import { openAuthenticatedShell } from "../helpers/session";

/**
 * Проверка UI-guards относительно фактических прав E2E-пользователя.
 * Для чистого TC-017/018 (только отказ) нужен сотрудник без manager/admin.
 * Если в .env admin/manager — проверяем успешный доступ (тот же маршрут).
 */
test.describe("RBAC UI", () => {
  test.beforeEach(async ({ page }) => {
    await openAuthenticatedShell(page);
  });

  test("корзина /p/trash по правам", async ({ page }) => {
    test.info().annotations.push({ type: "tc", description: "TC-018" });

    const canTrash = await page
      .getByRole("link", { name: "Корзина документов", exact: true })
      .isVisible();

    await page.goto("/p/trash");

    if (canTrash) {
      await expect(page).toHaveURL(/\/p\/trash/);
      await expectAuthenticatedShell(page);
    } else {
      await expect(page).toHaveURL((url) => new URL(url).pathname === "/", {
        timeout: 15_000,
      });
      await expectAuthenticatedShell(page);
    }
  });

  test("admin-bridge по правам", async ({ page }) => {
    test.info().annotations.push({ type: "tc", description: "TC-017" });

    const isAdmin = await page
      .getByRole("button", { name: "Панель администратора", exact: true })
      .isVisible();

    await page.goto("/admin-bridge");

    if (isAdmin) {
      await expect(page).toHaveURL(/\/admin\/?/, { timeout: 30_000 });
      await expect(page.getByText(/Atrium Admin|Административная панель/i).first()).toBeVisible({
        timeout: 15_000,
      });
    } else {
      await expect(
        page.getByText(/нет прав доступа к панели администратора/i),
      ).toBeVisible({ timeout: 30_000 });
      await expect(page).not.toHaveURL(/\/admin\/?$/);
    }
  });
});
