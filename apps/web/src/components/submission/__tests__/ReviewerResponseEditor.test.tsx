import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { createMock, updateMock } = vi.hoisted(() => ({
  createMock: vi.fn(
    async (_pid: string, body: { reviewer_label: string }) => ({
      id: 'rr1',
      project_id: 'p1',
      reviewer_label: body.reviewer_label,
      comments: [
        { comment_text: 'Add power calc.', response_html: '<p>Done.</p>' },
      ],
      created_at: 'x',
      updated_at: 'x',
    }),
  ),
  updateMock: vi.fn(
    async (
      _pid: string,
      _rid: string,
      body: Record<string, unknown>,
    ) => ({
      id: 'rr1',
      project_id: 'p1',
      reviewer_label:
        (body.reviewer_label as string | undefined) ?? 'Reviewer 1',
      comments:
        (body.comments as Array<{
          comment_text: string
          response_html: string
        }>) ?? [],
      created_at: 'x',
      updated_at: 'x',
    }),
  ),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    reviewerResponseApi: {
      list: vi.fn(async () => [
        {
          id: 'rr1',
          project_id: 'p1',
          reviewer_label: 'Reviewer 1',
          comments: [
            { comment_text: 'Add power calc.', response_html: '<p>Done.</p>' },
            { comment_text: 'Fix typo.', response_html: '<p>Fixed.</p>' },
          ],
          created_at: 'x',
          updated_at: 'x',
        },
      ]),
      create: createMock,
      update: updateMock,
      delete: vi.fn(async () => undefined),
    },
  }
})

import { ReviewerResponseEditor } from '../ReviewerResponseEditor'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

describe('ReviewerResponseEditor', () => {
  afterEach(cleanup)

  it('renders existing reviewer rows + per-comment editors', async () => {
    wrap(<ReviewerResponseEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('rr-row-rr1'))
    expect(screen.getByTestId('rr-comment-text-rr1-0')).toBeTruthy()
    expect(screen.getByTestId('rr-comment-text-rr1-1')).toBeTruthy()
  })

  it('drafts new responses from a raw comments block', async () => {
    wrap(<ReviewerResponseEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('rr-new-raw'))
    fireEvent.change(screen.getByTestId('rr-new-label'), {
      target: { value: 'Reviewer 2' },
    })
    fireEvent.change(screen.getByTestId('rr-new-raw'), {
      target: { value: '1. Power calc.\n\n2. Typo.' },
    })
    fireEvent.click(screen.getByTestId('rr-draft-button'))
    await waitFor(() => expect(createMock).toHaveBeenCalled())
    expect(createMock.mock.calls[0]?.[1]).toMatchObject({
      reviewer_label: 'Reviewer 2',
    })
  })

  it('saves edits to an existing reviewer row', async () => {
    wrap(<ReviewerResponseEditor projectId="p1" />)
    await waitFor(() => screen.getByTestId('rr-row-rr1'))
    const text = screen.getByTestId(
      'rr-comment-text-rr1-0',
    ) as HTMLTextAreaElement
    fireEvent.change(text, { target: { value: 'Edited by user' } })
    fireEvent.click(screen.getByTestId('rr-save-rr1'))
    await waitFor(() => expect(updateMock).toHaveBeenCalled())
    const body = updateMock.mock.calls[0]?.[2] as {
      comments: { comment_text: string }[]
    }
    expect(body.comments[0]?.comment_text).toBe('Edited by user')
  })
})
