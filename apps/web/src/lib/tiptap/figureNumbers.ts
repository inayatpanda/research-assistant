/**
 * Phase 4.5 — Figure-number store shared across:
 *   • the FiguresPanel / FigureNumberingPanel (source of truth on save)
 *   • the FigRef TipTap NodeView (renders the visible "Figure N" string)
 *
 * Same shape as ``citationNumbers`` — a single global store that the
 * editor's wrappers seed from ``figuresApi.list``, and the NodeView
 * reads from on every render. When ``Auto-renumber`` reorders the
 * figures server-side, the FiguresPanel writes the fresh map here and
 * every FigRef NodeView updates instantly (no editor reload needed).
 */
import { create } from 'zustand'

export type FigureNumberMap = Map<string, number>

type State = {
  map: FigureNumberMap
  setMap: (m: FigureNumberMap) => void
}

export const useFigureNumbers = create<State>((set) => ({
  map: new Map(),
  setMap: (m) => set({ map: m }),
}))

/** Convenience: hydrate the store from a list of ``{id, figure_number}``. */
export function setFigureNumbersFrom(
  figures: ReadonlyArray<{ id: string; figure_number: number }>,
): void {
  const next: FigureNumberMap = new Map()
  for (const f of figures) next.set(f.id, f.figure_number)
  useFigureNumbers.getState().setMap(next)
}
