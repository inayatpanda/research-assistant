import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { WordCountBar } from '../WordCountBar'

// Stub the templates hook so we don't hit the network
vi.mock('@/hooks/useJournalTemplates', () => ({
  useJournalTemplate: (key: string | null) => {
    if (key !== 'jbjs') return null
    return {
      key: 'jbjs',
      label: 'JBJS',
      max_total_words: 4000,
      max_words_by_section: { Methodology: 1200 },
      required_sections: [],
      structured_abstract: true,
      reference_style: 'vancouver' as const,
    }
  },
}))

function wrap(node: React.ReactNode) {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}>{node}</QueryClientProvider>)
}

describe('WordCountBar', () => {
  afterEach(cleanup)

  it('renders basic counts', () => {
    const { container } = wrap(
      <WordCountBar
        sectionWords={50}
        totalWords={100}
        saving={false}
        savedAt={null}
      />,
    )
    expect(container.textContent).toMatch(/50/)
    expect(container.textContent).toMatch(/100/)
  })

  it('turns amber at 90% of the section cap', () => {
    const { container } = wrap(
      <WordCountBar
        sectionWords={1100}
        totalWords={2000}
        saving={false}
        savedAt={null}
        templateKey="jbjs"
        activeSectionName="Methodology"
      />,
    )
    const amber = container.querySelector('.text-amber-600')
    expect(amber).not.toBeNull()
  })

  it('turns red at 100% of the section cap', () => {
    const { container } = wrap(
      <WordCountBar
        sectionWords={1300}
        totalWords={2000}
        saving={false}
        savedAt={null}
        templateKey="jbjs"
        activeSectionName="Methodology"
      />,
    )
    const red = container.querySelector('.text-red-600')
    expect(red).not.toBeNull()
  })

  it('shows the section cap when template active', () => {
    const { container } = wrap(
      <WordCountBar
        sectionWords={500}
        totalWords={1500}
        saving={false}
        savedAt={null}
        templateKey="jbjs"
        activeSectionName="Methodology"
      />,
    )
    expect(container.textContent).toContain('/ 1200')
    expect(container.textContent).toContain('/ 4000')
  })
})
