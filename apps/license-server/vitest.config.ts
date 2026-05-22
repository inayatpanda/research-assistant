// Phase L1a — Vitest config for the licence server.
//
// Tests run in a plain Node env against a hand-rolled in-memory D1
// fake (test/helpers/fakeD1.ts). This keeps the test loop fast and avoids
// the overhead of `@cloudflare/vitest-pool-workers` for the simple CRUD
// flows we're verifying. The Worker code only uses `crypto.subtle` /
// `crypto.randomUUID` / `fetch` (all available in modern Node).

import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    globals: false,
    pool: "forks",
  },
});
