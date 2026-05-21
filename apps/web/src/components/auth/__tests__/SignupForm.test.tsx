import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockMutateAsync = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useSignup: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}))

import { SignupForm } from '@/components/auth/SignupForm'

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  mockMutateAsync.mockReset()
})

describe('SignupForm', () => {
  it('rejects weak passwords client-side', async () => {
    renderWithProviders(<SignupForm />)
    fireEvent.click(screen.getByTestId('signup-tos'))
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: 'Alice' },
    })
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'a@b.com' },
    })
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: 'short' },
    })
    fireEvent.submit(screen.getByTestId('signup-form'))
    await waitFor(() => {
      expect(screen.getByTestId('signup-error').textContent).toMatch(/10 characters/i)
    })
    expect(mockMutateAsync).not.toHaveBeenCalled()
  })

  it('requires TOS acknowledgement before submitting', async () => {
    renderWithProviders(<SignupForm />)
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: 'Alice' },
    })
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'a@b.com' },
    })
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: 'longpassword1' },
    })
    // Skip clicking the TOS checkbox.
    fireEvent.submit(screen.getByTestId('signup-form'))
    await waitFor(() => {
      expect(screen.queryByTestId('signup-error')).not.toBeNull()
    })
    expect(mockMutateAsync).not.toHaveBeenCalled()
  })
})
