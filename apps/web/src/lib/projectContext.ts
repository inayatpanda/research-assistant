import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type ActiveProjectState = {
  projectId: string | null
  set: (id: string | null) => void
  clear: () => void
}

export const useActiveProject = create<ActiveProjectState>()(
  persist(
    (set) => ({
      projectId: null,
      set: (id) => set({ projectId: id }),
      clear: () => set({ projectId: null }),
    }),
    { name: 'research-active-project' },
  ),
)
