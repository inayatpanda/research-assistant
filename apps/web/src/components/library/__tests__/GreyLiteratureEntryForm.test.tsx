import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GreyLiteratureEntryForm } from '../GreyLiteratureEntryForm'

describe('GreyLiteratureEntryForm', () => {
  afterEach(cleanup)

  it('submits the form payload with the chosen reference_type + URL', () => {
    const onSubmit = vi.fn()
    render(<GreyLiteratureEntryForm onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText(/^title$/i), {
      target: { value: 'WHO TB report' },
    })
    fireEvent.change(screen.getByLabelText(/year/i), {
      target: { value: '2024' },
    })
    fireEvent.change(screen.getByLabelText(/url/i), {
      target: { value: 'https://who.int/tb' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add reference/i }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
    const value = onSubmit.mock.calls[0][0]
    expect(value).toMatchObject({
      title: 'WHO TB report',
      year: 2024,
      url: 'https://who.int/tb',
      reference_type: 'web_resource',
    })
  })

  it('disables the submit button when title is empty', () => {
    const onSubmit = vi.fn()
    render(<GreyLiteratureEntryForm onSubmit={onSubmit} />)
    const btn = screen.getByRole('button', { name: /add reference/i }) as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })
})
