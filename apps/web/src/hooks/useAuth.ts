import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  authApi,
  membersApi,
  type Invitation,
  type InvitationCreateResponse,
  type InvitationLanding,
  type LegacyDataStatus,
  type Member,
  type SessionRow,
  type User,
} from '@/lib/api'

/**
 * Returns the current user, or ``null`` if unauthenticated. Never throws
 * for a 401 — that's the "logged out" steady state.
 */
export function useCurrentUser() {
  return useQuery<User | null>({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.me(),
    staleTime: 60_000,
    retry: false,
  })
}

export function useSignup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; password: string; display_name: string }) =>
      authApi.signup(body.email, body.password, body.display_name),
    onSuccess: (user) => {
      qc.setQueryData(['auth', 'me'], user)
    },
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      authApi.login(body.email, body.password),
    onSuccess: (user) => {
      qc.setQueryData(['auth', 'me'], user)
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      qc.setQueryData(['auth', 'me'], null)
      qc.clear()
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { old_password: string; new_password: string }) =>
      authApi.changePassword(body.old_password, body.new_password),
  })
}

export function useSessions() {
  return useQuery<SessionRow[]>({
    queryKey: ['auth', 'sessions'],
    queryFn: () => authApi.listSessions(),
  })
}

export function useRevokeSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => authApi.revokeSession(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth', 'sessions'] })
    },
  })
}

export function useInvitationLanding(token: string | null) {
  return useQuery<InvitationLanding>({
    queryKey: ['auth', 'invitation', token],
    queryFn: () => authApi.invitationLanding(token as string),
    enabled: !!token,
    retry: false,
  })
}

export function useAcceptInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (token: string) => authApi.acceptInvitation(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useLegacyDataStatus() {
  return useQuery<LegacyDataStatus>({
    queryKey: ['auth', 'legacy-status'],
    queryFn: () => authApi.legacyDataStatus(),
    retry: false,
  })
}

export function useClaimLegacyData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => authApi.claimLegacyData(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth', 'legacy-status'] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

// ── Members ────────────────────────────────────────────────────────────

export function useMembers(projectId: string | null) {
  return useQuery<Member[]>({
    queryKey: ['members', projectId],
    queryFn: () => membersApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpdateMemberRole(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { userId: string; role: 'owner' | 'editor' | 'viewer' }) =>
      membersApi.updateRole(projectId, body.userId, body.role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members', projectId] })
    },
  })
}

export function useRemoveMember(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => membersApi.remove(projectId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members', projectId] })
    },
  })
}

export function useInvitations(projectId: string | null) {
  return useQuery<Invitation[]>({
    queryKey: ['invitations', projectId],
    queryFn: () => membersApi.listInvitations(projectId as string),
    enabled: !!projectId,
  })
}

export function useCreateInvitation(projectId: string) {
  const qc = useQueryClient()
  return useMutation<InvitationCreateResponse, Error, { email: string; role: 'owner' | 'editor' | 'viewer' }>({
    mutationFn: (body) => membersApi.createInvitation(projectId, body.email, body.role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invitations', projectId] })
    },
  })
}

export function useRevokeInvitation(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => membersApi.revokeInvitation(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invitations', projectId] })
    },
  })
}
