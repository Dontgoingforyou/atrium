import { test } from "@playwright/test";

import { expectAuthenticatedShell } from "../helpers/adapters/sso";
import { openAuthenticatedShell } from "../helpers/session";

test.describe("тихий refresh после перезагрузки", () => {
  test("после reload остаёмся в портале без повторного логина", async ({ page }) => {
    test.info().annotations.push({ type: "tc", description: "TC-003" });

    await openAuthenticatedShell(page);

    await page.reload();
    await expectAuthenticatedShell(page);
  });
});
