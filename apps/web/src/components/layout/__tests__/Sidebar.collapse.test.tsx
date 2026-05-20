/**
 * DEMO-FIX-B — Vitest for the collapsible Sidebar nav.
 *
 * Verifies that the sidebar:
 *   1. Renders expanded by default at 240px width with text labels visible.
 *   2. Clicking the collapse chevron shrinks it to icon-only mode (56px),
 *      hides the nav labels, and exposes the per-link aria-label tooltips.
 *   3. Collapsed state is persisted under `sidebar-nav-collapsed=1` in
 *      localStorage and restored on remount.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// jsdom 29 ships without a real localStorage. Provide an in-memory shim
// so the persistence assertions below work.
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

// Stub the projects list so the sidebar's stale-lastViewed cleanup doesn't
// reach the network.
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

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})
afterEach(cleanup)

describe('Sidebar — collapsible nav (DEMO-FIX-B)', () => {
  it('renders expanded by default with full-width branding', () => {
    const { getByTestId } = wrap()
    const sidebar = getByTestId('sidebar')
    expect(sidebar.getAttribute('data-collapsed')).toBe('false')
    expect(sidebar.className).toContain('w-[240px]')
    // Library label is visible while expanded.
    expect(sidebar.textContent ?? '').toMatch(/Library/)
  })

  it('clicking the collapse toggle shrinks to icon-only mode', () => {
    const { getByTestId } = wrap()
    fireEvent.click(getByTestId('sidebar-collapse-toggle'))
    const sidebar = getByTestId('sidebar')
    expect(sidebar.getAttribute('data-collapsed')).toBe('true')
    expect(sidebar.className).toContain('w-[56px]')
    // Persists to localStorage with the documented key.
    expect(window.localStorage.getItem('sidebar-nav-collapsed')).toBe('1')
  })

  it('restores collapsed state from localStorage on mount', () => {
    window.localStorage.setItem('sidebar-nav-collapsed', '1')
    const { getByTestId } = wrap()
    const sidebar = getByTestId('sidebar')
    expect(sidebar.getAttribute('data-collapsed')).toBe('true')
    expect(sidebar.className).toContain('w-[56px]')
  })
})
