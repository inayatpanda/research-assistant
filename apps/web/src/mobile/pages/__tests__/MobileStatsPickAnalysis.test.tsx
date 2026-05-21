/**
 * Phase M4.3 — MobileStatsPickAnalysis smoke tests.
 *
 *   1. All seven analysis chips render with their hints.
 *   2. Tapping a chip navigates to the configure route for that analysis.
 */
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import MobileStatsPickAnalysis from '@/mobile/pages/MobileStatsPickAnalysis'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/m/stats/:datasetId/pick-analysis"
          element={<MobileStatsPickAnalysis />}
        />
        <Route
          path="/m/stats/:datasetId/configure/:analysisType"
          element={<div data-testid="configure-route">configure</div>}
        />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
})

describe('MobileStatsPickAnalysis', () => {
  it('renders all 7 analysis chips and the desktop hint', () => {
    renderAt('/m/stats/ds-1/pick-analysis')
    expect(screen.getByTestId('mstats-analysis-t_test')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-anova')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-chi_square')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-correlation')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-linear_reg')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-logistic_reg')).toBeTruthy()
    expect(screen.getByTestId('mstats-analysis-survival')).toBeTruthy()
    expect(screen.getByTestId('mstats-desktop-hint')).toBeTruthy()
  })

  it('navigates to the configure route on chip tap', async () => {
    renderAt('/m/stats/ds-1/pick-analysis')
    fireEvent.click(screen.getByTestId('mstats-analysis-t_test'))
    await waitFor(() =>
      expect(screen.getByTestId('configure-route')).toBeTruthy(),
    )
  })
})
