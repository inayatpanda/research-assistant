import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import {
  frontmatterApi,
  type Funder,
  type ProjectFrontmatterUpdate,
} from '@/lib/api'

export function EthicsFundingForm({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const fmQ = useQuery({
    queryKey: ['frontmatter', projectId, 'frontmatter'],
    queryFn: () => frontmatterApi.frontmatter.get(projectId),
  })
  const patchMut = useMutation({
    mutationFn: (patch: ProjectFrontmatterUpdate) =>
      frontmatterApi.frontmatter.patch(projectId, patch),
    onSuccess: (out) =>
      qc.setQueryData(['frontmatter', projectId, 'frontmatter'], out),
  })

  const [funding, setFunding] = useState('')
  const [irb, setIrb] = useState('')
  const [approval, setApproval] = useState('')
  const [consent, setConsent] = useState('')
  const [coi, setCoi] = useState('')
  const [funders, setFunders] = useState<Funder[]>([])

  // Sync local state once the server payload arrives.
  useEffect(() => {
    if (!fmQ.data) return
    setFunding(fmQ.data.funding_statement ?? '')
    setIrb(fmQ.data.ethics_irb ?? '')
    setApproval(fmQ.data.ethics_approval_number ?? '')
    setConsent(fmQ.data.ethics_consent ?? '')
    setCoi(fmQ.data.conflicts_statement ?? '')
    setFunders(fmQ.data.funders ?? [])
  }, [fmQ.data])

  if (fmQ.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading…</div>
  }

  return (
    <div className="space-y-4">
      <Field
        label={
          <LearnTooltip
            concept="conflict-of-interest"
            iconOnly
            description="What to disclose, ICMJE form fields, when 'none' is acceptable."
          >
            Conflicts of interest
          </LearnTooltip>
        }
      >
        <textarea
          value={coi}
          onChange={(e) => setCoi(e.target.value)}
          onBlur={() => patchMut.mutate({ conflicts_statement: coi || null })}
          rows={2}
          data-testid="fm-conflicts"
          className="w-full rounded border border-border px-2 py-1.5 text-sm"
        />
      </Field>

      <Field label="Funding statement">
        <textarea
          value={funding}
          onChange={(e) => setFunding(e.target.value)}
          onBlur={() =>
            patchMut.mutate({ funding_statement: funding || null })
          }
          rows={2}
          data-testid="fm-funding-statement"
          className="w-full rounded border border-border px-2 py-1.5 text-sm"
        />
      </Field>

      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1">
          Funders
        </div>
        <div className="space-y-2" data-testid="fm-funders-list">
          {funders.map((f, idx) => (
            <div key={idx} className="flex gap-2">
              <input
                value={f.name}
                onChange={(e) => {
                  const next = funders.slice()
                  next[idx] = { ...next[idx], name: e.target.value }
                  setFunders(next)
                }}
                onBlur={() => patchMut.mutate({ funders })}
                placeholder="Funder name"
                className="flex-1 rounded border border-border px-2 py-1.5 text-sm"
              />
              <input
                value={f.grant_id ?? ''}
                onChange={(e) => {
                  const next = funders.slice()
                  next[idx] = { ...next[idx], grant_id: e.target.value }
                  setFunders(next)
                }}
                onBlur={() => patchMut.mutate({ funders })}
                placeholder="Grant ID"
                className="w-44 rounded border border-border px-2 py-1.5 text-sm font-mono"
              />
              <button
                onClick={() => {
                  const next = funders.filter((_, i) => i !== idx)
                  setFunders(next)
                  patchMut.mutate({ funders: next })
                }}
                className="text-xs text-rose-600"
                aria-label="Remove funder"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={() => setFunders([...funders, { name: '', grant_id: '' }])}
            data-testid="fm-funders-add"
            className="text-xs text-accent hover:underline"
          >
            + Add funder
          </button>
        </div>
      </div>

      <Field label="IRB / ethics committee">
        <input
          value={irb}
          onChange={(e) => setIrb(e.target.value)}
          onBlur={() => patchMut.mutate({ ethics_irb: irb || null })}
          data-testid="fm-ethics-irb"
          className="w-full rounded border border-border px-2 py-1.5 text-sm"
        />
      </Field>
      <Field label="Approval number">
        <input
          value={approval}
          onChange={(e) => setApproval(e.target.value)}
          onBlur={() =>
            patchMut.mutate({ ethics_approval_number: approval || null })
          }
          data-testid="fm-ethics-approval"
          className="w-full rounded border border-border px-2 py-1.5 text-sm"
        />
      </Field>
      <Field label="Consent statement">
        <textarea
          value={consent}
          onChange={(e) => setConsent(e.target.value)}
          onBlur={() =>
            patchMut.mutate({ ethics_consent: consent || null })
          }
          rows={2}
          data-testid="fm-ethics-consent"
          className="w-full rounded border border-border px-2 py-1.5 text-sm"
        />
      </Field>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">
        {label}
      </label>
      {children}
    </div>
  )
}
