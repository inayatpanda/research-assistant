import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Reference integrity panel — datasets resolution.
 *
 * Citations like `<sup data-citation data-article-id="dataset_<id>">`
 * resolve against the project's datasets list, NOT the article library, so
 * the panel must NOT flag them as orphan when the dataset exists.
 *
 * We mock the api module factory once and mutate the inner state per test
 * via the helpers below. Assertions use `toBeTruthy() / queryBy* === null`
 * to match the existing tests in this folder (no jest-dom extension).
 */

type Article = { id: string; title: string }
type Dataset = { id: string; filename: string }
type SectionContent = { content: string }

const state: {
  articles: Article[]
  datasets: Dataset[]
  sections: Record<string, SectionContent>
} = {
  articles: [],
  datasets: [],
  sections: {},
}

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    articlesApi: { list: vi.fn(async () => state.articles) },
    datasetsApi: { list: vi.fn(async () => state.datasets) },
    manuscriptApi: {
      getSection: vi.fn(async (_pid: string, sec: string) => state.sections[sec] ?? { content: '' }),
    },
  }
})

import { ReferenceIntegrityPanel } from '../ReferenceIntegrityPanel'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

const SECTIONS = ['Abstract', 'Introduction', 'Methodology', 'Results', 'Discussion', 'Conclusion']

function seed(opts: {
  articles?: Article[]
  datasets?: Dataset[]
  sections?: Partial<Record<(typeof SECTIONS)[number], string>>
}) {
  state.articles = opts.articles ?? []
  state.datasets = opts.datasets ?? []
  state.sections = {}
  for (const s of SECTIONS) state.sections[s] = { content: '' }
  for (const [k, html] of Object.entries(opts.sections ?? {})) {
    state.sections[k] = { content: html ?? '' }
  }
}

describe('ReferenceIntegrityPanel — dataset citations', () => {
  beforeEach(() => {
    seed({})
  })
  afterEach(cleanup)

  it('does NOT flag a dataset citation as orphan when the dataset exists', async () => {
    seed({
      datasets: [{ id: 'abc123', filename: 'trial.csv' }],
      sections: {
        Results:
          '<p>Mean differed <sup data-citation data-article-id="dataset_abc123">[1]</sup>.</p>',
      },
    })
    wrap(<ReferenceIntegrityPanel projectId="p1" />)
    await waitFor(() => {
      expect(screen.getByText(/1 reference cited/i)).toBeTruthy()
    })
    // No "Citations pointing to articles not in your library" heading should appear.
    expect(
      screen.queryByText(/Citations pointing to articles not in your library/i),
    ).toBeNull()
    // And the cited dataset id is NOT listed as orphan.
    expect(screen.queryByText(/dataset_abc/i)).toBeNull()
  })

  it('FLAGS a dataset citation when the dataset is missing from the project', async () => {
    seed({
      datasets: [],
      sections: {
        Results:
          '<p>Mean differed <sup data-citation data-article-id="dataset_missing">[1]</sup>.</p>',
      },
    })
    wrap(<ReferenceIntegrityPanel projectId="p1" />)
    await waitFor(() => {
      expect(
        screen.getByText(/Citations pointing to articles not in your library/i),
      ).toBeTruthy()
    })
    // Truncated id is rendered for the orphan list (first 12 chars).
    expect(screen.getByText(/dataset_miss/)).toBeTruthy()
  })

  it('FLAGS a missing article citation but PASSES a dataset citation in the same manuscript', async () => {
    seed({
      articles: [{ id: 'a-known', title: 'Known paper' }],
      datasets: [{ id: 'ds-known', filename: 'trial.csv' }],
      sections: {
        Introduction:
          '<p><sup data-citation data-article-id="a-known">[1]</sup>'
          + '<sup data-citation data-article-id="a-unknown">[2]</sup></p>',
        Results:
          '<p><sup data-citation data-article-id="dataset_ds-known">[3]</sup></p>',
      },
    })
    wrap(<ReferenceIntegrityPanel projectId="p1" />)
    await waitFor(() => {
      expect(
        screen.getByText(/Citations pointing to articles not in your library/i),
      ).toBeTruthy()
    })
    // Only the unknown article appears as orphan — the dataset is recognised.
    expect(screen.getByText(/a-unknown/)).toBeTruthy()
    expect(screen.queryByText(/dataset_ds-/)).toBeNull()
  })
})
