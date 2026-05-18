/**
 * MP12.5 — guard & legacy redirect tests.
 *
 * Mounts the full route tree under MemoryRouter so we can exercise:
 *  - Successful project resolution → child renders + projectId is
 *    available via useProjectId().
 *  - 404 (or any fetch error) → user is redirected to "/".
 *  - LegacyRedirect with a populated lastViewedProjectId in the
 *    Zustand store forwards to the URL-scoped route.
 *  - LegacyRedirect with no lastViewedProjectId falls back to "/".
 *  - The Zustand store records the routed projectId as "last viewed"
 *    once the guard mounts.
 *
 * jsdom 29 doesn't expose `window.localStorage` so we exercise the
 * Zustand store API directly rather than reaching into localStorage.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock the projects API so we never make real HTTP calls.
const getMock = vi.fn()
vi.mock('@/lib/api', () => ({
  projectsApi: {
    get: (id: string) => getMock(id),
  },
}))

// Silence sonner toasts during tests (still call them to verify error path).
const toastErrorMock = vi.fn()
vi.mock('sonner', () => ({
  toast: { error: (...args: unknown[]) => toastErrorMock(...args) },
}))

import { LegacyRedirect } from '../LegacyRedirect'
import { ProjectLayoutGuard } from '../ProjectLayoutGuard'
import { useLastViewedProject, useProjectId } from '@/lib/projectContext'

function ProjectIdProbe() {
  const id = useProjectId()
  return <div data-testid="project-id">{id}</div>
}

function renderWithRouter(initialEntry: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/" element={<div data-testid="dashboard">Dashboard</div>} />
          <Route path="/projects/:projectId" element={<ProjectLayoutGuard />}>
            <Route index element={<ProjectIdProbe />} />
            <Route path="library" element={<ProjectIdProbe />} />
          </Route>
          <Route path="/library" element={<LegacyRedirect to="/library" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProjectLayoutGuard', () => {
  beforeEach(() => {
    getMock.mockReset()
    toastErrorMock.mockReset()
    useLastViewedProject.getState().clear()
  })
  afterEach(() => cleanup())

  it('renders the child route when the project resolves', async () => {
    getMock.mockResolvedValue({
      id: 'p-1',
      title: 'My project',
      study_type: 'Outcome Study',
      citation_style: 'vancouver',
      ai_provider: 'claude',
    })

    const { findByTestId } = renderWithRouter('/projects/p-1')
    const probe = await findByTestId('project-id')
    expect(probe.textContent).toBe('p-1')
  })

  it('redirects to / and shows a toast when the project 404s', async () => {
    getMock.mockRejectedValue(new Error('Project not found'))

    const { findByTestId } = renderWithRouter('/projects/does-not-exist')
    const dash = await findByTestId('dashboard')
    expect(dash).toBeTruthy()
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled())
  })

  it('records the projectId as last-viewed once the route is mounted', async () => {
    getMock.mockResolvedValue({
      id: 'p-2',
      title: 'X',
      study_type: 'Outcome Study',
      citation_style: 'vancouver',
      ai_provider: 'claude',
    })
    renderWithRouter('/projects/p-2')
    await waitFor(() =>
      expect(useLastViewedProject.getState().projectId).toBe('p-2'),
    )
  })
})

describe('LegacyRedirect', () => {
  beforeEach(() => {
    getMock.mockReset()
    toastErrorMock.mockReset()
    useLastViewedProject.getState().clear()
  })
  afterEach(() => cleanup())

  it('forwards /library to /projects/<id>/library when last-viewed is set', async () => {
    useLastViewedProject.getState().set('p-9')
    getMock.mockResolvedValue({
      id: 'p-9',
      title: 'Y',
      study_type: 'Outcome Study',
      citation_style: 'vancouver',
      ai_provider: 'claude',
    })

    const { findByTestId } = renderWithRouter('/library')
    // After redirect, the guard mounts and the probe renders.
    const probe = await findByTestId('project-id')
    expect(probe.textContent).toBe('p-9')
  })

  it('redirects /library to / when no last-viewed project is stored', async () => {
    useLastViewedProject.getState().clear()
    const { findByTestId } = renderWithRouter('/library')
    const dash = await findByTestId('dashboard')
    expect(dash).toBeTruthy()
  })
})

describe('useProjectId()', () => {
  afterEach(() => cleanup())

  it('throws a helpful error when called outside a project route', () => {
    function Naked() {
      useProjectId()
      return null
    }
    // Suppress React's error logging for this expected throw.
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    expect(() =>
      render(
        <MemoryRouter>
          <Naked />
        </MemoryRouter>,
      ),
    ).toThrow(/useProjectId\(\) must be called inside/)
    consoleError.mockRestore()
  })
})
