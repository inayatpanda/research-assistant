import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CitationStylePicker } from '../CitationStylePicker'

describe('CitationStylePicker', () => {
  afterEach(cleanup)

  it('renders the configured style as the trigger label', () => {
    render(<CitationStylePicker value="lancet" onChange={vi.fn()} />)
    const trigger = screen.getByRole('combobox', { name: /citation style/i })
    expect(trigger).toBeTruthy()
    expect(trigger.textContent).toMatch(/Lancet/i)
  })

  it('passes the chosen value through onChange when value prop changes', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <CitationStylePicker value="vancouver" onChange={onChange} />,
    )
    rerender(<CitationStylePicker value="nejm" onChange={onChange} />)
    const trigger = screen.getByRole('combobox', { name: /citation style/i })
    expect(trigger.textContent).toMatch(/NEJM/i)
  })
})
