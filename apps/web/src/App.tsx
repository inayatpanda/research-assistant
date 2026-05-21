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
import WelcomePage from '@/routes/WelcomePage'
import AccountPage from '@/routes/AccountPage'
import InvitePage from '@/routes/InvitePage'
import LoginPage from '@/routes/LoginPage'
import SignupPage from '@/routes/SignupPage'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { Navigate, Outlet, useParams } from 'react-router-dom'

// Phase M0 — mobile shell + DeviceRouter.
import { DeviceRouter } from '@/mobile/DeviceRouter'
import { MobileShell } from '@/mobile/MobileShell'
import MobileAccount from '@/mobile/pages/MobileAccount'
import MobileLearn from '@/mobile/pages/MobileLearn'
import MobileLearnEntryPage from '@/mobile/pages/MobileLearnEntryPage'
import MobileLibrary from '@/mobile/pages/MobileLibrary'
import MobileReader from '@/mobile/pages/MobileReader'
import MobileManuscripts from '@/mobile/pages/MobileManuscripts'
import MobileManuscriptReader from '@/mobile/pages/MobileManuscriptReader'
import MobileMore from '@/mobile/pages/MobileMore'
import MobilePeerReview from '@/mobile/pages/MobilePeerReview'
import MobilePeerReviewDetail from '@/mobile/pages/MobilePeerReviewDetail'
import MobileSettings from '@/mobile/pages/MobileSettings'
import MobileSetupHelp from '@/mobile/pages/MobileSetupHelp'
import MobileSetupPage from '@/mobile/pages/MobileSetupPage'
import MobileStatsPlaceholder from '@/mobile/pages/MobileStatsPlaceholder'
import { useResolvedBackendUrl } from '@/mobile/lib/backendUrl'

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
 *
 * Phase M0 — the whole tree is wrapped in <DeviceRouter>, which renders
 * the existing desktop shell on wide viewports and a sibling mobile
 * shell (`/m/*`) on narrow ones. Desktop behaviour is unchanged.
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <DeviceRouter desktop={<DesktopRoutes />} mobile={<MobileRoutes />} />
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}

function DesktopRoutes() {
  return (
    <Routes>
      {/* Phase S1 — public auth pages (no AppShell, no RequireAuth). */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/invite/:token" element={<InvitePage />} />
      <Route path="/welcome" element={<WelcomePage />} />

      <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="health" element={<HealthPage />} />
        {/* Phase S1 — manage account, sessions, change password. */}
        <Route path="account" element={<AccountPage />} />

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
  )
}

/**
 * Phase M0 — mobile route tree mounted under `/m/*`.
 *
 * Public sub-routes (the setup screen + auth flow) live outside the
 * <MobileShell> so a user with no backend URL configured can still
 * reach `/m/setup`. Everything else is wrapped in the shell, which
 * itself gates on auth via <RequireAuth>.
 */
function MobileRoutes() {
  return (
    <Routes>
      {/* Auth pages — same components as desktop, viewport handles itself. */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/invite/:token" element={<InvitePage />} />
      <Route path="/welcome" element={<WelcomePage />} />

      {/* Public mobile route — no shell, no auth gate. */}
      <Route path="/m/setup" element={<MobileSetupPage />} />

      {/* Auth-gated mobile shell. */}
      <Route path="/m" element={<MobileRequireBackend />}>
        <Route index element={<Navigate to="/m/library" replace />} />
        <Route element={<MobileShell />}>
          <Route path="library" element={<MobileLibrary />} />
          <Route path="reader/:articleId" element={<MobileReader />} />
          <Route path="manuscripts" element={<MobileManuscripts />} />
          <Route
            path="manuscripts/:projectId"
            element={<MobileManuscriptReader />}
          />
          <Route path="stats" element={<MobileStatsPlaceholder />} />
          <Route path="learn" element={<MobileLearn />} />
          <Route path="learn/:category/:slug" element={<MobileLearnEntryPage />} />
          <Route path="more" element={<MobileMore />} />
          {/* Phase M1.3 — peer review entry + detail. */}
          <Route path="peer-review" element={<MobilePeerReview />} />
          <Route
            path="peer-review/:projectId/:id"
            element={<MobilePeerReviewDetail />}
          />
          {/* Phase M1.4 — account / settings / tailscale help. */}
          <Route path="account" element={<MobileAccount />} />
          <Route path="settings" element={<MobileSettings />} />
          <Route path="setup-help" element={<MobileSetupHelp />} />
          {/* Catch-all under /m/* → bounce to library. */}
          <Route path="*" element={<Navigate to="/m/library" replace />} />
        </Route>
      </Route>

      {/* Any other path on a small viewport falls through to library. */}
      <Route path="*" element={<Navigate to="/m/library" replace />} />
    </Routes>
  )
}

/**
 * Guard: if the PWA has no backend URL configured (no store value, no
 * Electron bridge, no VITE_API_URL), bounce to `/m/setup` first. The
 * setup screen is the only mobile route that always renders without
 * needing a backend.
 */
function MobileRequireBackend() {
  const backendUrl = useResolvedBackendUrl()
  if (!backendUrl) {
    return <Navigate to="/m/setup" replace />
  }
  return <Outlet />
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
