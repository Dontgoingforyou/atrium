import type { Page, Response } from "@playwright/test";
import { expect } from "@playwright/test";

import { AUTH_SHELL_VISIBLE_MS, PREFS_WATCH_MS } from "./timeouts";

function welcomeDialog(page: Page) {
  return page.getByRole("dialog", { name: /добро пожаловать/i });
}

/**
 * Ждёт GET preferences после логина (если запрос будет).
 * Регистрировать до клика «Войти», иначе можно пропустить ответ.
 */
export function watchAccountPreferencesGet(page: Page): Promise<Response | null> {
  return page
    .waitForResponse(
      (r) =>
        r.url().includes("/api/v1/portal/account/preferences") &&
        r.request().method() === "GET",
      { timeout: PREFS_WATCH_MS },
    )
    .catch(() => null);
}

/** После shell не блокируем timesheet-only на полном таймауте watcher'а. */
export async function awaitPrefsGetOrTimeout(
  prefsGet: Promise<Response | null>,
  timeoutMs = 10_000,
): Promise<Response | null> {
  return Promise.race([
    prefsGet,
    new Promise<null>((resolve) => {
      setTimeout(() => resolve(null), timeoutMs);
    }),
  ]);
}

/**
 * Снять running/hint-оверлей (`data-guided-tour`), иначе клики по nav перехватываются.
 * Welcome обрабатывает dismissGuidedTourAfterPrefs.
 */
export async function dismissRunningTourOrHint(page: Page, timeoutMs = 8_000): Promise<void> {
  const tourFlag = page.locator("html[data-guided-tour='1']");
  const closeHint = page.getByRole("button", { name: "Закрыть", exact: true });
  try {
    await tourFlag.waitFor({ state: "attached", timeout: timeoutMs });
  } catch {
    return;
  }

  try {
    await closeHint.waitFor({ state: "visible", timeout: 10_000 });
    await closeHint.click();
  } catch {
    await page.keyboard.press("Escape");
  }

  await expect(page.locator("html")).not.toHaveAttribute("data-guided-tour", "1", {
    timeout: 10_000,
  });
}

/**
 * Закрыть welcome guided tour, если он автостартовал.
 * Иначе smoke-клики по сайдбару упираются в modalBackdrop.
 * После пройденного тура всё равно закрываем контекстные плашки (TASKS-344).
 */
export async function dismissGuidedTourAfterPrefs(
  page: Page,
  prefsResponse: Response | null,
): Promise<void> {
  const welcome = welcomeDialog(page);

  if (prefsResponse?.ok()) {
    let completed = true;
    try {
      const body = (await prefsResponse.json()) as { guided_tour_completed?: boolean };
      completed = Boolean(body.guided_tour_completed);
    } catch {
      await dismissRunningTourOrHint(page);
      return;
    }
    if (completed) {
      await dismissRunningTourOrHint(page);
      return;
    }
    await welcome.waitFor({ state: "visible", timeout: 15_000 });
  } else {
    // Не поймали prefs (гонка / timesheet-only) — короткая проверка модалки.
    try {
      await welcome.waitFor({ state: "visible", timeout: 2_000 });
    } catch {
      await dismissRunningTourOrHint(page, 2_000);
      return;
    }
  }

  const skip = welcome.getByRole("button", { name: /пропустить/i })
  if (await skip.isVisible()) {
    await skip.click()
    await page.getByRole("button", { name: /приступить к работе|начать работу/i }).click()
    await expect(welcome).toBeHidden({ timeout: 15_000 })
    await dismissRunningTourOrHint(page, 3_000)
    return
  }

  const marked = await markGuidedTourCompletedInBrowser(page)
  if (!marked) {
    throw new Error(
      "Guided tour блокирует UI: нет «Пропустить…» и не удалось PATCH guided_tour_completed",
    )
  }
  await page.reload();
  await expect(page.getByRole("link", { name: "Аккаунт", exact: true })).toBeVisible({
    timeout: AUTH_SHELL_VISIBLE_MS,
  });
  await expect(welcome).toBeHidden({ timeout: 5_000 });
  await dismissRunningTourOrHint(page);
}

async function markGuidedTourCompletedInBrowser(page: Page): Promise<boolean> {
  return page.evaluate(async () => {
    let clientId = "";
    try {
      const raw = localStorage.getItem("atrium-auth");
      if (raw) {
        const parsed = JSON.parse(raw) as { state?: { oauthClientId?: string | null } };
        clientId = parsed.state?.oauthClientId?.trim() ?? "";
      }
    } catch {
      // ignore
    }

    const body: Record<string, string> = {};
    if (clientId) body.client_id = clientId;

    const refreshRes = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    });
    if (!refreshRes.ok) return false;

    const data = (await refreshRes.json()) as { access_token?: string };
    if (!data.access_token) return false;

    const patchRes = await fetch("/api/v1/portal/account/preferences", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${data.access_token}`,
      },
      body: JSON.stringify({ guided_tour_completed: true }),
    });
    return patchRes.ok;
  });
}
