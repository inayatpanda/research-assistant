import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useCreateInvitation,
  useCurrentUser,
  useInvitations,
  useMembers,
  useRemoveMember,
  useRevokeInvitation,
  useUpdateMemberRole,
} from '@/hooks/useAuth'

type Role = 'owner' | 'editor' | 'viewer'
const ROLES: Role[] = ['owner', 'editor', 'viewer']

export function MembersPanel({ projectId }: { projectId: string }) {
  const { data: me } = useCurrentUser()
  const { data: members = [] } = useMembers(projectId)
  const { data: invitations = [] } = useInvitations(projectId)
  const updateRole = useUpdateMemberRole(projectId)
  const removeMember = useRemoveMember(projectId)
  const createInvitation = useCreateInvitation(projectId)
  const revokeInvitation = useRevokeInvitation(projectId)

  const myRow = members.find((m) => m.user_id === me?.id) ?? null
  const isOwner = myRow?.role === 'owner'

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<Role>('viewer')
  const [lastInviteUrl, setLastInviteUrl] = useState<string | null>(null)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  async function onCreateInvite(e: React.FormEvent) {
    e.preventDefault()
    setInviteError(null)
    try {
      const res = await createInvitation.mutateAsync({
        email: inviteEmail,
        role: inviteRole,
      })
      setLastInviteUrl(res.invite_url)
      setInviteEmail('')
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : 'Failed to invite.')
    }
  }

  return (
    <div className="space-y-6" data-testid="members-panel">
      <section className="rounded-md border bg-card p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Members</h2>
          {isOwner ? (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button size="sm" data-testid="invite-button">
                  Invite member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite a collaborator</DialogTitle>
                </DialogHeader>
                <form onSubmit={onCreateInvite} className="space-y-3">
                  <div className="grid gap-2">
                    <Label htmlFor="invite-email">Email</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="invite-role">Role</Label>
                    <Select
                      value={inviteRole}
                      onValueChange={(v) => setInviteRole(v as Role)}
                    >
                      <SelectTrigger id="invite-role">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((r) => (
                          <SelectItem key={r} value={r}>
                            {r}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {inviteError ? (
                    <p className="text-sm text-destructive" role="alert">
                      {inviteError}
                    </p>
                  ) : null}
                  {lastInviteUrl ? (
                    <div
                      className="rounded border bg-muted/50 p-2 text-xs"
                      data-testid="invite-url"
                    >
                      <p className="font-medium">Invitation URL (copy-paste):</p>
                      <p className="break-all font-mono">{lastInviteUrl}</p>
                    </div>
                  ) : null}
                  <DialogFooter>
                    <DialogClose asChild>
                      <Button type="button" variant="outline">
                        Close
                      </Button>
                    </DialogClose>
                    <Button type="submit" disabled={createInvitation.isPending}>
                      Send
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          ) : null}
        </div>
        <table className="mt-3 w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="py-1">User</th>
              <th className="py-1">Role</th>
              {isOwner ? <th className="py-1" /> : null}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.user_id} className="border-t">
                <td className="py-2">
                  <div className="font-medium">{m.display_name}</div>
                  <div className="text-xs text-muted-foreground">{m.email}</div>
                </td>
                <td className="py-2">
                  {isOwner ? (
                    <Select
                      value={m.role}
                      onValueChange={(v) =>
                        updateRole.mutate({ userId: m.user_id, role: v as Role })
                      }
                    >
                      <SelectTrigger className="w-32" aria-label={`Role for ${m.email}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((r) => (
                          <SelectItem key={r} value={r}>
                            {r}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <span>{m.role}</span>
                  )}
                </td>
                {isOwner ? (
                  <td className="py-2 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeMember.mutate(m.user_id)}
                    >
                      Remove
                    </Button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {isOwner ? (
        <section className="rounded-md border bg-card p-4">
          <h2 className="text-lg font-semibold">Pending invitations</h2>
          {invitations.filter((i) => !i.accepted_at).length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              No pending invitations.
            </p>
          ) : (
            <ul className="mt-2 divide-y">
              {invitations
                .filter((i) => !i.accepted_at)
                .map((i) => (
                  <li
                    key={i.id}
                    className="flex items-center justify-between gap-3 py-2 text-sm"
                  >
                    <div>
                      <span className="font-medium">{i.email}</span>
                      <span className="ml-2 text-muted-foreground">
                        ({i.role})
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => revokeInvitation.mutate(i.id)}
                    >
                      Revoke
                    </Button>
                  </li>
                ))}
            </ul>
          )}
        </section>
      ) : null}
    </div>
  )
}

export default MembersPanel
