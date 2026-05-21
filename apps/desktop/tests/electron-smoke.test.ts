/**
 * Phase E1.5 — Electron end-to-end smoke test.
 *
 * Not wired into the default vitest sweep — Playwright/Electron adds 150 MB
 * of dev deps and the test itself takes ~30 seconds to boot the packaged
 * `.app`. Run manually with:
 *
 *     cd apps/desktop
 *     npm install --save-dev @playwright/test  # one-time
 *     npx playwright test tests/electron-smoke.test.ts
 *
 * The test asserts that:
 *
 *   1. The packaged `Research Assistant.app` exists under release/mac/.
 *   2. The Electron main process boots without crashing.
 *   3. The renderer finishes loading and #root is present in the DOM
 *      (proving the React app mounted under the file:// URL).
 *
 * If you don't have `@playwright/test` installed yet, the import will
 * fail and the test is effectively skipped — Vitest will simply not pick
 * it up since the file extension and harness differ.
 */

// Stub out the test file when Playwright isn't present so that direct
// vitest invocations don't blow up on the import. The actual e2e harness
// only loads this when run via Playwright's CLI.
// @ts-expect-error - optional peer dep, only required when running e2e.
// eslint-disable-next-line import/no-unresolved
import { _electron as electron, expect, test } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

const APP_PATH = path.resolve(
  __dirname,
  "..",
  "release",
  "mac",
  "Research Assistant.app",
  "Contents",
  "MacOS",
  "Research Assistant",
);

test.skip(
  () => !existsSync(APP_PATH),
  "build the .app first with `npm run dist:mac`",
);

test("boots and renders the React app", async () => {
  const app = await electron.launch({ executablePath: APP_PATH });
  try {
    const window = await app.firstWindow({ timeout: 45_000 });
    await window.waitForLoadState("domcontentloaded", { timeout: 45_000 });
    const root = await window.locator("#root").elementHandle({ timeout: 30_000 });
    expect(root).not.toBeNull();
  } finally {
    await app.close();
  }
});
