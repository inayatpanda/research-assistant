/**
 * Phase D3 — ArchitectureDiagram test.
 *
 * The diagram is pure SVG so we can assert on its accessible labels
 * and the caption that explains the picture in words.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import { ArchitectureDiagram } from '@/components/ArchitectureDiagram'

afterEach(() => cleanup())

describe('ArchitectureDiagram', () => {
  it('renders the SVG with an accessible title and a caption', () => {
    render(<ArchitectureDiagram />)
    expect(screen.getByTestId('architecture-diagram')).toBeInTheDocument()
    expect(screen.getByText(/local-first network architecture/i)).toBeInTheDocument()
    expect(screen.getByTestId('architecture-caption')).toHaveTextContent(
      /your data stays on your laptop/i,
    )
  })

  it('omits the caption when showCaption=false', () => {
    render(<ArchitectureDiagram showCaption={false} />)
    expect(screen.queryByTestId('architecture-caption')).toBeNull()
  })
})
