import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

import {
  awaitPrefsGetOrTimeout,
  dismissGuidedTourAfterPrefs,
  watchAccountPreferencesGet,
} from "../dismissGuidedTour";
import { requireEnv } from "../env";
import { loadIntegrationEnv } from "../loadEnv";
import {
  AUTH_SHELL_VISIBLE_MS,
  LOGIN_FORM_VISIBLE_MS,
  LOGIN_SHELL_VISIBLE_MS,
} from "../timeouts";

/** Пункт сайдбара «Аккаунт» — exact, иначе цепляются документы «аккаунт-менеджера». */
function accountNavLink(page: Page) {
  return page.getByRole("link", { name: "Аккаунт", exact: true });
}

/**
 * Логин через форму `/login` Cosmolet (POST /auth/login → прокси SSO).
 * Критерий: app-shell с пунктом «Аккаунт» и кнопкой «Выход».
 * После логина закрывает автостарт guided tour (иначе modalBackdrop ломает клики по nav).
 */
export async function loginViaStandSso(page: Page): Promise<void> {
  loadIntegrationEnv();
  const appBase = requireEnv("APP_BASE_URL").replace(/\/$/, "");
  const email = requireEnv("E2E_SSO_USER_EMAIL");
  const password = requireEnv("E2E_SSO_USER_PASSWORD");

  await page.goto(`${appBase}/login`);

  await expect(page.getByRole("heading", { name: /войти в/i })).toBeVisible({
    timeout: LOGIN_FORM_VISIBLE_MS,
  });

  const loginField = page.getByLabel(/email или логин/i);
  await loginField.waitFor({ state: "visible", timeout: LOGIN_FORM_VISIBLE_MS });
  await loginField.fill(email);

  const passwordField = page.getByLabel(/^пароль$/i);
  await passwordField.fill(password);

  // Preferences грузятся сразу после shell — слушаем до клика «Войти».
  const prefsGet = watchAccountPreferencesGet(page);

  await page.getByRole("button", { name: /^войти$/i }).click();

  const account = accountNavLink(page);
  const loginError = page.getByRole("alert");
  try {
    await expect(account).toBeVisible({ timeout: LOGIN_SHELL_VISIBLE_MS });
  } catch (err) {
    const errText = (await loginError.textContent().catch(() => null))?.trim();
    if (errText) {
      throw new Error(`Логин не удался (форма): ${errText}`);
    }
    throw err;
  }
  await expect(page.getByRole("button", { name: "Выход", exact: true })).toBeVisible();

  const prefsResponse = await awaitPrefsGetOrTimeout(prefsGet);
  await dismissGuidedTourAfterPrefs(page, prefsResponse);
}

/** Проверка, что сессия жива (после reload или навигации). */
export async function expectAuthenticatedShell(page: Page): Promise<void> {
  await expect(accountNavLink(page)).toBeVisible({ timeout: AUTH_SHELL_VISIBLE_MS });
  await expect(page.getByRole("button", { name: "Выход", exact: true })).toBeVisible();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
}
