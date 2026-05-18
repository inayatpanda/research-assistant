import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  CREDIT_ROLES,
  frontmatterApi,
  type CreditRole,
} from '@/lib/api'

export function ContributionsMatrix({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const authorsQ = useQuery({
    queryKey: ['frontmatter', projectId, 'authors'],
    queryFn: () => frontmatterApi.authors.list(projectId),
  })

  const authors = authorsQ.data ?? []

  const contributionQueries = useQueries({
    queries: authors.map((a) => ({
      queryKey: ['frontmatter', projectId, 'contributions', a.id],
      queryFn: () => frontmatterApi.contributions.list(a.id),
      enabled: authors.length > 0,
    })),
  })

  const toggleMut = useMutation({
    mutationFn: async (args: {
      authorId: string
      role: CreditRole
      currentlyOn: boolean
    }) => {
      if (args.currentlyOn) {
        await frontmatterApi.contributions.clear(args.authorId, args.role)
      } else {
        await frontmatterApi.contributions.set(args.authorId, args.role)
      }
    },
    onSuccess: (_, vars) =>
      qc.invalidateQueries({
        queryKey: ['frontmatter', projectId, 'contributions', vars.authorId],
      }),
  })

  if (authorsQ.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading…</div>
  }
  if (authors.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        Add at least one author to assign CRediT contributions.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table
        className="min-w-full border-collapse text-xs"
        data-testid="contributions-matrix"
      >
        <thead>
          <tr>
            <th className="sticky left-0 bg-background border border-border px-2 py-2 text-left font-medium">
              Author
            </th>
            {CREDIT_ROLES.map((role) => (
              <th
                key={role}
                className="border border-border px-2 py-2 text-left font-medium whitespace-nowrap"
              >
                {role}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {authors.map((author, idx) => {
            const contributions = contributionQueries[idx]?.data ?? []
            const active = new Set(contributions.map((c) => c.role))
            return (
              <tr key={author.id}>
                <td className="sticky left-0 bg-background border border-border px-2 py-1.5 font-medium">
                  {author.full_name}
                </td>
                {CREDIT_ROLES.map((role) => {
                  const on = active.has(role)
                  return (
                    <td
                      key={role}
                      className="border border-border px-2 py-1.5 text-center"
                    >
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() =>
                          toggleMut.mutate({
                            authorId: author.id,
                            role,
                            currentlyOn: on,
                          })
                        }
                        data-testid={`contribution-${author.id}-${role}`}
                        aria-label={`${role} for ${author.full_name}`}
                      />
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
