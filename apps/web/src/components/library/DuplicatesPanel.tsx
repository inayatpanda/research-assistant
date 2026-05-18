import { useQuery } from '@tanstack/react-query'
import { Merge } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useDuplicates, useMergeDuplicates } from '@/hooks/useIngest'
import { articlesApi, type Article, type DuplicateGroup } from '@/lib/api'

function ReasonBadge({ reason }: { reason: DuplicateGroup['reason'] }) {
  const label =
    reason === 'doi_exact'
      ? 'DOI match'
      : reason === 'pmid_exact'
        ? 'PMID match'
        : 'Title similar'
  return (
    <Badge variant="secondary" className="uppercase text-[10px]">
      {label}
    </Badge>
  )
}

function GroupCard({
  projectId,
  group,
  articlesById,
}: {
  projectId: string
  group: DuplicateGroup
  articlesById: Map<string, Article>
}) {
  const [keepId, setKeepId] = useState(group.keep_candidate_id)
  const merge = useMergeDuplicates(projectId)

  const dropIds = group.candidate_ids.filter((id) => id !== keepId)
  const candidates = group.candidate_ids
    .map((id) => articlesById.get(id))
    .filter((a): a is Article => Boolean(a))

  async function onMerge() {
    if (dropIds.length === 0) return
    try {
      await merge.mutateAsync({ keepId, dropIds })
      toast.success(`Merged ${dropIds.length + 1} articles into 1`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Merge failed')
    }
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ReasonBadge reason={group.reason} />
          <span className="text-[11px] text-muted-foreground">
            score {group.score.toFixed(2)} · {group.candidate_ids.length} rows
          </span>
        </div>
        <Button
          size="sm"
          onClick={() => void onMerge()}
          disabled={merge.isPending || dropIds.length === 0}
        >
          <Merge className="h-4 w-4 mr-1" />
          {merge.isPending ? 'Merging…' : `Merge ${group.candidate_ids.length} → 1`}
        </Button>
      </div>
      <ul className="space-y-2">
        {candidates.map((a) => {
          const isKeep = a.id === keepId
          return (
            <li
              key={a.id}
              className={
                'rounded-md border p-3 text-[13px] ' +
                (isKeep
                  ? 'border-emerald-300 bg-emerald-50/60'
                  : 'border-border bg-white')
              }
            >
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name={`keep-${group.keep_candidate_id}`}
                  checked={isKeep}
                  onChange={() => setKeepId(a.id)}
                  aria-label={`Keep ${a.title}`}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="uppercase text-[10px]">
                      {a.source}
                    </Badge>
                    {isKeep && (
                      <Badge className="bg-emerald-600 text-white text-[10px]">
                        Keep
                      </Badge>
                    )}
                    <span className="text-[11px] text-muted-foreground">
                      {a.year ?? '—'}
                    </span>
                    {a.doi && (
                      <span className="text-[11px] font-mono text-muted-foreground truncate">
                        DOI {a.doi}
                      </span>
                    )}
                    {a.pmid && (
                      <span className="text-[11px] font-mono text-muted-foreground">
                        PMID {a.pmid}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 font-medium">{a.title}</div>
                  <div className="text-[12px] text-muted-foreground line-clamp-1">
                    {a.authors.join(', ') || '—'}
                    {a.journal ? ` · ${a.journal}` : ''}
                  </div>
                </div>
              </label>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function DuplicatesPanel({ projectId }: { projectId: string }) {
  const dups = useDuplicates(projectId)
  const arts = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
    enabled: !!projectId,
  })

  if (!dups.data || dups.data.length === 0) return null
  const articlesById = new Map(
    (arts.data ?? []).map((a) => [a.id, a] as const),
  )

  return (
    <section
      aria-label="Possible duplicates"
      className="space-y-3"
    >
      <div className="flex items-center gap-2">
        <h2 className="text-[14px] font-semibold tracking-tight">
          Possible duplicates
        </h2>
        <Badge variant="secondary" className="text-[10px]">
          {dups.data.length} group{dups.data.length === 1 ? '' : 's'}
        </Badge>
      </div>
      <div className="space-y-3">
        {dups.data.map((g) => (
          <GroupCard
            key={g.keep_candidate_id + g.candidate_ids.join(',')}
            projectId={projectId}
            group={g}
            articlesById={articlesById}
          />
        ))}
      </div>
    </section>
  )
}
