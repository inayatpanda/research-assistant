import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { draftMock, updateMock } = vi.hoisted(() => ({
  draftMock: vi.fn(async () => ({
    id: 'cl1',
    project_id: 'p1',
    target_journal: 'jbjs',
    novelty_points: ['First MC trial'],
    body_html: '<p>AI-drafted body</p>',
    ai_model: 'fake',
    created_at: 'x',
    updated_at: 'x',
  })),
  updateMock: vi.fn(
    async (_pid: string, body: Record<string, unknown>) => ({
      id: 'cl1',
      project_id: 'p1',
      target_journal: (body.target_journal as string | null) ?? null,
      novelty_points: (body.novelty_points as string[]) ?? [],
      body_html: (body.body_html as string) ?? '',
      ai_model: null,
      created_at: 'x',
      updated_at: 'x',
    }),
  ),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    coverLetterApi: {
      get: vi.fn(async () => ({
        id: 'cl1',
        project_id: 'p1',
        target_journal: null,
        novelty_points: [],
        body_html: '',
        ai_model: null,
        created_at: 'x',
        updated_at: 'x',
      })),
      update: updateMock,
      draft: draftMock,
    },
    journalTemplatesApi: {
      list: vi.fn(async () => [
        {
          key: 'jbjs',
          label: 'JBJS',
          max_total_words: 4000,
          max_words_by_section: {},
          required_sections: [],
          structured_abstract: true,
          reference_style: 'vancouver',
          max_figures: 8,
          max_tables: 4,
        },
      ]),
    },
  }
})

import { CoverLetterEditor } from '../CoverLetterEditor'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

describe('CoverLetterEditor', () => {
  afterEach(cleanup)

  it('shows the editor surface after loading', async () => {
    wrap(<CoverLetterEditor projectId="p1" />)
    await waitFor(() =>
      expect(screen.getByTestId('cover-letter-editor')).toBeTruthy(),
    )
    expect(screen.getByTestId('cover-journal-trigger')).toBeTruthy()
    expect(screen.getByTestId('cover-body-input')).toBeTruthy()
  })

  it('adds and removes novelty bullets', async () => {
    wrap(<CoverLetterEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('cover-novelty-input'))
    const input = screen.getByTestId('cover-novelty-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'First MC trial' } })
    fireEvent.click(screen.getByTestId('cover-novelty-add'))
    await waitFor(() => {
      expect(screen.getByTestId('cover-novelty-remove-0')).toBeTruthy()
    })
    fireEvent.click(screen.getByTestId('cover-novelty-remove-0'))
    await waitFor(() => {
      expect(screen.queryByTestId('cover-novelty-remove-0')).toBeNull()
    })
  })

  it('disables the AI draft button until a journal is picked', async () => {
    wrap(<CoverLetterEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('cover-draft-button'))
    const draftBtn = screen.getByTestId(
      'cover-draft-button',
    ) as HTMLButtonElement
    expect(draftBtn.disabled).toBe(true)
  })

  it('saves the cover letter via PATCH', async () => {
    wrap(<CoverLetterEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('cover-body-input'))
    const body = screen.getByTestId('cover-body-input') as HTMLTextAreaElement
    fireEvent.change(body, { target: { value: '<p>Manually edited</p>' } })
    fireEvent.click(screen.getByTestId('cover-save-button'))
    await waitFor(() => {
      expect(updateMock).toHaveBeenCalled()
    })
    expect(updateMock.mock.calls[0]?.[1]).toMatchObject({
      body_html: '<p>Manually edited</p>',
    })
  })
})
