/**
 * apps/site/scripts/capture_screenshots.ts
 *
 * Drives the real apps/web React app via Playwright Chromium and saves
 * 12 PNG screenshots into apps/site/public/screenshots/ that the new
 * landing page embeds.
 *
 * Prereqs (see redesign plan):
 *   - apps/api running with `RMA_DISABLE_AUTH=1` at 127.0.0.1:8787
 *   - apps/web dev server running with `VITE_LICENSE_BYPASS=1`
 *   - scripts/seed_demo.py has been run so demo projects exist
 *
 * Usage:  cd apps/site && npx tsx scripts/capture_screenshots.ts
 *
 * NOTE: This file is dev-only. It is not imported by the site bundle
 * and is excluded from production builds (Vite ignores anything outside
 * src/). Do not import it from app code.
 */
import { chromium, type Page } from '@playwright/test'
import * as path from 'node:path'
import * as fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const WEB_BASE = process.env.WEB_BASE_URL ?? 'http://127.0.0.1:5173'
const API_BASE = process.env.API_BASE_URL ?? 'http://127.0.0.1:8787'
const OUT_DIR = path.resolve(__dirname, '..', 'public', 'screenshots')

const DESKTOP = { width: 1440, height: 900 }
const DESKTOP_2X = { width: 1440, height: 900, deviceScaleFactor: 2 }
const MOBILE = { width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true }

interface DemoProject {
  id: string
  title: string
  study_type: string
}

async function pickProjects(): Promise<{ sr: DemoProject; rct: DemoProject; cohort: DemoProject }> {
  const res = await fetch(`${API_BASE}/api/projects`)
  if (!res.ok) throw new Error(`API not reachable at ${API_BASE}: ${res.status}`)
  const all = (await res.json()) as DemoProject[]
  const sr = all.find((p) => p.title.toLowerCase().includes('cruciate'))
    ?? all.find((p) => p.study_type === 'Systematic Review')
  const rct = all.find((p) => p.title.toLowerCase().includes('lisinopril'))
    ?? all.find((p) => p.study_type === 'Randomised Controlled Trial')
  const cohort = all.find((p) => p.title.toLowerCase().includes('laparoscopic'))
    ?? all.find((p) => p.study_type === 'Retrospective Case Series')
    ?? rct
  if (!sr || !rct || !cohort) {
    throw new Error('Demo projects missing — run scripts/seed_demo.py first')
  }
  return { sr, rct, cohort }
}

async function settle(page: Page, ms = 900) {
  await page.waitForLoadState('networkidle').catch(() => undefined)
  await page.waitForTimeout(ms)
}

async function capture(page: Page, slug: string) {
  const file = path.join(OUT_DIR, `${slug}.png`)
  await page.screenshot({ path: file, fullPage: false })
  console.log(`  -> ${slug}.png`)
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true })
  const projects = await pickProjects()
  console.log('Demo projects:')
  console.log('  SR    :', projects.sr.id, projects.sr.title)
  console.log('  RCT   :', projects.rct.id, projects.rct.title)
  console.log('  cohort:', projects.cohort.id, projects.cohort.title)

  const browser = await chromium.launch({ headless: true })

  // --- Desktop captures ----------------------------------------------------
  const ctx = await browser.newContext({ viewport: DESKTOP, deviceScaleFactor: 1 })
  const page = await ctx.newPage()

  console.log('\n[desktop] dashboard')
  await page.goto(`${WEB_BASE}/`)
  await settle(page, 1200)
  await capture(page, 'dashboard')

  console.log('[desktop] library')
  await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/library`)
  await settle(page, 1200)
  await capture(page, 'library')

  // Pick first article for reader
  console.log('[desktop] reader')
  try {
    const arts = await (await fetch(`${API_BASE}/api/projects/${projects.sr.id}/articles`)).json()
    const articleId = arts[0]?.id
    if (articleId) {
      await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/reader/${articleId}`)
      await settle(page, 1500)
    } else {
      await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/reader`)
      await settle(page, 1200)
    }
  } catch {
    await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/reader`)
    await settle(page, 1200)
  }
  await capture(page, 'reader')

  console.log('[desktop] manuscript')
  await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/manuscript`)
  await settle(page, 1500)
  await capture(page, 'manuscript')

  console.log('[desktop] statistics')
  await page.goto(`${WEB_BASE}/projects/${projects.rct.id}/statistics`)
  await settle(page, 1500)
  await capture(page, 'statistics')

  console.log('[desktop] meta-analysis')
  // Resolve the first meta-analysis id directly via API so we can navigate
  // to `?tab=meta&meta=<id>` and skip click-driven selection entirely.
  try {
    const metas = (await (await fetch(
      `${API_BASE}/api/projects/${projects.sr.id}/reviews/meta`,
    )).json()) as Array<{ id: string }>
    const metaId = metas[0]?.id
    if (metaId) {
      // Make sure the meta-analysis has been computed so the forest plot
      // panel renders (the seed leaves it as 'draft' by default).
      await fetch(
        `${API_BASE}/api/projects/${projects.sr.id}/reviews/meta/${metaId}/run`,
        { method: 'POST' },
      ).catch(() => undefined)
      await page.goto(
        `${WEB_BASE}/projects/${projects.sr.id}/systematic-review?tab=meta&meta=${metaId}`,
      )
    } else {
      await page.goto(
        `${WEB_BASE}/projects/${projects.sr.id}/systematic-review?tab=meta`,
      )
    }
  } catch {
    await page.goto(
      `${WEB_BASE}/projects/${projects.sr.id}/systematic-review?tab=meta`,
    )
  }
  await settle(page, 2400)
  // Scroll down so the forest+funnel plots are visible in the viewport.
  await page.evaluate(() => window.scrollTo({ top: 700, behavior: 'instant' as ScrollBehavior }))
  await page.waitForTimeout(800)
  await capture(page, 'meta-analysis')

  console.log('[desktop] peer-review')
  // Resolve a completed peer review id and deep-link to it.
  try {
    const reviews = (await (await fetch(
      `${API_BASE}/api/projects/${projects.sr.id}/peer-reviews`,
    )).json()) as Array<{ id: string }>
    const prId = reviews[0]?.id
    if (prId) {
      await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/peer-review?review=${prId}`)
    } else {
      await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/peer-review`)
    }
  } catch {
    await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/peer-review`)
  }
  await settle(page, 1800)
  // If still on history, try clicking the first history card.
  try {
    const card = page.locator('text=/Major Revision|Minor Revision|Accept|Reject/i').first()
    if ((await card.count()) > 0) {
      await card.click({ timeout: 1500, force: true }).catch(() => undefined)
      await settle(page, 1500)
    }
  } catch {
    /* ignore */
  }
  await capture(page, 'peer-review')

  console.log('[desktop] learn')
  await page.goto(`${WEB_BASE}/projects/${projects.sr.id}/learn`)
  await settle(page, 1200)
  await capture(page, 'learn')

  console.log('[desktop] submission')
  // RCT project has the cover letter populated by the seed.
  await page.goto(`${WEB_BASE}/projects/${projects.rct.id}/submission`)
  await settle(page, 1500)
  await capture(page, 'submission')

  // Retina hero capture (2x) of manuscript for the hero embed
  console.log('[desktop@2x] manuscript-hero')
  const ctx2x = await browser.newContext({ viewport: DESKTOP_2X, deviceScaleFactor: 2 })
  const page2x = await ctx2x.newPage()
  await page2x.goto(`${WEB_BASE}/projects/${projects.sr.id}/manuscript`)
  await settle(page2x, 1800)
  await page2x.screenshot({
    path: path.join(OUT_DIR, 'manuscript@2x.png'),
    fullPage: false,
  })
  await ctx2x.close()

  await ctx.close()

  // --- Mobile captures -----------------------------------------------------
  const mobileCtx = await browser.newContext({
    viewport: { width: MOBILE.width, height: MOBILE.height },
    deviceScaleFactor: MOBILE.deviceScaleFactor,
    isMobile: MOBILE.isMobile,
    hasTouch: MOBILE.hasTouch,
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  })
  // Pre-seed the mobile backend URL in localStorage so the mobile shell
  // skips its first-run setup screen. Persist also expects the same
  // shape that zustand/persist writes. We also pin the RCT project as
  // the last-viewed one because its dataset/analysis ids are the ones
  // we deep-link to in the stats screenshot.
  await mobileCtx.addInitScript(`
    (() => {
      try {
        window.localStorage.setItem(
          'rma.backendUrl',
          JSON.stringify({ state: { url: '${API_BASE}' }, version: 0 }),
        );
        window.localStorage.setItem(
          'research-last-viewed-project',
          JSON.stringify({ state: { projectId: '${projects.sr.id}' }, version: 0 }),
        );
      } catch {}
    })();
  `)
  const mPage = await mobileCtx.newPage()

  console.log('\n[mobile] library')
  await mPage.goto(`${WEB_BASE}/m/library`)
  await settle(mPage, 1500)
  await capture(mPage, 'mobile-library')

  console.log('[mobile] reader')
  try {
    const arts = await (await fetch(`${API_BASE}/api/projects/${projects.sr.id}/articles`)).json()
    const articleId = arts[0]?.id
    if (articleId) {
      await mPage.goto(`${WEB_BASE}/m/reader/${articleId}`)
      await settle(mPage, 1500)
    } else {
      await mPage.goto(`${WEB_BASE}/m/library`)
      await settle(mPage, 1500)
    }
  } catch {
    await mPage.goto(`${WEB_BASE}/m/library`)
    await settle(mPage, 1500)
  }
  await capture(mPage, 'mobile-reader')

  console.log('[mobile] stats')
  // Need a fresh context for the stats screen so the RCT project becomes
  // the persisted "last viewed" project before the React tree hydrates.
  await mobileCtx.close()
  const statsCtx = await browser.newContext({
    viewport: { width: MOBILE.width, height: MOBILE.height },
    deviceScaleFactor: MOBILE.deviceScaleFactor,
    isMobile: MOBILE.isMobile,
    hasTouch: MOBILE.hasTouch,
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  })
  await statsCtx.addInitScript(`
    (() => {
      try {
        window.localStorage.setItem(
          'rma.backendUrl',
          JSON.stringify({ state: { url: '${API_BASE}' }, version: 0 }),
        );
        window.localStorage.setItem(
          'research-last-viewed-project',
          JSON.stringify({ state: { projectId: '${projects.rct.id}' }, version: 0 }),
        );
      } catch {}
    })();
  `)
  const sPage = await statsCtx.newPage()
  try {
    const ds = await (await fetch(`${API_BASE}/api/projects/${projects.rct.id}/datasets`)).json()
    const datasetId = ds[0]?.id
    if (datasetId) {
      const analyses = await (await fetch(
        `${API_BASE}/api/projects/${projects.rct.id}/datasets/${datasetId}/analyses`,
      )).json()
      const analysisId = analyses[0]?.id
      if (analysisId) {
        await sPage.goto(`${WEB_BASE}/m/stats/${datasetId}/results/${analysisId}`)
      } else {
        await sPage.goto(`${WEB_BASE}/m/stats/${datasetId}/preview`)
      }
    } else {
      await sPage.goto(`${WEB_BASE}/m/library`)
    }
  } catch {
    await sPage.goto(`${WEB_BASE}/m/library`)
  }
  await settle(sPage, 2500)
  try {
    await sPage.waitForSelector('[data-testid="mstats-results-body"]', { timeout: 5000 })
  } catch {
    /* the page may have fallen back to an empty state — capture anyway */
  }
  await sPage.waitForTimeout(800)
  await capture(sPage, 'mobile-stats')

  await statsCtx.close()
  await browser.close()
  console.log('\nDone. PNGs written to', OUT_DIR)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
