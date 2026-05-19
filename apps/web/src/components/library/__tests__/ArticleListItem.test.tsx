import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return { ...actual, useNavigate: () => navigateMock }
})

import type { Article } from '@/lib/api'

import { ArticleListItem } from '../ArticleListItem'

function makeArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: 'a-1',
    user_id: 'u-1',
    project_id: 'p-1',
    title: 'Anterior approach reduces ambulation time',
    authors: ['Jane Doe', 'John Smith'],
    journal: 'Hip International',
    year: 2024,
    volume: null,
    issue: null,
    pages: null,
    doi: '10.1234/foo',
    pmid: null,
    file_ref: { backend: 'local', key: 'a-1.pdf' },
    file_type: 'pdf',
    abstract: null,
    study_design: 'cohort',
    review_status: 'pending',
    exclusion_reason: null,
    conflict_of_interest: null,
    source: 'upload',
    created_at: '2024-01-01T00:00:00Z',
    file_url: '/files/a-1.pdf',
    ...overrides,
  } as Article
}

function setup(article: Article) {
  return render(
    <MemoryRouter>
      <ArticleListItem
        article={article}
        index={0}
        onEdit={() => {}}
        onDelete={() => {}}
      />
    </MemoryRouter>,
  )
}

describe('ArticleListItem — #R1 Open in Reader', () => {
  afterEach(() => {
    cleanup()
    navigateMock.mockReset()
  })

  it('navigates to the reader when the BookOpen icon is clicked', () => {
    setup(makeArticle())
    const btn = screen.getByRole('button', { name: /open in reader/i })
    expect((btn as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(btn)
    expect(navigateMock).toHaveBeenCalledWith('/projects/p-1/reader/a-1')
  })

  it('disables the Open-in-Reader button when no file is attached', () => {
    setup(makeArticle({ file_url: null, file_ref: null }))
    const btn = screen.getByRole('button', { name: /open in reader/i })
    expect((btn as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(btn)
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
