import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockMutateAsync = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useLogin: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}))

import { LoginForm } from '@/components/auth/LoginForm'

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
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

describe('LoginForm', () => {
  it('renders email + password inputs', () => {
    renderWithProviders(<LoginForm />)
    expect(screen.getByLabelText(/email/i)).toBeTruthy()
    expect(screen.getByLabelText(/password/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy()
  })

  it('submits credentials when form is filled', async () => {
    mockMutateAsync.mockResolvedValue({
      id: 'u1',
      email: 'a@b.com',
      display_name: 'A',
    })
    renderWithProviders(<LoginForm />)
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'a@b.com' },
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'longpassword1' },
    })
    fireEvent.submit(screen.getByTestId('login-form'))
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        email: 'a@b.com',
        password: 'longpassword1',
      })
    })
  })
})
