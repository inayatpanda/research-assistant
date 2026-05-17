import { create } from 'zustand'

import type { HighlightColour } from '@/lib/api'

type ReaderState = {
  activeColour: HighlightColour | null
  setActiveColour: (c: HighlightColour | null) => void
  scale: number
  setScale: (s: number) => void
  currentPage: number
  setCurrentPage: (p: number) => void
}

export const useReader = create<ReaderState>((set) => ({
  activeColour: null,
  setActiveColour: (c) => set({ activeColour: c }),
  scale: 1.0,
  setScale: (s) => set({ scale: Math.max(0.5, Math.min(3.0, s)) }),
  currentPage: 1,
  setCurrentPage: (p) => set({ currentPage: Math.max(1, p) }),
}))

export const SECTION_FOR_COLOUR: Record<HighlightColour, 'Introduction' | 'Methodology' | 'Results' | 'Discussion'> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}
