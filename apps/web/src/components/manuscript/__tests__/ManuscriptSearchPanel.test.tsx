import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ManuscriptSearchPanel,
  __testing,
  type SectionHtml,
} from '../ManuscriptSearchPanel'

const { findMatches, stripHtmlForSearch } = __testing

const SECTIONS: SectionHtml[] = [
  { section: 'Abstract', html: '<p>Hip arthroplasty is a common surgery.</p>' },
  { section: 'Introduction', html: '<p>The Bayesian model is used in arthroplasty research.</p>' },
  { section: 'Methodology', html: '<p>We compared cohorts using propensity-score matching.</p>' },
  {
    section: 'Results',
    html:
      '<p>Outcome scores favoured the arthroplasty group <sup data-citation data-article-id="a1">[1]</sup>.</p>',
  },
  { section: 'Discussion', html: '<p>Limitations include sample size.</p>' },
  { section: 'Conclusion', html: '' },
]

describe('ManuscriptSearchPanel unit helpers', () => {
  it('strips HTML tags and inline citation sups', () => {
    const html = '<p>Foo <sup data-citation>[1]</sup> bar.</p>'
    const out = stripHtmlForSearch(html)
    expect(out).not.toContain('<')
    expect(out).not.toContain('[1]')
    expect(out).toContain('Foo')
    expect(out).toContain('bar')
  })

  it('returns no matches for empty query', () => {
    expect(findMatches(SECTIONS, '')).toEqual([])
    expect(findMatches(SECTIONS, '   ')).toEqual([])
  })

  it('finds matches across multiple sections', () => {
    const hits = findMatches(SECTIONS, 'arthroplasty')
    const sections = hits.map((h) => h.section)
    expect(sections).toContain('Abstract')
    expect(sections).toContain('Introduction')
    expect(sections).toContain('Results')
    // Does NOT match the sup text since we stripped it.
    expect(hits.every((h) => !h.preview.includes('[1]'))).toBe(true)
  })

  it('preview text is at most 80 chars and contains the match', () => {
    const hits = findMatches(SECTIONS, 'arthroplasty')
    for (const h of hits) {
      expect(h.preview.length).toBeLessThanOrEqual(80)
      expect(h.preview.toLowerCase()).toContain('arthroplasty')
    }
  })

  it('case-insensitive search', () => {
    const hits = findMatches(SECTIONS, 'BAYESIAN')
    expect(hits.length).toBeGreaterThan(0)
  })
})

// -- Component-level tests ---------------------------------------------------

describe('ManuscriptSearchPanel component', () => {
  afterEach(cleanup)

  it('shows nothing for an empty query', () => {
    render(
      <ManuscriptSearchPanel
        sections={SECTIONS}
        onJump={() => {}}
        onClose={() => {}}
      />,
    )
    expect(screen.queryByTestId('search-hit')).toBeNull()
  })

  it('renders hits grouped by section and calls onJump when clicked', async () => {
    const onJump = vi.fn()
    render(
      <ManuscriptSearchPanel
        sections={SECTIONS}
        onJump={onJump}
        onClose={() => {}}
      />,
    )
    const input = screen.getByPlaceholderText(/search/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'arthroplasty' } })
    // Debounce 150ms.
    await waitFor(() => {
      const hits = screen.queryAllByTestId('search-hit')
      expect(hits.length).toBeGreaterThan(0)
    }, { timeout: 800 })
    const firstHit = screen.getAllByTestId('search-hit')[0]
    fireEvent.click(firstHit)
    expect(onJump).toHaveBeenCalledTimes(1)
    const arg = onJump.mock.calls[0][0]
    expect(arg.section).toBeTruthy()
    expect(typeof arg.matchIndex).toBe('number')
  })

  it('Escape calls onClose', async () => {
    const onClose = vi.fn()
    render(
      <ManuscriptSearchPanel
        sections={SECTIONS}
        onJump={() => {}}
        onClose={onClose}
      />,
    )
    const input = screen.getByPlaceholderText(/search/i) as HTMLInputElement
    fireEvent.keyDown(input, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('navigates next/prev with F3 and Shift+F3', async () => {
    const onJump = vi.fn()
    render(
      <ManuscriptSearchPanel
        sections={SECTIONS}
        onJump={onJump}
        onClose={() => {}}
      />,
    )
    const input = screen.getByPlaceholderText(/search/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'arthroplasty' } })
    await waitFor(() => {
      expect(screen.getAllByTestId('search-hit').length).toBeGreaterThan(1)
    }, { timeout: 800 })
    onJump.mockClear()
    // F3 advances.
    fireEvent.keyDown(input, { key: 'F3' })
    expect(onJump).toHaveBeenCalledTimes(1)
    // Shift+F3 retreats.
    fireEvent.keyDown(input, { key: 'F3', shiftKey: true })
    expect(onJump).toHaveBeenCalledTimes(2)
  })
})
