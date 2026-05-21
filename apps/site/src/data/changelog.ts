/**
 * Phase D2 — Hand-authored changelog.
 *
 * Sourced from the repo's phase-tag history. Entries are listed in
 * reverse-chronological order (newest first) and rendered as-is by
 * ChangelogPage. Once the GitHub repo is live, a future iteration will
 * generate this from the Releases API — flagged with a footnote at the
 * bottom of the page.
 */
export interface ChangelogEntry {
  version: string
  date: string // ISO yyyy-mm-dd
  headline: string
  bullets: string[]
}

export const CHANGELOG: ChangelogEntry[] = [
  {
    version: 'v1.0.0-d2',
    date: '2026-05-21',
    headline: 'Landing site live',
    bullets: [
      'Public marketing site at apps/site shipping with Hero, Install, Sync, Docs and Changelog pages.',
      'OS auto-detection on the hero CTA and Install page highlights the visitor’s platform.',
      'Tailscale onboarding guide with troubleshooting accordion.',
    ],
  },
  {
    version: 'v1.0.0-d1',
    date: '2026-05-19',
    headline: 'Distribution polish',
    bullets: [
      'Linux AppImage target added alongside macOS .dmg and Windows .exe.',
      'Highlight-colour PATCH endpoint, electron-updater wiring and GitHub Actions release workflow.',
      'HTTPS-over-tailnet docs for trusted certs from `tailscale cert`.',
    ],
  },
  {
    version: 'v0.9.0-s1',
    date: '2026-05-15',
    headline: 'Multi-user auth + project sharing',
    bullets: [
      'JWT-based auth, sign-up / sign-in / password reset flows.',
      'Project-level role-based access (Owner / Editor / Commenter / Viewer).',
      'Invitation flow with one-time accept links and legacy single-user data claim.',
    ],
  },
  {
    version: 'v0.8.0-e1',
    date: '2026-05-10',
    headline: 'Desktop packaging',
    bullets: [
      'Electron bundle ships the React frontend and FastAPI backend as one app.',
      'macOS .dmg and Windows .exe artefacts built by GitHub Actions.',
      'App auto-updates from GitHub Releases on launch.',
    ],
  },
  {
    version: 'v0.7.0-m5',
    date: '2026-05-04',
    headline: 'Mobile mini-apps',
    bullets: [
      'Mobile Economics, Checklists and Submission screens wired into MobileMore.',
      'Touch-optimised drawer sheets for editing checklist items on iPad.',
    ],
  },
  {
    version: 'v0.6.0-m4',
    date: '2026-04-29',
    headline: 'Mobile statistics wizard',
    bullets: [
      'Five-page linear stats wizard for iPad: pick dataset → variables → test → run → interpret.',
      'Push results to the manuscript directly from the wizard.',
    ],
  },
  {
    version: 'v0.5.0-m3',
    date: '2026-04-24',
    headline: 'Mobile manuscript reader',
    bullets: [
      'Read the manuscript on iPad with per-paragraph edit sheets.',
      'Bubble-AI paraphrase and rewrite on selection.',
    ],
  },
  {
    version: 'v0.4.0-m2',
    date: '2026-04-19',
    headline: 'Mobile Library + Reader',
    bullets: [
      'Library upload from the iPad share sheet (PDF, RIS, BibTeX).',
      'Touch highlights with the same Intro / Method / Results / Discussion palette.',
    ],
  },
  {
    version: 'v0.3.0-m1',
    date: '2026-04-14',
    headline: 'Mobile read-only mode',
    bullets: ['Mobile Settings, Learn, Peer Review and More pages with the laptop-only modules clearly flagged.'],
  },
  {
    version: 'v0.2.0-m0',
    date: '2026-04-09',
    headline: 'PWA foundations',
    bullets: [
      'Service worker, manifest, and mobile shell scaffolding.',
      'DeviceRouter that picks the right shell for desktop and touch devices.',
    ],
  },
  {
    version: 'v0.1.0-e1-preview',
    date: '2026-04-01',
    headline: 'First public preview',
    bullets: [
      'Library, Reader, Manuscript editor, Statistics, Meta-analysis and Peer Review in one workspace.',
      'Backend pytest suite ≥2200 tests, frontend vitest ≥400 tests.',
    ],
  },
]
