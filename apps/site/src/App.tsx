import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom'
import type { ReactNode } from 'react'

import { Layout } from '@/components/Layout'
import HomePage from '@/pages/HomePage'
import InstallPage from '@/pages/InstallPage'
import SyncPage from '@/pages/SyncPage'
import DocsPage from '@/pages/DocsPage'
import ChangelogPage from '@/pages/ChangelogPage'
import PricingPage from '@/pages/PricingPage'
import SignupPage from '@/pages/SignupPage'
import LoginPage from '@/pages/LoginPage'
import AccountPage from '@/pages/AccountPage'
import ForgotPasswordPage from '@/pages/ForgotPasswordPage'
import ResetPasswordPage from '@/pages/ResetPasswordPage'

/**
 * Phase D2 — Top-level router for the landing site.
 *
 * `routerOverride` is used by tests to swap the BrowserRouter for a
 * MemoryRouter with a known initial path. Production callers don't pass
 * anything; the default ships a normal BrowserRouter so a deploy to
 * Cloudflare Pages serves clean URLs.
 *
 * Phase L1c — added the commerce routes (/pricing, /signup, /login,
 * /account, /forgot-password, /reset-password/:token).
 */
interface AppProps {
  routerOverride?: 'memory'
  initialEntries?: string[]
}

function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/install" element={<InstallPage />} />
        <Route path="/sync" element={<SyncPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/changelog" element={<ChangelogPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        {/* 404 fallback — Cloudflare Pages serves _redirects, but a soft
            client-side fallback keeps deep links working in dev. */}
        <Route path="*" element={<HomePage />} />
      </Routes>
    </Layout>
  )
}

export default function App({ routerOverride, initialEntries }: AppProps = {}): ReactNode {
  if (routerOverride === 'memory') {
    return (
      <MemoryRouter initialEntries={initialEntries ?? ['/']}>
        <AppRoutes />
      </MemoryRouter>
    )
  }
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
