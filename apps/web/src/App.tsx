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
import CompilePage from '@/routes/CompilePage'
import ConsortPage from '@/routes/ConsortPage'
import DashboardPage from '@/routes/DashboardPage'
import EconomicsPage from '@/routes/EconomicsPage'
import HealthPage from '@/routes/HealthPage'
import LibraryPage from '@/routes/LibraryPage'
import ManuscriptPage from '@/routes/ManuscriptPage'
import ProjectHomePage from '@/routes/ProjectHomePage'
import ReaderPage from '@/routes/ReaderPage'
import SettingsPage from '@/routes/SettingsPage'
import StatisticsPage from '@/routes/StatisticsPage'
import SubmissionPage from '@/routes/SubmissionPage'
import SystematicReviewPage from '@/routes/SystematicReviewPage'

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
              <Route path="review" element={<SystematicReviewPage />} />
              <Route path="consort" element={<ConsortPage />} />
              <Route path="statistics" element={<StatisticsPage />} />
              <Route path="economics" element={<EconomicsPage />} />
              <Route path="submission" element={<SubmissionPage />} />
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
            <Route path="review" element={<LegacyRedirect to="/review" />} />
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
