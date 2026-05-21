import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockChange = vi.fn()
const mockRevoke = vi.fn()
const mockLogout = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({
    data: { id: 'u1', email: 'a@b.com', display_name: 'Alice', is_admin: false, created_at: '2026-05-21T00:00:00Z' },
  }),
  useSessions: () => ({
    data: [
      {
        id: 'sess1',
        user_agent: 'Test/1.0',
        created_at: '2026-05-21T00:00:00Z',
        last_seen_at: '2026-05-21T00:00:00Z',
        expires_at: '2026-06-21T00:00:00Z',
      },
    ],
  }),
  useChangePassword: () => ({ mutateAsync: mockChange, isPending: false }),
  useRevokeSession: () => ({ mutate: mockRevoke }),
  useLogout: () => ({ mutateAsync: mockLogout }),
}))

import { AccountPanel } from '@/components/auth/AccountPanel'

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
  mockChange.mockReset()
  mockRevoke.mockReset()
  mockLogout.mockReset()
})

describe('AccountPanel', () => {
  it('renders the user email + display name', () => {
    renderWithProviders(<AccountPanel />)
    expect(screen.getByText(/a@b.com/)).toBeTruthy()
    expect(screen.getByText(/Alice/)).toBeTruthy()
  })

  it('lists active sessions and triggers revoke', () => {
    renderWithProviders(<AccountPanel />)
    const revoke = screen.getAllByRole('button', { name: /revoke/i })[0]
    fireEvent.click(revoke)
    expect(mockRevoke).toHaveBeenCalledWith('sess1')
  })

  it('validates the new password locally', async () => {
    renderWithProviders(<AccountPanel />)
    fireEvent.change(screen.getByLabelText(/current password/i), {
      target: { value: 'old' },
    })
    fireEvent.change(screen.getByLabelText(/new password/i), {
      target: { value: 'tooshort' },
    })
    fireEvent.click(screen.getByRole('button', { name: /update password/i }))
    await waitFor(() => {
      expect(screen.getByText(/at least 10 characters/i)).toBeTruthy()
    })
    expect(mockChange).not.toHaveBeenCalled()
  })
})
