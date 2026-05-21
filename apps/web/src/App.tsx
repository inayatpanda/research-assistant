import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import { AppShell } from '@/components/layout/AppShell'
import {
  LegacyRedirect,
  ReaderLegacyForward,
} from '@/components/layout/LegacyRedirect'
import { ProjectLayoutGuard } from '@/components/layout/ProjectLayoutGuard'
import { queryClient } from '@/lib/query'
import ChecklistsPage from '@/routes/ChecklistsPage'
import CompilePage from '@/routes/CompilePage'
import ConsortPage from '@/routes/ConsortPage'
import DashboardPage from '@/routes/DashboardPage'
import EconomicsPage from '@/routes/EconomicsPage'
import HealthPage from '@/routes/HealthPage'
import LearnPage from '@/routes/LearnPage'
import LibraryPage from '@/routes/LibraryPage'
import ManuscriptPage from '@/routes/ManuscriptPage'
import PeerReviewPage from '@/routes/PeerReviewPage'
import ProjectHomePage from '@/routes/ProjectHomePage'
import ReaderPage from '@/routes/ReaderPage'
import SettingsPage from '@/routes/SettingsPage'
import StatisticsPage from '@/routes/StatisticsPage'
import SubmissionPage from '@/routes/SubmissionPage'
import SystematicReviewPage from '@/routes/SystematicReviewPage'
import { Navigate, useParams } from 'react-router-dom'

/**
 * MP12.5 — URL-scoped project routing.
 *
 * Routes are now organised as:
 *   `/`                 → Dashboard (project picker)
 *   `/settings`         → SettingsPage (global)
 *   `/health`           → HealthPage   (global)
 *   `/projects/:id`     → ProjectHomePage
 *   `/projects/:id/<m>` → per-module pages, guarded by <ProjectLayoutGuard>
 *
 * Pre-MP12.5 module paths (`/library`, `/manuscript`, etc.) still resolve
 * via <LegacyRedirect>, which forwards to the last-viewed project. These
 * legacy redirects will be removed in MP14.
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="health" element={<HealthPage />} />

            {/* Project-scoped routes — every page below sees a real
                projectId via the <ProjectLayoutGuard> context. */}
            <Route path="projects/:projectId" element={<ProjectLayoutGuard />}>
              <Route index element={<ProjectHomePage />} />
              <Route path="library" element={<LibraryPage />} />
              <Route path="reader" element={<ReaderPage />} />
              <Route path="reader/:articleId" element={<ReaderPage />} />
              <Route path="compile" element={<CompilePage />} />
              <Route path="manuscript" element={<ManuscriptPage />} />
              <Route path="peer-review" element={<PeerReviewPage />} />
              <Route path="systematic-review" element={<SystematicReviewPage />} />
              {/* Phase 4.6 — legacy `/review` path now redirects to
                  systematic-review so existing deep links keep working. */}
              <Route path="review" element={<ScopedReviewRedirect />} />
              <Route path="consort" element={<ConsortPage />} />
              <Route path="statistics" element={<StatisticsPage />} />
              <Route path="economics" element={<EconomicsPage />} />
              <Route path="checklists" element={<ChecklistsPage />} />
              <Route path="submission" element={<SubmissionPage />} />
              {/* Phase 5a — Learn hub (reference content, mounted under
                  Settings as a "Reference & how-to" entry point). */}
              <Route path="learn" element={<LearnPage />} />
            </Route>

            {/* Legacy redirects — will be removed in MP14. */}
            <Route path="library" element={<LegacyRedirect to="/library" />} />
            <Route path="reader" element={<LegacyRedirect to="/reader" />} />
            <Route path="reader/:articleId" element={<ReaderLegacyForward />} />
            <Route path="compile" element={<LegacyRedirect to="/compile" />} />
            <Route
              path="manuscript"
              element={<LegacyRedirect to="/manuscript" />}
            />
            <Route
              path="review"
              element={<LegacyRedirect to="/systematic-review" />}
            />
            <Route
              path="systematic-review"
              element={<LegacyRedirect to="/systematic-review" />}
            />
            <Route
              path="peer-review"
              element={<LegacyRedirect to="/peer-review" />}
            />
            <Route path="consort" element={<LegacyRedirect to="/consort" />} />
            <Route
              path="statistics"
              element={<LegacyRedirect to="/statistics" />}
            />
            <Route
              path="submission"
              element={<LegacyRedirect to="/submission" />}
            />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}


/**
 * Phase 4.6 — Redirects ``/projects/:projectId/review`` →
 * ``/projects/:projectId/systematic-review`` so legacy deep links still
 * resolve after the rename.
 */
function ScopedReviewRedirect() {
  const { projectId } = useParams<{ projectId: string }>()
  return <Navigate to={`/projects/${projectId}/systematic-review`} replace />
}
