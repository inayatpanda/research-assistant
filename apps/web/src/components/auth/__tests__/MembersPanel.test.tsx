import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockCreate = vi.fn()
const mockUpdate = vi.fn()
const mockRemove = vi.fn()
const mockRevokeInv = vi.fn()

let mockRole: 'owner' | 'editor' | 'viewer' = 'owner'

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { id: 'me', email: 'me@x.com', display_name: 'Me', is_admin: false, created_at: 'now' } }),
  useMembers: () => ({
    data: [
      {
        user_id: 'me',
        email: 'me@x.com',
        display_name: 'Me',
        role: mockRole,
        created_at: '2026-05-21T00:00:00Z',
      },
      {
        user_id: 'guest',
        email: 'guest@x.com',
        display_name: 'Guest',
        role: 'viewer',
        created_at: '2026-05-21T00:00:00Z',
      },
    ],
  }),
  useInvitations: () => ({ data: [] }),
  useUpdateMemberRole: () => ({ mutate: mockUpdate }),
  useRemoveMember: () => ({ mutate: mockRemove }),
  useCreateInvitation: () => ({ mutateAsync: mockCreate, isPending: false }),
  useRevokeInvitation: () => ({ mutate: mockRevokeInv }),
}))

import { MembersPanel } from '@/components/auth/MembersPanel'

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
})

describe('MembersPanel', () => {
  it('renders the members list', () => {
    mockRole = 'owner'
    renderWithProviders(<MembersPanel projectId="p1" />)
    expect(screen.getByText('me@x.com')).toBeTruthy()
    expect(screen.getByText('guest@x.com')).toBeTruthy()
  })

  it('hides the invite button when not an owner', () => {
    mockRole = 'viewer'
    renderWithProviders(<MembersPanel projectId="p1" />)
    expect(screen.queryByTestId('invite-button')).toBeNull()
  })
})
