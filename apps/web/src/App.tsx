import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import { AppShell } from '@/components/layout/AppShell'
import { queryClient } from '@/lib/query'
import CompilePage from '@/routes/CompilePage'
import DashboardPage from '@/routes/DashboardPage'
import HealthPage from '@/routes/HealthPage'
import LibraryPage from '@/routes/LibraryPage'
import ManuscriptPage from '@/routes/ManuscriptPage'
import ReaderPage from '@/routes/ReaderPage'
import SettingsPage from '@/routes/SettingsPage'
import StatisticsPage from '@/routes/StatisticsPage'
import SystematicReviewPage from '@/routes/SystematicReviewPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="reader" element={<ReaderPage />} />
            <Route path="reader/:articleId" element={<ReaderPage />} />
            <Route path="compile" element={<CompilePage />} />
            <Route path="manuscript" element={<ManuscriptPage />} />
            <Route path="review" element={<SystematicReviewPage />} />
            <Route path="statistics" element={<StatisticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="health" element={<HealthPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}
