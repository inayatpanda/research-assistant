/**
 * Phase M1.5 — MobileList smoke tests.
 *
 *   1. Renders all rows with their titles + subtitles.
 *   2. Clicking an interactive row fires the onClick handler.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Settings } from 'lucide-react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MobileList, MobileListRow } from '@/mobile/components/MobileList'

afterEach(cleanup)

describe('MobileList', () => {
  it('renders a group title and rows with subtitles', () => {
    render(
      <MobileList groupTitle="Account">
        <MobileListRow icon={Settings} title="Settings" subtitle="general" />
        <MobileListRow title="Log out" />
      </MobileList>,
    )
    expect(screen.getByTestId('mobile-list-group-title').textContent).toBe('Account')
    expect(screen.getByText('Settings')).toBeTruthy()
    expect(screen.getByText('general')).toBeTruthy()
    expect(screen.getByText('Log out')).toBeTruthy()
  })

  it('fires onClick for interactive rows but not static rows', () => {
    const onClick = vi.fn()
    const onClickStatic = vi.fn()
    render(
      <MobileList>
        <MobileListRow
          title="Tap me"
          onClick={onClick}
          data-testid="row-button"
        />
        <MobileListRow
          title="Read-only"
          static
          onClick={onClickStatic}
          data-testid="row-static"
        />
      </MobileList>,
    )
    fireEvent.click(screen.getByTestId('row-button'))
    expect(onClick).toHaveBeenCalledTimes(1)
    // Static row doesn't wire the click — calling it shouldn't fire.
    fireEvent.click(screen.getByTestId('row-static'))
    expect(onClickStatic).not.toHaveBeenCalled()
  })
})
