import { cleanup, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { JournalChip } from '../JournalChip'

vi.mock('@/hooks/useJournalTemplates', () => ({
  useJournalTemplate: (key: string | null) => {
    if (key !== 'jbjs') return null
    return {
      key: 'jbjs',
      label: 'JBJS (Journal of Bone & Joint Surgery)',
      max_total_words: 4000,
      max_words_by_section: {},
      required_sections: [],
      structured_abstract: true,
      reference_style: 'vancouver' as const,
    }
  },
}))

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>)
}

describe('JournalChip', () => {
  afterEach(cleanup)

  it('renders the "No template" call to action when key is null', () => {
    const { getByText } = wrap(<JournalChip templateKey={null} />)
    expect(getByText(/No template/i)).toBeTruthy()
  })

  it('shows the journal label and max-words when a template is set', () => {
    const { container } = wrap(<JournalChip templateKey="jbjs" />)
    expect(container.textContent).toMatch(/JBJS/)
    expect(container.textContent).toMatch(/4000 words/)
  })
})
