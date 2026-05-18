import { describe, expect, it } from 'vitest'

import type { Article } from '../api'
import {
  apaEntry,
  bibliographyEntry,
  harvardEntry,
  ieeeEntry,
  toBibTeX,
  toCSLJSON,
  toRIS,
  vancouverEntry,
} from '../bibliographyFormat'

function makeArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: 'art-1',
    user_id: 'u1',
    project_id: 'p1',
    title: 'A randomised trial of widget X',
    authors: ['Jane Doe', 'John Smith'],
    journal: 'Journal of Widgets',
    year: 2024,
    volume: '12',
    issue: '3',
    pages: '100-110',
    doi: '10.1234/widget.2024',
    file_ref: null,
    file_type: null,
    study_design: null,
    review_status: 'pending',
    exclusion_reason: null,
    conflict_of_interest: null,
    created_at: '2024-01-01T00:00:00Z',
    file_url: null,
    ...overrides,
  }
}

describe('vancouverEntry', () => {
  it('formats a typical journal article with numbering', () => {
    const out = vancouverEntry(makeArticle(), 1)
    expect(out).toBe(
      '1. Doe J, Smith J. A randomised trial of widget X. Journal of Widgets. 2024;12(3):100-110. doi:10.1234/widget.2024',
    )
  })
  it('caps author list at 6 and appends "et al."', () => {
    const a = makeArticle({
      authors: ['A One', 'B Two', 'C Three', 'D Four', 'E Five', 'F Six', 'G Seven'],
    })
    expect(vancouverEntry(a)).toContain('One A, Two B, Three C, Four D, Five E, Six F, et al.')
  })
})

describe('apaEntry', () => {
  it('uses ampersand before final author + en-dash pages', () => {
    const out = apaEntry(makeArticle())
    expect(out).toBe(
      'Doe, J., & Smith, J. (2024). A randomised trial of widget X. Journal of Widgets, 12(3), 100–110. https://doi.org/10.1234/widget.2024',
    )
  })
  it('handles single author', () => {
    const out = apaEntry(makeArticle({ authors: ['Jane Doe'] }))
    expect(out.startsWith('Doe, J. (2024).')).toBe(true)
  })
})

describe('harvardEntry', () => {
  it('uses "and" between two authors and quoted title', () => {
    const out = harvardEntry(makeArticle({ authors: ['Jane Doe', 'John Smith'] }))
    expect(out).toContain("'A randomised trial of widget X'")
    // 3+ authors collapses to "et al." per Cite Them Right; 2 authors gets "and".
    // (We pass only 2 so expect "and" form here.)
    expect(out.startsWith('Doe, J. and Smith, J. (2024)')).toBe(true)
  })
  it('collapses 3+ authors to "et al."', () => {
    const out = harvardEntry(
      makeArticle({ authors: ['Jane Doe', 'John Smith', 'Mary Adams'] }),
    )
    expect(out.startsWith('Doe, J. et al. (2024)')).toBe(true)
  })
})

describe('ieeeEntry', () => {
  it('renders initials-first, vol/no, pages, year and doi', () => {
    const out = ieeeEntry(makeArticle(), 7)
    expect(out).toBe(
      '[7] J. Doe and J. Smith, "A randomised trial of widget X," Journal of Widgets, vol. 12, no. 3, pp. 100–110, 2024, doi: 10.1234/widget.2024.',
    )
  })
})

describe('bibliographyEntry dispatch', () => {
  const a = makeArticle()
  it('dispatches vancouver', () => {
    expect(bibliographyEntry(a, 1, 'vancouver').startsWith('1. ')).toBe(true)
  })
  it('dispatches apa', () => {
    expect(bibliographyEntry(a, 1, 'apa')).toContain('(2024)')
  })
  it('dispatches harvard', () => {
    expect(bibliographyEntry(a, 1, 'harvard')).toContain("'A randomised trial")
  })
  it('dispatches ieee with bracketed number', () => {
    expect(bibliographyEntry(a, 1, 'ieee').startsWith('[1] ')).toBe(true)
  })
})

describe('toBibTeX', () => {
  it('produces an @article entry with key from first author + year', () => {
    const out = toBibTeX([makeArticle()])
    expect(out).toMatch(/@article\{Doe2024,/)
    expect(out).toContain('author = {Jane Doe and John Smith}')
    expect(out).toContain('title = {{A randomised trial of widget X}}')
    expect(out).toContain('journal = {Journal of Widgets}')
    expect(out).toContain('year = {2024}')
    expect(out).toContain('pages = {100--110}')
    expect(out).toContain('doi = {10.1234/widget.2024}')
  })
})

describe('toRIS', () => {
  it('emits TY, AU, PY, SP/EP, DO and ER markers', () => {
    const out = toRIS([makeArticle()])
    expect(out).toContain('TY  - JOUR')
    expect(out).toContain('AU  - Jane Doe')
    expect(out).toContain('AU  - John Smith')
    expect(out).toContain('PY  - 2024')
    expect(out).toContain('SP  - 100')
    expect(out).toContain('EP  - 110')
    expect(out).toContain('DO  - 10.1234/widget.2024')
    expect(out).toContain('ER  - ')
  })
})

describe('toCSLJSON', () => {
  it('produces an article-journal item with author objects and issued date-parts', () => {
    const out = JSON.parse(toCSLJSON([makeArticle()]))
    expect(out).toHaveLength(1)
    const item = out[0]
    expect(item.type).toBe('article-journal')
    expect(item.author).toEqual([
      { family: 'Doe', given: 'Jane' },
      { family: 'Smith', given: 'John' },
    ])
    expect(item.issued).toEqual({ 'date-parts': [[2024]] })
    expect(item.DOI).toBe('10.1234/widget.2024')
  })
})
