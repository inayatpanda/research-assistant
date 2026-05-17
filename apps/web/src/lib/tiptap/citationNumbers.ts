import { create } from 'zustand'

import type { CitationNumberMap } from './citationEngine'

type State = {
  map: CitationNumberMap
  setMap: (m: CitationNumberMap) => void
}

/** Global-ish singleton citation-number store. The editor recomputes the map on
 *  every doc update; the NodeView re-renders against it. We use a single global
 *  store rather than per-section because the Final Manuscript view also reads
 *  it for cross-section continuous numbering. */
export const useCitationNumbers = create<State>((set) => ({
  map: new Map(),
  setMap: (m) => set({ map: m }),
}))
