import { test, expect } from "@playwright/test";

import { expectAuthenticatedShell, loginViaStandSso } from "../helpers/adapters/sso";

test.describe("вход по логину и паролю", () => {
  test("после логина виден app-shell и refresh cookie", async ({ page, context }) => {
    test.info().annotations.push({ type: "tc", description: "TC-019" });

    await loginViaStandSso(page);
    await expectAuthenticatedShell(page);

    const cookies = await context.cookies();
    const refresh = cookies.find((c) => c.name === "rt" && c.httpOnly);
    expect(refresh, "ожидается httpOnly cookie rt после успешного логина").toBeTruthy();
    expect(refresh?.path ?? "").toContain("/api/v1/auth/refresh");
  });
});
