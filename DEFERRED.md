# Deferred Features

Features and improvements deliberately punted past v1. Each entry is a
**YAGNI call** I made during the build — not a TODO, not a bug, just
"this would be nice but isn't worth doing now."

Format: `[date] description · phase it came up · why deferred`

---

## Already-decided deferrals (from design spec §13)

- Real authentication / multi-user (schema-ready, UI deferred) · spec · single-user faster path
- Cloud storage (adapter ready, impl deferred) · spec · user wants local-first
- PubMed direct search import · spec · v2 idea
- OCR for scanned PDFs · spec · v2 idea
- Journal submission checker · spec · v2 idea
- Collaboration / co-author annotations · spec · v2 idea
- Version history / snapshots · spec · v2 idea
- Mobile PDF highlighting on phones · spec · bad UX on small screens
- Vercel / cloud deploy · spec · user chose local-only
- Voice-to-text · spec · user opted out
- Electron desktop packaging (Phase 9) · spec · user-gated, not in autonomous run

## Discovered during build

- [2026-05-17] Migrate `google-generativeai` → `google.genai` SDK · phase 2 build · old SDK works but deprecated; tests pass and behaviour is identical. Migrating now would mean rewriting `real_gemini_client.py`. Scheduled for after Phase 8 polish. The provider boundary (GeminiClient port) means the migration is just swapping the client adapter.
- [2026-05-19] Bayesian alternatives (t-test / ANOVA / regression via bambi) · MP13.6 preflight · `pip install bambi pymc` fails on macOS because `llvmlite` can't build a wheel against the system Xcode CLT (clang errors during numba's pytensor chain). The frequentist stack (statsmodels MixedLM / GLM / GEE / bootstrap / permutation / TOST) shipped in MP13 covers the common-case Bayesian alternatives. Re-attempt when either (a) bambi publishes macOS wheels for Python 3.12 that don't require local llvm compilation, or (b) the user installs `brew install llvm` and we can build pymc against it. Add as a new mini-phase MP16-Bayesian when ready.
