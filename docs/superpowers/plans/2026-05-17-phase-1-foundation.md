# Phase 1 — Foundation & Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Running monorepo with React+Vite+TS frontend and FastAPI+SQLite backend. Sidebar shell with 6 nav routes, Dashboard with project create/list, Settings page, `/health` endpoint reporting AI/storage/DB status. Persisted projects survive reload.

**Architecture:** Two-process monorepo (`apps/web` on :5173, `apps/api` on :8787) booted with `concurrently`. Repository + storage + AI adapter layers per spec §4. SQLite via SQLAlchemy 2.0 async. Tailwind+shadcn+Framer Motion frontend. All design tokens from `tokens.ts`.

**Tech Stack:** Node 26 / npm 11; Python 3.12 (Homebrew); React 18 + TypeScript 5; Vite 5; Tailwind CSS 3; shadcn/ui; Framer Motion; React Router 6; TanStack Query 5; Zustand; React Hook Form + Zod; Lucide React; Tremor 3; FastAPI; SQLAlchemy 2.0 async + aiosqlite; Alembic; Pydantic 2 + pydantic-settings; pytest + httpx.

**Verification:** After each task that compiles or runs, the step explicitly says what command and what output to expect. UI tasks include a `chrome-devtools-mcp` browser check.

---

## File Structure (created by this plan)

```
research-assistant/
├── package.json                      # workspace orchestrator
├── package-lock.json
├── README.md                          # how to run + structure
├── .env                               # (already present — gitignored)
├── .env.example                       # (already present)
├── .gitignore                         # (already present)
├── apps/
│   ├── web/
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json / tsconfig.node.json
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.cjs
│   │   ├── index.html
│   │   ├── components.json            # shadcn config
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── index.css
│   │       ├── lib/
│   │       │   ├── tokens.ts          # design tokens (single source of truth)
│   │       │   ├── motion.ts          # 6 named transitions
│   │       │   ├── utils.ts           # cn() helper (shadcn)
│   │       │   ├── api.ts             # axios client + zod runtime types
│   │       │   └── query.ts           # TanStack Query client
│   │       ├── components/
│   │       │   ├── ui/                # shadcn primitives (generated)
│   │       │   ├── layout/
│   │       │   │   ├── AppShell.tsx
│   │       │   │   ├── Sidebar.tsx
│   │       │   │   ├── Topbar.tsx
│   │       │   │   └── nav-items.ts
│   │       │   └── projects/
│   │       │       ├── ProjectCard.tsx
│   │       │       └── CreateProjectDialog.tsx
│   │       └── routes/
│   │           ├── DashboardPage.tsx
│   │           ├── LibraryPage.tsx           # stub for Phase 2
│   │           ├── ReaderPage.tsx            # stub for Phase 3
│   │           ├── CompilePage.tsx           # stub for Phase 4
│   │           ├── ManuscriptPage.tsx        # stub for Phase 5
│   │           ├── StatisticsPage.tsx        # stub for Phase 6
│   │           └── SettingsPage.tsx
│   └── api/
│       ├── pyproject.toml
│       ├── alembic.ini
│       ├── .python-version             # 3.12
│       ├── alembic/
│       │   ├── env.py
│       │   ├── script.py.mako
│       │   └── versions/
│       │       └── 0001_initial.py     # generated
│       ├── src/research_api/
│       │   ├── __init__.py
│       │   ├── main.py                 # FastAPI app
│       │   ├── settings.py             # pydantic-settings
│       │   ├── container.py            # DI
│       │   ├── db/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # SQLAlchemy Base + engine
│       │   │   └── models.py           # ORM models
│       │   ├── schemas/
│       │   │   ├── __init__.py
│       │   │   ├── project.py          # Pydantic in/out
│       │   │   └── health.py
│       │   ├── repositories/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # Protocol
│       │   │   └── projects.py         # Sqlite impl
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── ai/
│       │   │   │   ├── __init__.py
│       │   │   │   └── base.py         # AIProvider Protocol stub
│       │   │   └── storage/
│       │   │       ├── __init__.py
│       │   │       └── base.py         # FileStorage Protocol stub
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       └── projects.py
│       └── tests/
│           ├── conftest.py
│           ├── test_settings.py
│           ├── test_project_repository.py
│           ├── test_health_route.py
│           └── test_projects_route.py
├── scripts/
│   ├── start-dev.sh                    # boots both servers
│   └── init-db.sh                      # alembic upgrade head
└── data/                               # gitignored
    └── files/                          # created at runtime
```

---

## Task 0: Pre-flight — Install Python 3.12

**Files:** none (system install)

- [ ] **Step 1: Check Homebrew, install Python 3.12 if missing**

Run:
```bash
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
```
Expected: either silent (already installed) or full brew install completing without error.

- [ ] **Step 2: Verify python3.12 binary exists**

Run:
```bash
/usr/local/opt/python@3.12/bin/python3.12 --version || /opt/homebrew/opt/python@3.12/bin/python3.12 --version
```
Expected: `Python 3.12.x`.

- [ ] **Step 3: Confirm Xcode CLT (needed for scipy/lifelines wheels-from-source fallback)**

Run:
```bash
xcode-select -p
```
Expected: `/Library/Developer/CommandLineTools` or `/Applications/Xcode.app/Contents/Developer`.

---

## Task 1: Bootstrap repo workspace

**Files:**
- Create: `package.json`
- Create: `README.md`
- Create: `scripts/start-dev.sh`
- Create: `scripts/init-db.sh`

- [ ] **Step 1: Create root `package.json`**

```json
{
  "name": "research-assistant",
  "private": true,
  "version": "0.0.1",
  "description": "Research Manuscript Assistant — local-first writing tool for medical researchers.",
  "engines": { "node": ">=22" },
  "scripts": {
    "dev": "concurrently -n web,api -c blue,green \"npm:dev:web\" \"npm:dev:api\"",
    "dev:web": "npm --prefix apps/web run dev",
    "dev:api": "bash -c 'cd apps/api && .venv/bin/uvicorn research_api.main:app --reload --host 127.0.0.1 --port 8787'",
    "build:web": "npm --prefix apps/web run build",
    "test:web": "npm --prefix apps/web run test",
    "test:api": "bash -c 'cd apps/api && .venv/bin/pytest -q'",
    "test": "npm run test:api && npm run test:web",
    "init-db": "bash scripts/init-db.sh",
    "lint:web": "npm --prefix apps/web run lint"
  },
  "devDependencies": {
    "concurrently": "^9.0.0"
  }
}
```

- [ ] **Step 2: Install root deps**

Run: `npm install`
Expected: `concurrently` installed; `package-lock.json` created.

- [ ] **Step 3: Create README.md**

```markdown
# Research Manuscript Assistant

Local-first web app for medical researchers writing manuscripts.

## Run

\`\`\`bash
npm install                          # one-time
cd apps/web && npm install && cd ../..
bash scripts/init-db.sh              # one-time DB setup
npm run dev                          # boots web (:5173) + api (:8787)
\`\`\`

## Structure

- `apps/web` — React + Vite + TS + Tailwind + shadcn
- `apps/api` — FastAPI + SQLAlchemy + SQLite
- `data/` — local DB and uploaded files (gitignored)
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — phased implementation plans

## Tracking files

- `BUILD_LOG.md` — narrative of each phase
- `POLISH.md` — UX/visual nits to revisit
- `DEFERRED.md` — features deferred past v1
- `DECISIONS.md` — lightweight ADRs
- `QUESTIONS.md` — open questions with chosen defaults
```

- [ ] **Step 4: Create `scripts/start-dev.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec npm run dev
```

Run: `chmod +x scripts/start-dev.sh`

- [ ] **Step 5: Create `scripts/init-db.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/files
cd apps/api
.venv/bin/alembic upgrade head
echo "DB ready at data/research.db"
```

Run: `chmod +x scripts/init-db.sh`

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json README.md scripts/
git commit -m "chore(phase1): bootstrap monorepo orchestration"
```

---

## Task 2: Scaffold `apps/web` with Vite + React + TS + Tailwind

**Files:**
- Create: `apps/web/` (full Vite scaffold)
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/postcss.config.cjs`
- Modify: `apps/web/src/index.css`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Scaffold Vite app non-interactively**

Run:
```bash
npm create vite@latest apps/web -- --template react-ts -y
```
Expected: `apps/web/` created with React+TS template.

- [ ] **Step 2: Install web deps**

Run:
```bash
cd apps/web && npm install && cd ../..
```
Expected: `node_modules/` populated, lockfile written.

- [ ] **Step 3: Install Tailwind v3 + PostCSS**

Run:
```bash
cd apps/web && npm install -D tailwindcss@3 postcss autoprefixer && cd ../..
```
Expected: deps appear in `apps/web/package.json` devDependencies.

- [ ] **Step 4: Create `apps/web/tailwind.config.ts`**

```ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        sidebar: { DEFAULT: '#0F1117', foreground: '#FAFAFA' },
        workspace: '#FAFAFA',
        accent: { DEFAULT: '#2563EB', hover: '#1D4ED8', tint: '#EFF6FF', foreground: '#FFFFFF' },
        ai: { DEFAULT: '#7C3AED', tint: 'rgba(124,58,237,0.08)', ring: 'rgba(124,58,237,0.35)' },
        highlight: {
          intro: '#EF4444',
          method: '#3B82F6',
          results: '#22C55E',
          discussion: '#EAB308',
        },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['Source Serif 4', 'Source Serif Pro', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: { shimmer: 'shimmer 1.4s linear infinite' },
    },
  },
  plugins: [],
} satisfies Config
```

- [ ] **Step 5: Create `apps/web/postcss.config.cjs`**

```js
module.exports = {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
```

- [ ] **Step 6: Replace `apps/web/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 6% 5%;
    --card: 0 0% 100%;
    --card-foreground: 240 6% 5%;
    --popover: 0 0% 100%;
    --popover-foreground: 240 6% 5%;
    --primary: 222 89% 53%;
    --primary-foreground: 0 0% 100%;
    --secondary: 240 5% 96%;
    --secondary-foreground: 240 6% 10%;
    --muted: 240 5% 96%;
    --muted-foreground: 240 4% 46%;
    --accent: 222 89% 53%;
    --accent-foreground: 0 0% 100%;
    --destructive: 0 72% 51%;
    --destructive-foreground: 0 0% 100%;
    --border: 220 13% 91%;
    --input: 220 13% 91%;
    --ring: 222 89% 53%;
    --radius: 0.5rem;
  }

  * { @apply border-border; }
  body { @apply bg-workspace text-foreground antialiased; font-family: theme('fontFamily.sans'); }
}
```

- [ ] **Step 7: Replace `apps/web/src/App.tsx` with a temporary smoke screen**

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-workspace text-foreground">
      <div className="p-8">
        <h1 className="text-2xl font-semibold">Research Manuscript Assistant</h1>
        <p className="mt-2 text-sm text-muted-foreground">Phase 1 — scaffold check</p>
        <div className="mt-4 flex gap-2">
          <div className="h-6 w-6 rounded bg-highlight-intro" />
          <div className="h-6 w-6 rounded bg-highlight-method" />
          <div className="h-6 w-6 rounded bg-highlight-results" />
          <div className="h-6 w-6 rounded bg-highlight-discussion" />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 8: Run dev server and verify**

Run (in background, then check):
```bash
cd apps/web && npm run dev &
sleep 4
curl -s http://127.0.0.1:5173 | head -5
```
Expected: HTML response containing `<title>Vite + React + TS</title>` or similar (the SSR-less index). No errors.

Stop the dev server: `pkill -f "vite" || true`.

- [ ] **Step 9: Commit**

```bash
git add apps/web/
git commit -m "feat(phase1): scaffold apps/web with Vite + React + TS + Tailwind"
```

---

## Task 3: Lock design tokens & motion vocabulary

**Files:**
- Create: `apps/web/src/lib/tokens.ts`
- Create: `apps/web/src/lib/motion.ts`
- Create: `apps/web/src/lib/utils.ts`

- [ ] **Step 1: Create `apps/web/src/lib/utils.ts`**

```ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 2: Install clsx + tailwind-merge**

Run: `cd apps/web && npm install clsx tailwind-merge && cd ../..`

- [ ] **Step 3: Create `apps/web/src/lib/tokens.ts`**

```ts
export const highlightColors = {
  intro:      { solid: '#EF4444', fill: 'rgba(239,68,68,0.22)',  ring: 'rgba(239,68,68,0.55)' },
  method:     { solid: '#3B82F6', fill: 'rgba(59,130,246,0.22)', ring: 'rgba(59,130,246,0.55)' },
  results:    { solid: '#22C55E', fill: 'rgba(34,197,94,0.22)',  ring: 'rgba(34,197,94,0.55)' },
  discussion: { solid: '#EAB308', fill: 'rgba(234,179,8,0.22)',  ring: 'rgba(234,179,8,0.55)' },
} as const

export type HighlightColor = keyof typeof highlightColors

export const sectionLabels: Record<HighlightColor, string> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

export const studyTypes = [
  'Before/After Intervention',
  'Outcome Study',
  'Risk Factor Analysis',
  'Group Comparison',
  'Prospective Cohort',
  'Retrospective Case Series',
  'Systematic Review',
] as const
export type StudyType = (typeof studyTypes)[number]

export const citationStyles = ['vancouver', 'apa', 'harvard'] as const
export type CitationStyle = (typeof citationStyles)[number]

export const aiProviders = ['gemini', 'claude', 'openai'] as const
export type AIProviderName = (typeof aiProviders)[number]
```

- [ ] **Step 4: Create `apps/web/src/lib/motion.ts`**

```ts
import type { Transition, Variants } from 'framer-motion'

const standard: Transition = { duration: 0.2, ease: [0.2, 0.0, 0.0, 1.0] }
const expressive: Transition = { duration: 0.32, ease: [0.16, 1, 0.3, 1] }

export const pageEnter: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.24, ease: [0.2, 0, 0, 1] } },
  exit:    { opacity: 0, y: -4, transition: standard },
}

export const cardEnter = (i = 0): Variants => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { ...standard, delay: i * 0.03 } },
})

export const modalIn: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: expressive },
  exit:    { opacity: 0, scale: 0.96, transition: standard },
}

export const sidebarSlide: Variants = {
  initial: { x: -20, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] } },
}

export const aiSuggestionEnter: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: expressive },
}

export const highlightBloom: Variants = {
  initial: { opacity: 0, scale: 1.04 },
  animate: { opacity: 1, scale: 1, transition: expressive },
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/
git commit -m "feat(phase1): design tokens + motion vocabulary"
```

---

## Task 4: Install shadcn/ui + initial primitives (non-interactive)

**Files:**
- Create: `apps/web/components.json`
- Create: `apps/web/src/components/ui/*` (generated)
- Modify: `apps/web/tsconfig.json`, `apps/web/vite.config.ts` (path aliases)

- [ ] **Step 1: Add path alias `@/*` to `apps/web/tsconfig.json`**

Open `apps/web/tsconfig.json` (or its referenced project file `tsconfig.app.json`). Inside `compilerOptions`, add:

```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

- [ ] **Step 2: Add same alias to `apps/web/vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: { host: '127.0.0.1', port: 5173 },
})
```

- [ ] **Step 3: Initialise shadcn non-interactively**

Run (from `apps/web`):
```bash
cd apps/web && npx -y shadcn@latest init --yes --defaults --base-color slate && cd ../..
```
Expected: `apps/web/components.json` exists; `apps/web/src/components/ui/` directory created.

- [ ] **Step 4: Add the Phase 1 primitives**

Run (from `apps/web`):
```bash
cd apps/web && npx -y shadcn@latest add -y button card dialog input label select textarea sonner tooltip badge skeleton separator scroll-area && cd ../..
```
Expected: each primitive added under `src/components/ui/`.

- [ ] **Step 5: Sanity check imports compile**

Run: `cd apps/web && npx tsc --noEmit && cd ../..`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/
git commit -m "feat(phase1): install shadcn + initial primitives (button, card, dialog, input, label, select, textarea, sonner, tooltip, badge, skeleton, separator, scroll-area)"
```

---

## Task 5: Install support libraries

**Files:** modify `apps/web/package.json`

- [ ] **Step 1: Install runtime deps**

Run:
```bash
cd apps/web && npm install \
  framer-motion@^11 \
  react-router-dom@^6 \
  lucide-react \
  @tremor/react \
  @tanstack/react-query \
  zustand \
  react-hook-form \
  zod \
  @hookform/resolvers \
  axios && cd ../..
```
Expected: all packages added to `dependencies`.

- [ ] **Step 2: Confirm versions line up**

Run: `cd apps/web && npm ls framer-motion react-router-dom @tanstack/react-query zustand axios | head -20 && cd ../..`
Expected: no version conflicts, no peer-dep errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json
git commit -m "feat(phase1): install framer-motion, react-router, lucide, tremor, tanstack-query, zustand, react-hook-form, zod, axios"
```

---

## Task 6: Bootstrap `apps/api` (FastAPI + SQLAlchemy + Alembic)

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/.python-version`
- Create: `apps/api/src/research_api/__init__.py`
- Create: `apps/api/src/research_api/main.py` (minimal)
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/conftest.py` (minimal)

- [ ] **Step 1: Create `apps/api/.python-version`**

```
3.12
```

- [ ] **Step 2: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "research-api"
version = "0.0.1"
description = "Research Manuscript Assistant API"
requires-python = ">=3.12,<3.14"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy[asyncio]>=2.0.30",
  "aiosqlite>=0.20",
  "alembic>=1.13",
  "pydantic>=2.7",
  "pydantic-settings>=2.4",
  "python-multipart>=0.0.9",
  "httpx>=0.27",
  "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "anyio>=4",
  "ruff>=0.6",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 3: Create venv and install deps**

Run:
```bash
cd apps/api && \
  /usr/local/opt/python@3.12/bin/python3.12 -m venv .venv 2>/dev/null || \
  /opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"
cd ../..
```
Expected: `.venv/` created, all deps installed without error.

- [ ] **Step 4: Create empty package init**

```bash
mkdir -p apps/api/src/research_api apps/api/tests
touch apps/api/src/research_api/__init__.py apps/api/tests/__init__.py
```

- [ ] **Step 5: Create minimal `apps/api/src/research_api/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Research Manuscript Assistant API")

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Create `apps/api/tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from research_api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

- [ ] **Step 7: Smoke test**

Run:
```bash
cd apps/api && .venv/bin/uvicorn research_api.main:app --host 127.0.0.1 --port 8787 &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8787/ping
echo ""
kill $SERVER_PID
cd ../..
```
Expected: `{"status":"ok"}`.

- [ ] **Step 8: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): scaffold apps/api with FastAPI + venv + smoke /ping endpoint"
```

---

## Task 7: Settings module (env loader) — TDD

**Files:**
- Create: `apps/api/src/research_api/settings.py`
- Create: `apps/api/tests/test_settings.py`

- [ ] **Step 1: Write failing test `apps/api/tests/test_settings.py`**

```python
import os
from pathlib import Path
from research_api.settings import Settings


def test_settings_load_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    s = Settings()
    assert s.gemini_api_key == "test-key"
    assert s.data_dir == Path(str(tmp_path))
    assert s.ai_provider_default == "gemini"
    assert s.storage_backend == "local"
    assert s.local_user_id == "local-user"


def test_settings_missing_key_falls_back(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = Settings()
    assert s.gemini_api_key is None
```

- [ ] **Step 2: Run test, expect failure**

Run: `cd apps/api && .venv/bin/pytest tests/test_settings.py -v && cd ../..`
Expected: ImportError or ModuleNotFoundError for `research_api.settings`.

- [ ] **Step 3: Implement `apps/api/src/research_api/settings.py`**

```python
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../../.env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ai_provider_default: Literal["gemini", "claude", "openai"] = "gemini"
    gemini_api_key: str | None = None
    claude_api_key: str | None = None
    openai_api_key: str | None = None

    data_dir: Path = Field(default=Path("./data"))
    sqlite_url: str = "sqlite+aiosqlite:///./data/research.db"
    storage_backend: Literal["local", "supabase"] = "local"

    local_user_id: str = "local-user"

    api_host: str = "127.0.0.1"
    api_port: int = 8787
    api_signing_secret: str = "change-me-before-deploy"

    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test, expect pass**

Run: `cd apps/api && .venv/bin/pytest tests/test_settings.py -v && cd ../..`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): settings loader with .env (gemini key + data dir + sqlite + user_id)"
```

---

## Task 8: DB base + Project model + Alembic

**Files:**
- Create: `apps/api/src/research_api/db/__init__.py`
- Create: `apps/api/src/research_api/db/base.py`
- Create: `apps/api/src/research_api/db/models.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/script.py.mako`
- Create: `apps/api/alembic/versions/0001_initial.py`

- [ ] **Step 1: Create `apps/api/src/research_api/db/base.py`**

```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, echo=False, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

- [ ] **Step 2: Create `apps/api/src/research_api/db/models.py`** (only Project for Phase 1; rest land in their respective phases)

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from uuid import uuid4

from .base import Base


def new_id() -> str:
    return uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    study_type: Mapped[str] = mapped_column(String(64), nullable=False)
    citation_style: Mapped[str] = mapped_column(String(32), default="vancouver", nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(32), default="gemini", nullable=False)
    target_journal: Mapped[str | None] = mapped_column(Text, nullable=True)
    prospero_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clinicaltrials_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 3: Create `apps/api/src/research_api/db/__init__.py`**

```python
from .base import Base, make_engine, make_session_factory
from .models import Project, new_id

__all__ = ["Base", "make_engine", "make_session_factory", "Project", "new_id"]
```

- [ ] **Step 4: Create `apps/api/alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
sqlalchemy.url = sqlite:///../data/research.db
file_template = %%(rev)s_%%(slug)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Note: Alembic uses the **sync** SQLAlchemy URL `sqlite:///...` (not `+aiosqlite`) for migrations. The async URL is only used by the running app.

- [ ] **Step 5: Create `apps/api/alembic/env.py`**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from research_api.db.base import Base
from research_api.db import models  # noqa: F401  ensure model import

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Create `apps/api/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7: Generate baseline migration**

Run:
```bash
mkdir -p data apps/api/alembic/versions
cd apps/api && .venv/bin/alembic revision --autogenerate -m "initial: projects" -r 0001 && cd ../..
```
Expected: `apps/api/alembic/versions/0001_initial_projects.py` created with a `create_table('projects', ...)` op.

- [ ] **Step 8: Apply migration**

Run:
```bash
cd apps/api && .venv/bin/alembic upgrade head && cd ../..
ls -la data/research.db
```
Expected: file `data/research.db` exists (at the project root because alembic.ini points to `../data/research.db`).

- [ ] **Step 9: Verify schema**

Run:
```bash
.venv_dummy=apps/api/.venv
$.venv_dummy/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect('data/research.db')
print([r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")])
print([r for r in con.execute("PRAGMA table_info(projects)")])
PY
```

Use direct path instead:
```bash
apps/api/.venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect('data/research.db')
print(sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")))
print(list(con.execute("PRAGMA table_info(projects)")))
PY
```
Expected: tables include `projects` and `alembic_version`; columns include id, user_id, title, study_type, citation_style, ai_provider, etc.

- [ ] **Step 10: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): SQLAlchemy Project model + alembic baseline migration"
```

---

## Task 9: Pydantic schemas for Project

**Files:**
- Create: `apps/api/src/research_api/schemas/__init__.py`
- Create: `apps/api/src/research_api/schemas/project.py`
- Create: `apps/api/src/research_api/schemas/health.py`

- [ ] **Step 1: Create `apps/api/src/research_api/schemas/__init__.py`**

```python
from .project import ProjectCreate, ProjectRead, ProjectUpdate
from .health import HealthResponse, ProviderStatus

__all__ = ["ProjectCreate", "ProjectRead", "ProjectUpdate", "HealthResponse", "ProviderStatus"]
```

- [ ] **Step 2: Create `apps/api/src/research_api/schemas/project.py`**

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

StudyType = Literal[
    "Before/After Intervention",
    "Outcome Study",
    "Risk Factor Analysis",
    "Group Comparison",
    "Prospective Cohort",
    "Retrospective Case Series",
    "Systematic Review",
]

CitationStyle = Literal["vancouver", "apa", "harvard"]
AIProviderName = Literal["gemini", "claude", "openai"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    study_type: StudyType
    citation_style: CitationStyle = "vancouver"
    ai_provider: AIProviderName = "gemini"
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    study_type: StudyType | None = None
    citation_style: CitationStyle | None = None
    ai_provider: AIProviderName | None = None
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    study_type: StudyType
    citation_style: CitationStyle
    ai_provider: AIProviderName
    target_journal: str | None
    prospero_number: str | None
    clinicaltrials_number: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: Create `apps/api/src/research_api/schemas/health.py`**

```python
from typing import Literal
from pydantic import BaseModel


class ProviderStatus(BaseModel):
    ok: bool
    active_model: str | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    db_ok: bool
    storage_backend: str
    ai_providers: dict[str, ProviderStatus]
```

- [ ] **Step 4: Compile check**

Run: `cd apps/api && .venv/bin/python -c "from research_api.schemas import ProjectCreate, ProjectRead, HealthResponse; print('ok')" && cd ../..`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): pydantic schemas for Project + Health"
```

---

## Task 10: ProjectRepository — TDD

**Files:**
- Create: `apps/api/src/research_api/repositories/__init__.py`
- Create: `apps/api/src/research_api/repositories/base.py`
- Create: `apps/api/src/research_api/repositories/projects.py`
- Create: `apps/api/tests/test_project_repository.py`

- [ ] **Step 1: Update `apps/api/tests/conftest.py` with a project-DB fixture**

Replace the existing conftest content:

```python
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import ASGITransport, AsyncClient

from research_api.db.base import Base, make_engine, make_session_factory


@pytest_asyncio.fixture
async def session(tmp_path: Path) -> AsyncSession:
    url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = make_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()
```

- [ ] **Step 2: Write failing tests `apps/api/tests/test_project_repository.py`**

```python
import pytest
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.project import ProjectCreate


@pytest.mark.asyncio
async def test_create_and_get(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="My Study", study_type="Outcome Study"),
        user_id="user-a",
    )
    assert created.id
    assert created.user_id == "user-a"
    assert created.title == "My Study"
    assert created.citation_style == "vancouver"

    fetched = await repo.get(created.id, user_id="user-a")
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_rejects_other_user(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="Owned", study_type="Group Comparison"),
        user_id="user-a",
    )
    assert await repo.get(created.id, user_id="user-b") is None


@pytest.mark.asyncio
async def test_list_for_user(session):
    repo = SqliteProjectRepository(session)
    await repo.create(ProjectCreate(title="A", study_type="Outcome Study"), user_id="user-a")
    await repo.create(ProjectCreate(title="B", study_type="Outcome Study"), user_id="user-a")
    await repo.create(ProjectCreate(title="C", study_type="Outcome Study"), user_id="user-b")
    user_a_projects = await repo.list_for_user("user-a")
    assert len(user_a_projects) == 2
    assert {p.title for p in user_a_projects} == {"A", "B"}


@pytest.mark.asyncio
async def test_delete(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(ProjectCreate(title="X", study_type="Outcome Study"), user_id="user-a")
    await repo.delete(created.id, user_id="user-a")
    assert await repo.get(created.id, user_id="user-a") is None
```

- [ ] **Step 3: Run, expect import failure**

Run: `cd apps/api && .venv/bin/pytest tests/test_project_repository.py -v && cd ../..`
Expected: ModuleNotFoundError for repositories.

- [ ] **Step 4: Create `apps/api/src/research_api/repositories/base.py`**

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class Repository(Protocol):
    """Marker for repository implementations."""
    ...
```

- [ ] **Step 5: Create `apps/api/src/research_api/repositories/projects.py`**

```python
from typing import Protocol
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Project, new_id
from ..schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository(Protocol):
    async def create(self, data: ProjectCreate, user_id: str) -> Project: ...
    async def get(self, project_id: str, user_id: str) -> Project | None: ...
    async def list_for_user(self, user_id: str) -> list[Project]: ...
    async def update(self, project_id: str, patch: ProjectUpdate, user_id: str) -> Project | None: ...
    async def delete(self, project_id: str, user_id: str) -> None: ...


class SqliteProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: ProjectCreate, user_id: str) -> Project:
        project = Project(id=new_id(), user_id=user_id, **data.model_dump())
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get(self, project_id: str, user_id: str) -> Project | None:
        stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Project]:
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, project_id: str, patch: ProjectUpdate, user_id: str) -> Project | None:
        existing = await self.get(project_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, project_id: str, user_id: str) -> None:
        stmt = sa_delete(Project).where(Project.id == project_id, Project.user_id == user_id)
        await self.session.execute(stmt)
        await self.session.commit()
```

- [ ] **Step 6: Create `apps/api/src/research_api/repositories/__init__.py`**

```python
from .projects import ProjectRepository, SqliteProjectRepository

__all__ = ["ProjectRepository", "SqliteProjectRepository"]
```

- [ ] **Step 7: Install `pytest-asyncio` (already in dev deps) and run tests**

Run: `cd apps/api && .venv/bin/pytest tests/test_project_repository.py -v && cd ../..`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): ProjectRepository protocol + SQLite impl + user-isolation tests"
```

---

## Task 11: DI container

**Files:**
- Create: `apps/api/src/research_api/container.py`

- [ ] **Step 1: Create `apps/api/src/research_api/container.py`**

```python
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from .db.base import make_engine, make_session_factory
from .settings import Settings, get_settings


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


_container: Container | None = None


def build_container(settings: Settings | None = None) -> Container:
    s = settings or get_settings()
    engine = make_engine(s.sqlite_url)
    factory = make_session_factory(engine)
    return Container(settings=s, engine=engine, session_factory=factory)


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def set_container(c: Container) -> None:
    """Test hook to override the global container."""
    global _container
    _container = c
```

- [ ] **Step 2: Smoke check**

Run: `cd apps/api && .venv/bin/python -c "from research_api.container import build_container; c=build_container(); print(c.settings.local_user_id)" && cd ../..`
Expected: `local-user`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): DI container wiring settings + engine + session factory"
```

---

## Task 12: `/health` route — TDD

**Files:**
- Create: `apps/api/src/research_api/routes/__init__.py`
- Create: `apps/api/src/research_api/routes/health.py`
- Modify: `apps/api/src/research_api/main.py`
- Create: `apps/api/tests/test_health_route.py`

- [ ] **Step 1: Write failing test `apps/api/tests/test_health_route.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_health_returns_200_with_provider_status(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["db_ok"] is True
    assert body["storage_backend"] == "local"
    assert "gemini" in body["ai_providers"]
    assert body["ai_providers"]["gemini"]["ok"] is True
    assert body["version"]
```

Also update `conftest.py` so the test app uses a tmp DB (so `db_ok` checks against a real reachable DB):

Append to `apps/api/tests/conftest.py`:

```python
@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from research_api.container import build_container, set_container
    from research_api.main import app
    container = build_container()
    async with container.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_container(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await container.engine.dispose()
```

Remove the old simpler `client` fixture if present (it's replaced).

- [ ] **Step 2: Run, expect failure**

Run: `cd apps/api && .venv/bin/pytest tests/test_health_route.py -v && cd ../..`
Expected: 404 (route not present yet) or import error.

- [ ] **Step 3: Create `apps/api/src/research_api/routes/__init__.py`**

```python
from . import health, projects

__all__ = ["health", "projects"]
```

(`projects` is created in the next task — for now, you can defer this import or split. **Decision:** create it now as an empty placeholder so the import works.)

Create `apps/api/src/research_api/routes/projects.py` with a stub:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])
```

- [ ] **Step 4: Create `apps/api/src/research_api/routes/health.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..container import Container, get_container
from ..schemas.health import HealthResponse, ProviderStatus

router = APIRouter(tags=["meta"])


async def _check_db(container: Container) -> bool:
    try:
        async with container.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_providers(container: Container) -> dict[str, ProviderStatus]:
    s = container.settings
    return {
        "gemini": (
            ProviderStatus(ok=True, active_model=None)
            if s.gemini_api_key
            else ProviderStatus(ok=False, reason="no key")
        ),
        "claude": (
            ProviderStatus(ok=True) if s.claude_api_key else ProviderStatus(ok=False, reason="no key")
        ),
        "openai": (
            ProviderStatus(ok=True) if s.openai_api_key else ProviderStatus(ok=False, reason="no key")
        ),
    }


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    db_ok = await _check_db(container)
    providers = _check_providers(container)
    any_ai_ok = any(p.ok for p in providers.values())
    status: str = "ok" if (db_ok and any_ai_ok) else ("degraded" if db_ok else "down")
    return HealthResponse(
        status=status,  # type: ignore[arg-type]
        version="0.0.1",
        db_ok=db_ok,
        storage_backend=container.settings.storage_backend,
        ai_providers=providers,
    )
```

- [ ] **Step 5: Update `apps/api/src/research_api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .container import get_container
from .routes.health import router as health_router
from .routes.projects import router as projects_router

app = FastAPI(title="Research Manuscript Assistant API", version="0.0.1")

_settings = get_container().settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(projects_router, prefix="/api")
```

- [ ] **Step 6: Run, expect pass**

Run: `cd apps/api && .venv/bin/pytest tests/test_health_route.py -v && cd ../..`
Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): /health route with per-provider status + db check + CORS"
```

---

## Task 13: `/api/projects` routes — TDD

**Files:**
- Modify: `apps/api/src/research_api/routes/projects.py`
- Create: `apps/api/tests/test_projects_route.py`

- [ ] **Step 1: Write failing tests `apps/api/tests/test_projects_route.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    r = await client.post(
        "/api/projects",
        json={"title": "Hip Outcomes 2026", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"]
    assert body["user_id"] == "local-user"
    assert body["title"] == "Hip Outcomes 2026"
    assert body["citation_style"] == "vancouver"
    assert body["ai_provider"] == "gemini"


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post(
        "/api/projects",
        json={"title": "A", "study_type": "Outcome Study"},
    )
    await client.post(
        "/api/projects",
        json={"title": "B", "study_type": "Systematic Review"},
    )
    r = await client.get("/api/projects")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert {p["title"] for p in body} == {"A", "B"}


@pytest.mark.asyncio
async def test_get_project(client):
    created = (
        await client.post(
            "/api/projects", json={"title": "Solo", "study_type": "Outcome Study"}
        )
    ).json()
    r = await client.get(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_unknown_project_returns_404(client):
    r = await client.get("/api/projects/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_invalid_study_type(client):
    r = await client.post(
        "/api/projects", json={"title": "Bad", "study_type": "NotARealType"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_project(client):
    created = (
        await client.post(
            "/api/projects", json={"title": "Del", "study_type": "Outcome Study"}
        )
    ).json()
    r = await client.delete(f"/api/projects/{created['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{created['id']}")
    assert r2.status_code == 404
```

- [ ] **Step 2: Run, expect failures**

Run: `cd apps/api && .venv/bin/pytest tests/test_projects_route.py -v && cd ../..`
Expected: 405/404/etc. — the route handlers don't exist yet.

- [ ] **Step 3: Implement `apps/api/src/research_api/routes/projects.py` fully**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.projects import SqliteProjectRepository
from ..schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


async def _session(container: Container = Depends(get_container)):
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
):
    repo = SqliteProjectRepository(session)
    return await repo.create(data, user_id)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
):
    repo = SqliteProjectRepository(session)
    return await repo.list_for_user(user_id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
):
    repo = SqliteProjectRepository(session)
    found = await repo.get(project_id, user_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return found


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    patch: ProjectUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
):
    repo = SqliteProjectRepository(session)
    updated = await repo.update(project_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
):
    repo = SqliteProjectRepository(session)
    await repo.delete(project_id, user_id)
    return None
```

- [ ] **Step 4: Run, expect all pass**

Run: `cd apps/api && .venv/bin/pytest tests/test_projects_route.py -v && cd ../..`
Expected: 6 passed.

- [ ] **Step 5: Full backend test sweep**

Run: `cd apps/api && .venv/bin/pytest -q && cd ../..`
Expected: all tests pass (settings + repo + health + projects).

- [ ] **Step 6: Commit**

```bash
git add apps/api/
git commit -m "feat(phase1): /api/projects CRUD routes with user-id isolation"
```

---

## Task 14: Frontend API client

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/query.ts`

- [ ] **Step 1: Create `apps/web/src/lib/api.ts`**

```ts
import axios, { AxiosError } from 'axios'
import { z } from 'zod'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8787'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30_000,
})

api.interceptors.response.use(
  r => r,
  (error: AxiosError) => {
    const message =
      // @ts-expect-error untyped detail field
      error.response?.data?.detail ?? error.message ?? 'Network error'
    return Promise.reject(new Error(typeof message === 'string' ? message : 'Request failed'))
  },
)

// --- Schemas (runtime + types) ---

export const ProjectSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  study_type: z.string(),
  citation_style: z.enum(['vancouver', 'apa', 'harvard']),
  ai_provider: z.enum(['gemini', 'claude', 'openai']),
  target_journal: z.string().nullable(),
  prospero_number: z.string().nullable(),
  clinicaltrials_number: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Project = z.infer<typeof ProjectSchema>

export const ProjectCreateSchema = z.object({
  title: z.string().min(1).max(500),
  study_type: z.enum([
    'Before/After Intervention',
    'Outcome Study',
    'Risk Factor Analysis',
    'Group Comparison',
    'Prospective Cohort',
    'Retrospective Case Series',
    'Systematic Review',
  ]),
  citation_style: z.enum(['vancouver', 'apa', 'harvard']).optional(),
  ai_provider: z.enum(['gemini', 'claude', 'openai']).optional(),
  target_journal: z.string().optional(),
  prospero_number: z.string().optional(),
  clinicaltrials_number: z.string().optional(),
})
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>

export const HealthSchema = z.object({
  status: z.enum(['ok', 'degraded', 'down']),
  version: z.string(),
  db_ok: z.boolean(),
  storage_backend: z.string(),
  ai_providers: z.record(
    z.string(),
    z.object({
      ok: z.boolean(),
      active_model: z.string().nullable().optional(),
      reason: z.string().nullable().optional(),
    }),
  ),
})
export type Health = z.infer<typeof HealthSchema>

// --- Endpoints ---

export const projectsApi = {
  list: async (): Promise<Project[]> => {
    const r = await api.get('/api/projects')
    return z.array(ProjectSchema).parse(r.data)
  },
  get: async (id: string): Promise<Project> => {
    const r = await api.get(`/api/projects/${id}`)
    return ProjectSchema.parse(r.data)
  },
  create: async (data: ProjectCreate): Promise<Project> => {
    const r = await api.post('/api/projects', data)
    return ProjectSchema.parse(r.data)
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/projects/${id}`)
  },
}

export const metaApi = {
  health: async (): Promise<Health> => {
    const r = await api.get('/health')
    return HealthSchema.parse(r.data)
  },
}
```

- [ ] **Step 2: Create `apps/web/src/lib/query.ts`**

```ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
})
```

- [ ] **Step 3: Compile check**

Run: `cd apps/web && npx tsc --noEmit && cd ../..`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/lib/
git commit -m "feat(phase1): API client (axios + zod runtime types) + TanStack Query client"
```

---

## Task 15: App shell (Sidebar + Topbar + Layout)

**Files:**
- Create: `apps/web/src/components/layout/nav-items.ts`
- Create: `apps/web/src/components/layout/Sidebar.tsx`
- Create: `apps/web/src/components/layout/Topbar.tsx`
- Create: `apps/web/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Create `apps/web/src/components/layout/nav-items.ts`**

```ts
import {
  LayoutDashboard,
  Library,
  FileText,
  Layers,
  PenLine,
  BarChart3,
  Settings as SettingsIcon,
} from 'lucide-react'

export type NavItem = {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

export const navItems: NavItem[] = [
  { to: '/',           label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/library',    label: 'Library',    icon: Library },
  { to: '/reader',     label: 'Reader',     icon: FileText },
  { to: '/compile',    label: 'Compile',    icon: Layers },
  { to: '/manuscript', label: 'Manuscript', icon: PenLine },
  { to: '/statistics', label: 'Statistics', icon: BarChart3 },
  { to: '/settings',   label: 'Settings',   icon: SettingsIcon },
]
```

- [ ] **Step 2: Create `apps/web/src/components/layout/Sidebar.tsx`**

```tsx
import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { sidebarSlide } from '@/lib/motion'
import { navItems } from './nav-items'

export function Sidebar() {
  return (
    <motion.aside
      variants={sidebarSlide}
      initial="initial"
      animate="animate"
      className="hidden md:flex w-[240px] shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-black/20"
    >
      <div className="px-5 py-5 border-b border-white/10">
        <div className="text-[15px] font-semibold tracking-tight">Research Assistant</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-white/50">Manuscripts</div>
      </div>

      <nav className="flex-1 px-2 py-3">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'group relative flex items-center gap-3 h-10 px-3 rounded-md text-[14px] font-medium transition-colors',
                'text-white/70 hover:text-white hover:bg-white/[0.06]',
                isActive && 'text-white bg-white/[0.08]',
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="active-bar"
                    className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-r bg-accent"
                  />
                )}
                <item.icon className="h-[16px] w-[16px] shrink-0" />
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-4 py-3 text-[11px] text-white/40">
        v0.0.1 · local
      </div>
    </motion.aside>
  )
}
```

- [ ] **Step 3: Create `apps/web/src/components/layout/Topbar.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { CircleDot } from 'lucide-react'
import { metaApi } from '@/lib/api'
import { cn } from '@/lib/utils'

export function Topbar() {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: metaApi.health,
    refetchInterval: 30_000,
  })

  const ok = !isError && data?.status === 'ok'
  const degraded = !isError && data?.status === 'degraded'

  return (
    <header className="h-14 shrink-0 border-b border-border bg-white flex items-center justify-between px-5">
      <div className="text-[13px] text-muted-foreground">Local · ./data</div>
      <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
        <CircleDot
          className={cn(
            'h-3 w-3',
            ok && 'text-emerald-500',
            degraded && 'text-amber-500',
            !ok && !degraded && 'text-rose-500',
          )}
        />
        <span>
          {ok && 'API ready'}
          {degraded && 'API degraded'}
          {!ok && !degraded && 'API offline'}
        </span>
      </div>
    </header>
  )
}
```

- [ ] **Step 4: Create `apps/web/src/components/layout/AppShell.tsx`**

```tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppShell() {
  return (
    <div className="flex min-h-screen bg-workspace">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Compile check**

Run: `cd apps/web && npx tsc --noEmit && cd ../..`
Expected: no errors (but routes don't exist yet — Topbar's query will fail until backend runs, which is fine for compile).

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/layout/
git commit -m "feat(phase1): app shell — Sidebar with 7 nav routes, Topbar with health dot, AppShell layout"
```

---

## Task 16: Router + stub pages + Dashboard + Settings

**Files:**
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/App.tsx`
- Create: `apps/web/src/routes/DashboardPage.tsx`
- Create: `apps/web/src/routes/LibraryPage.tsx`
- Create: `apps/web/src/routes/ReaderPage.tsx`
- Create: `apps/web/src/routes/CompilePage.tsx`
- Create: `apps/web/src/routes/ManuscriptPage.tsx`
- Create: `apps/web/src/routes/StatisticsPage.tsx`
- Create: `apps/web/src/routes/SettingsPage.tsx`
- Create: `apps/web/src/components/projects/CreateProjectDialog.tsx`
- Create: `apps/web/src/components/projects/ProjectCard.tsx`

- [ ] **Step 1: Stub pages — create one helper for the boilerplate**

Create `apps/web/src/components/layout/PagePlaceholder.tsx`:

```tsx
import { motion } from 'framer-motion'
import { pageEnter } from '@/lib/motion'

export function PagePlaceholder({ title, subtitle, phase }: { title: string; subtitle: string; phase: string }) {
  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-3xl mx-auto px-8 py-10"
    >
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        {phase}
      </div>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-[14px] text-muted-foreground">{subtitle}</p>
      <div className="mt-6 rounded-lg border border-dashed border-border bg-white/40 p-12 text-center text-[13px] text-muted-foreground">
        This module ships in {phase}.
      </div>
    </motion.div>
  )
}
```

- [ ] **Step 2: Create the five stub route files**

`apps/web/src/routes/LibraryPage.tsx`:
```tsx
import { PagePlaceholder } from '@/components/layout/PagePlaceholder'
export default function LibraryPage() {
  return <PagePlaceholder title="Library" subtitle="Upload PDFs and Word docs. AI extracts citations on upload." phase="Phase 2" />
}
```

`apps/web/src/routes/ReaderPage.tsx`:
```tsx
import { PagePlaceholder } from '@/components/layout/PagePlaceholder'
export default function ReaderPage() {
  return <PagePlaceholder title="Reader" subtitle="Annotate PDFs with the four-colour highlight system." phase="Phase 3" />
}
```

`apps/web/src/routes/CompilePage.tsx`:
```tsx
import { PagePlaceholder } from '@/components/layout/PagePlaceholder'
export default function CompilePage() {
  return <PagePlaceholder title="Compile" subtitle="Aggregate highlights by section. Generate AI drafts." phase="Phase 4" />
}
```

`apps/web/src/routes/ManuscriptPage.tsx`:
```tsx
import { PagePlaceholder } from '@/components/layout/PagePlaceholder'
export default function ManuscriptPage() {
  return <PagePlaceholder title="Manuscript" subtitle="TipTap editor with floating AI toolbar and citation engine." phase="Phase 5" />
}
```

`apps/web/src/routes/StatisticsPage.tsx`:
```tsx
import { PagePlaceholder } from '@/components/layout/PagePlaceholder'
export default function StatisticsPage() {
  return <PagePlaceholder title="Statistics" subtitle="Upload Excel data. Run tests. Plain-English interpretation." phase="Phase 6" />
}
```

- [ ] **Step 3: Create `apps/web/src/components/projects/CreateProjectDialog.tsx`**

```tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { projectsApi, ProjectCreateSchema, type ProjectCreate } from '@/lib/api'
import { studyTypes } from '@/lib/tokens'

export function CreateProjectDialog() {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [studyType, setStudyType] = useState<ProjectCreate['study_type']>('Outcome Study')
  const qc = useQueryClient()

  const { mutate, isPending } = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project created')
      setOpen(false)
      setTitle('')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const parsed = ProjectCreateSchema.safeParse({ title: title.trim(), study_type: studyType })
    if (!parsed.success) {
      toast.error(parsed.error.errors[0]?.message ?? 'Invalid input')
      return
    }
    mutate(parsed.data)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-accent hover:bg-accent-hover text-white">
          <Plus className="h-4 w-4 mr-1.5" />
          New project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[460px]">
        <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>Set a title and study type. You can change these later.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="mt-2 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Anterior approach vs posterior approach in THA"
                autoFocus
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="study-type">Study type</Label>
              <Select value={studyType} onValueChange={v => setStudyType(v as ProjectCreate['study_type'])}>
                <SelectTrigger id="study-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {studyTypes.map(t => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isPending} className="bg-accent hover:bg-accent-hover text-white">
                {isPending ? 'Creating…' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </motion.div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 4: Create `apps/web/src/components/projects/ProjectCard.tsx`**

```tsx
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { cardEnter } from '@/lib/motion'
import { format } from 'date-fns'
import type { Project } from '@/lib/api'

export function ProjectCard({ project, index }: { project: Project; index: number }) {
  return (
    <motion.div
      variants={cardEnter(index)}
      initial="initial"
      animate="animate"
      className="group p-5 rounded-lg border border-border bg-white hover:shadow-sm transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-[15px] font-semibold tracking-tight leading-tight line-clamp-2">
          {project.title}
        </h3>
        <Badge variant="secondary" className="shrink-0 text-[10px] uppercase tracking-wider font-medium">
          {project.study_type}
        </Badge>
      </div>
      <div className="mt-4 flex items-center justify-between text-[12px] text-muted-foreground">
        <span>{project.citation_style.toUpperCase()} · {project.ai_provider}</span>
        <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
      </div>
    </motion.div>
  )
}
```

- [ ] **Step 5: Install `date-fns`**

Run: `cd apps/web && npm install date-fns && cd ../..`

- [ ] **Step 6: Create `apps/web/src/routes/DashboardPage.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FolderOpen } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { CreateProjectDialog } from '@/components/projects/CreateProjectDialog'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { pageEnter } from '@/lib/motion'
import { projectsApi } from '@/lib/api'

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  return (
    <motion.div variants={pageEnter} initial="initial" animate="animate" exit="exit" className="max-w-6xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Dashboard</div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Your projects</h1>
        </div>
        <CreateProjectDialog />
      </div>

      <div className="mt-8">
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[0, 1, 2].map(i => <Skeleton key={i} className="h-[112px] rounded-lg" />)}
          </div>
        )}
        {isError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-[13px] text-destructive">
            Couldn't reach the API. Make sure the backend is running on :8787 (`npm run dev`).
          </div>
        )}
        {data && data.length === 0 && (
          <div className="mt-2 rounded-lg border border-dashed border-border bg-white/40 p-12 text-center">
            <FolderOpen className="h-7 w-7 mx-auto text-muted-foreground" />
            <div className="mt-3 text-[14px] font-medium">No projects yet</div>
            <div className="mt-1 text-[13px] text-muted-foreground">Create one to get started.</div>
          </div>
        )}
        {data && data.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.map((p, i) => <ProjectCard key={p.id} project={p} index={i} />)}
          </div>
        )}
      </div>
    </motion.div>
  )
}
```

- [ ] **Step 7: Create `apps/web/src/routes/SettingsPage.tsx`**

```tsx
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { pageEnter } from '@/lib/motion'
import { metaApi } from '@/lib/api'

export default function SettingsPage() {
  const { data } = useQuery({ queryKey: ['health'], queryFn: metaApi.health })

  return (
    <motion.div variants={pageEnter} initial="initial" animate="animate" exit="exit" className="max-w-3xl mx-auto px-8 py-10 space-y-6">
      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Settings</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Configuration</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          API keys live in <code className="text-[12px] bg-muted px-1 py-0.5 rounded">.env</code> at the project root. Restart the API to apply changes.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-[15px]">AI providers</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data && Object.entries(data.ai_providers).map(([name, status]) => (
            <div key={name} className="flex items-center justify-between border-b last:border-b-0 border-border py-2">
              <div>
                <div className="text-[14px] font-medium capitalize">{name}</div>
                {status.active_model && <div className="text-[12px] text-muted-foreground">Model: {status.active_model}</div>}
                {status.reason && <div className="text-[12px] text-muted-foreground">{status.reason}</div>}
              </div>
              <Badge variant={status.ok ? 'default' : 'secondary'} className={status.ok ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20' : ''}>
                {status.ok ? 'configured' : 'no key'}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-[15px]">Storage</CardTitle></CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          <div>Backend: <span className="font-mono text-foreground">{data?.storage_backend ?? '—'}</span></div>
          <div className="mt-1">DB: <span className="font-mono text-foreground">{data?.db_ok ? 'reachable' : 'unreachable'}</span></div>
          <div className="mt-1">Version: <span className="font-mono text-foreground">{data?.version ?? '—'}</span></div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
```

- [ ] **Step 8: Replace `apps/web/src/App.tsx` with the real router**

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

import { AppShell } from '@/components/layout/AppShell'
import { queryClient } from '@/lib/query'
import DashboardPage from '@/routes/DashboardPage'
import LibraryPage from '@/routes/LibraryPage'
import ReaderPage from '@/routes/ReaderPage'
import CompilePage from '@/routes/CompilePage'
import ManuscriptPage from '@/routes/ManuscriptPage'
import StatisticsPage from '@/routes/StatisticsPage'
import SettingsPage from '@/routes/SettingsPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="reader" element={<ReaderPage />} />
            <Route path="compile" element={<CompilePage />} />
            <Route path="manuscript" element={<ManuscriptPage />} />
            <Route path="statistics" element={<StatisticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}
```

- [ ] **Step 9: Compile check**

Run: `cd apps/web && npx tsc --noEmit && cd ../..`
Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add apps/web/
git commit -m "feat(phase1): router + dashboard + settings + 5 stub pages + create-project dialog"
```

---

## Task 17: End-to-end verification in browser via Chrome DevTools MCP

**Files:** none modified — verification only.

- [ ] **Step 1: Start both servers**

Run from project root:
```bash
npm run dev > /tmp/research-dev.log 2>&1 &
sleep 6
curl -s http://127.0.0.1:8787/health | head -c 300; echo
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173
```
Expected: `/health` returns JSON with `"status":"ok"`; `5173` returns `200`.

- [ ] **Step 2: Drive the browser via chrome-devtools-mcp**

Use `chrome-devtools-mcp` to:
1. `navigate_page` → `http://127.0.0.1:5173`
2. `take_snapshot` → confirm sidebar with all 7 nav items visible
3. `list_console_messages` → confirm no errors
4. Click "New project" → dialog appears
5. Type "Phase 1 smoke test" into title
6. Select "Outcome Study" study type
7. Click "Create"
8. `take_snapshot` → confirm project card appears in list
9. `navigate_page` → `http://127.0.0.1:5173` (reload)
10. `take_snapshot` → confirm card still present
11. Visit `/settings` → confirm Gemini = configured

Capture screenshots at: dashboard empty state, create dialog open, dashboard with project, settings page.

- [ ] **Step 3: Stop servers**

Run: `pkill -f "vite\|uvicorn" || true`

- [ ] **Step 4: Update BUILD_LOG.md and commit**

Append a Phase 1 completion entry to `BUILD_LOG.md` with summary and screenshot references.

```bash
git add BUILD_LOG.md
git commit -m "docs(phase1): build log entry for Phase 1 completion"
git tag -a phase-1 -m "Phase 1 — Foundation & scaffold complete"
```

---

## Acceptance check

Run before declaring Phase 1 complete:

- [ ] `npm run test` (both web placeholder + api tests) → all green
- [ ] `curl http://127.0.0.1:8787/health` → `status: ok`, `db_ok: true`, Gemini ok
- [ ] In browser: create project → reload → project persists
- [ ] No console errors at any of: `/`, `/library`, `/reader`, `/compile`, `/manuscript`, `/statistics`, `/settings`
- [ ] All commits land; `phase-1` tag exists

---

## What this plan deliberately does NOT do

- No upload UI yet (Phase 2)
- No PDF viewer (Phase 3)
- No AI calls anywhere yet — Phase 1 only confirms a key is set
- No Alembic migrations beyond `projects` table (other tables ship with the phase that uses them)
- No tests for frontend components (Phase 8 polish)
- No motion-reduced-motion handling (handled in Phase 8 polish if not by default Framer behaviour)

---

## Self-Review

**Spec coverage:** Phase 1 acceptance bar from spec §7 → covered by Tasks 13 (CRUD persists), 12 (health), 16 (all routes), 17 (browser verify). Adapter layer §4 → repository protocol + DI container present (storage + AI deferred since they aren't called in Phase 1, but Protocols can land in Phase 2 with their first real use to avoid dead code).

**Placeholders:** scanned — none.

**Type consistency:** `ProjectCreate`/`ProjectRead` schemas align between Python (`schemas/project.py`) and TS (`lib/api.ts`). `study_type` enum identical in both. `local_user_id` from settings, `user_id` on every model.

**Self-check ok. Proceeding.**
