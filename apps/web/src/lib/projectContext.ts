/**
 * Project context (MP12.5 — URL-scoped project routing).
 *
 * Two surfaces live in this module:
 *
 * 1. A lightweight React Context (`ProjectContext`) populated by the
 *    `<ProjectLayoutGuard>` element in `App.tsx`. Pages inside a
 *    `/projects/:projectId/*` route read the active projectId / project
 *    object via `useProjectId()` and `useProject()`. This is the source
 *    of truth for "what project is this tab showing".
 *
 * 2. A Zustand `useLastViewedProject` store (persisted to localStorage)
 *    that records the **last** project the user opened anywhere. It is
 *    used by the sidebar/Topbar to redirect generic module links to the
 *    most-recent project, and by the legacy `<Route path="/library">`
 *    redirects to keep old links working.
 *
 * The store was previously named `useActiveProject` with key
 * `research-active-project`. The new name (`useLastViewedProject` /
 * `research-last-viewed-project`) better matches its new role of
 * "default project for new tabs" — projects are no longer "active"
 * globally, they're active per-tab via the URL. A small read-time
 * migration copies the old key forward so existing users keep their
 * last-viewed project across the rename.
 */
import { createContext, useContext } from 'react'
import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

import type { Project } from './api'

/**
 * jsdom 29 (used by vitest's `environment: 'jsdom'`) does not expose
 * `window.localStorage`. The zustand persist middleware would crash
 * on `setItem` in that case, so we provide an in-memory fallback any
 * time `window.localStorage` is missing.
 */
function getStableStorage(): StateStorage {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage
  }
  const memory = new Map<string, string>()
  return {
    getItem: (k) => memory.get(k) ?? null,
    setItem: (k, v) => {
      memory.set(k, v)
    },
    removeItem: (k) => {
      memory.delete(k)
    },
  }
}

// ---------------------------------------------------------------------------
// Zustand store — "last viewed project" (used outside any project route).
// ---------------------------------------------------------------------------

type LastViewedProjectState = {
  projectId: string | null
  set: (id: string | null) => void
  clear: () => void
}

const NEW_KEY = 'research-last-viewed-project'
const OLD_KEY = 'research-active-project'

/**
 * One-shot migration: if the new key isn't in localStorage yet but the
 * legacy `research-active-project` key is, copy its `projectId` forward
 * so users don't lose their last-viewed project across the rename.
 */
function migrateLegacyKey() {
  if (typeof window === 'undefined') return
  // jsdom 29 omits `window.localStorage` by default — guard so the
  // module still loads under the test environment.
  if (!window.localStorage) return
  try {
    if (window.localStorage.getItem(NEW_KEY)) return
    const old = window.localStorage.getItem(OLD_KEY)
    if (!old) return
    const parsed = JSON.parse(old) as { state?: { projectId?: string | null } }
    const projectId = parsed?.state?.projectId ?? null
    if (projectId) {
      const migrated = { state: { projectId }, version: 0 }
      window.localStorage.setItem(NEW_KEY, JSON.stringify(migrated))
    }
    window.localStorage.removeItem(OLD_KEY)
  } catch {
    // localStorage may be unavailable (SSR, private mode); swallow silently.
  }
}

migrateLegacyKey()

export const useLastViewedProject = create<LastViewedProjectState>()(
  persist(
    (set) => ({
      projectId: null,
      set: (id) => set({ projectId: id }),
      clear: () => set({ projectId: null }),
    }),
    { name: NEW_KEY, storage: createJSONStorage(getStableStorage) },
  ),
)

/**
 * Back-compat alias. New code should import `useLastViewedProject`.
 * The old name is kept as a re-export so any straggler imports compile.
 * @deprecated Use `useLastViewedProject` instead.
 */
export const useActiveProject = useLastViewedProject

// ---------------------------------------------------------------------------
// React Context — "the project this tab is currently showing".
// ---------------------------------------------------------------------------

export type ProjectContextValue = {
  projectId: string
  project: Project | null
}

export const ProjectContext = createContext<ProjectContextValue | null>(null)

/**
 * Returns the projectId from the surrounding `<ProjectLayoutGuard>`. Throws
 * if called outside a `/projects/:projectId/*` route — the guard always
 * provides a non-null projectId.
 */
export function useProjectId(): string {
  const ctx = useContext(ProjectContext)
  if (!ctx) {
    throw new Error(
      'useProjectId() must be called inside a /projects/:projectId/* route',
    )
  }
  return ctx.projectId
}

/**
 * Returns the full Project object if the guard's `projectsApi.get(...)`
 * call has resolved. May briefly return `null` during the first paint.
 */
export function useProject(): Project | null {
  const ctx = useContext(ProjectContext)
  return ctx?.project ?? null
}
