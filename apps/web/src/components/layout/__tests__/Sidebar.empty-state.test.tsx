/**
 * Fix-E2E/6 — Sidebar empty-state regression.
 *
 * When the user has not selected a project (no `:projectId` in the route
 * AND no last-viewed projectId persisted in localStorage), the project-
 * scoped nav items must render as disabled placeholders instead of links
 * that silently collapse back to the Dashboard.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// jsdom 29 ships without a real localStorage. In-memory shim so the
// `useLastViewedProject` zustand store doesn't crash.
function installLocalStorageShim() {
  const store = new Map<string, string>()
  const shim: Storage = {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (k: string) => {
      store.delete(k)
    },
    setItem: (k: string, v: string) => {
      store.set(k, String(v))
    },
  }
  Object.defineProperty(window, 'localStorage', {
    value: shim,
    configurable: true,
    writable: true,
  })
  Object.defineProperty(globalThis, 'localStorage', {
    value: shim,
    configurable: true,
    writable: true,
  })
}
installLocalStorageShim()

// Stub the projects list so we don't hit the network. Empty list is fine —
// the cleanup effect won't fire because storedLastViewedProjectId is null.
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    projectsApi: {
      ...actual.projectsApi,
      list: vi.fn(async () => []),
    },
  }
})

import { Sidebar } from '../Sidebar'

function wrap(opts: { route?: string } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[opts.route ?? '/']}>
        <Routes>
          {/* Mount the sidebar inside both the bare and project-scoped
              routes so useParams() resolves `:projectId` like it does in
              production. */}
          <Route path="/" element={<Sidebar />} />
          <Route path="/projects/:projectId/*" element={<Sidebar />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})
afterEach(cleanup)

describe('Sidebar empty-state (Fix-E2E/6)', () => {
  it('renders the "pick a project" hint when no project is selected', () => {
    const { getByTestId } = wrap({ route: '/' })
    const hint = getByTestId('sidebar-empty-hint')
    expect(hint.textContent ?? '').toMatch(/Pick a project/i)
  })

  it('renders project-scoped nav items as disabled placeholders', () => {
    const { getByTestId, queryByTestId } = wrap({ route: '/' })
    // Library is a project-scoped item → must render as a disabled div.
    const disabledLibrary = getByTestId('sidebar-nav-disabled-library')
    expect(disabledLibrary.getAttribute('aria-disabled')).toBe('true')
    expect(disabledLibrary.tagName.toLowerCase()).toBe('div')
    // Reader, Statistics also disabled.
    expect(
      queryByTestId('sidebar-nav-disabled-reader'),
    ).not.toBeNull()
    expect(
      queryByTestId('sidebar-nav-disabled-statistics'),
    ).not.toBeNull()
    // Dashboard and Settings remain enabled (global slugs).
    expect(queryByTestId('sidebar-nav-disabled-dashboard')).toBeNull()
    expect(queryByTestId('sidebar-nav-disabled-settings')).toBeNull()
  })

  it('hides the empty-state hint and re-enables links once a project is in the route', () => {
    const { getByTestId, queryByTestId } = wrap({
      route: '/projects/some-id/library',
    })
    // No hint while inside a project.
    expect(queryByTestId('sidebar-empty-hint')).toBeNull()
    // Library is no longer a disabled placeholder.
    expect(queryByTestId('sidebar-nav-disabled-library')).toBeNull()
    // Sidebar itself still mounted.
    expect(getByTestId('sidebar')).toBeTruthy()
  })
})
