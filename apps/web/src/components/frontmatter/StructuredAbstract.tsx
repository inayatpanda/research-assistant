import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { frontmatterApi, type StructuredAbstractValue } from '@/lib/api'

const SECTION_LABELS: Array<{ key: keyof StructuredAbstractValue; label: string }> = [
  { key: 'background', label: 'Background' },
  { key: 'methods', label: 'Methods' },
  { key: 'results', label: 'Results' },
  { key: 'conclusions', label: 'Conclusions' },
]

export function StructuredAbstract({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const fmQ = useQuery({
    queryKey: ['frontmatter', projectId, 'frontmatter'],
    queryFn: () => frontmatterApi.frontmatter.get(projectId),
  })
  const patchMut = useMutation({
    mutationFn: (patch: {
      structured_abstract_enabled?: boolean
      structured_abstract?: StructuredAbstractValue
    }) => frontmatterApi.frontmatter.patch(projectId, patch),
    onSuccess: (out) =>
      qc.setQueryData(['frontmatter', projectId, 'frontmatter'], out),
  })

  const [draft, setDraft] = useState<StructuredAbstractValue>({
    background: '',
    methods: '',
    results: '',
    conclusions: '',
  })
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    if (!fmQ.data) return
    setEnabled(fmQ.data.structured_abstract_enabled)
    setDraft(fmQ.data.structured_abstract)
  }, [fmQ.data])

  if (fmQ.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading…</div>
  }

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => {
            setEnabled(e.target.checked)
            patchMut.mutate({ structured_abstract_enabled: e.target.checked })
          }}
          data-testid="sa-enable"
        />
        <span>
          Use a structured abstract (replaces freeform Abstract on export)
        </span>
      </label>
      {enabled ? (
        <div className="space-y-3" data-testid="sa-fields">
          {SECTION_LABELS.map(({ key, label }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                {label}
              </label>
              <textarea
                rows={3}
                value={draft[key]}
                onChange={(e) =>
                  setDraft({ ...draft, [key]: e.target.value })
                }
                onBlur={() => patchMut.mutate({ structured_abstract: draft })}
                data-testid={`sa-${key}`}
                className="w-full rounded border border-border px-2 py-1.5 text-sm"
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">
          The freeform Abstract section will be used. Toggle the box above to
          replace it with Background / Methods / Results / Conclusions sub-fields.
        </div>
      )}
    </div>
  )
}
