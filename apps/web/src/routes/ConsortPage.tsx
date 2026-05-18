import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { CONSORTFlowChart } from '@/components/consort/CONSORTFlowChart'
import { useConsort, usePushConsort, useUpdateConsort } from '@/hooks/useConsort'
import { projectsApi, type ConsortDataPayload } from '@/lib/api'
import { useProjectId } from '@/lib/projectContext'

const NUM_FIELDS: { key: keyof ConsortDataPayload; label: string }[] = [
  { key: 'enrollment_assessed', label: 'Assessed for eligibility' },
  { key: 'enrollment_excluded', label: 'Excluded' },
  { key: 'randomised', label: 'Randomised' },
  { key: 'allocated_intervention', label: 'Allocated (intervention)' },
  { key: 'allocated_control', label: 'Allocated (control)' },
  { key: 'intervention_received', label: 'Received (intervention)' },
  { key: 'control_received', label: 'Received (control)' },
  { key: 'intervention_lost_followup', label: 'Lost to follow-up (intervention)' },
  { key: 'control_lost_followup', label: 'Lost to follow-up (control)' },
  { key: 'intervention_discontinued', label: 'Discontinued (intervention)' },
  { key: 'control_discontinued', label: 'Discontinued (control)' },
  { key: 'intervention_analysed', label: 'Analysed (intervention)' },
  { key: 'control_analysed', label: 'Analysed (control)' },
]

export default function ConsortPage() {
  const projectId = useProjectId()
  return <ConsortInner projectId={projectId} />
}

function ConsortInner({ projectId }: { projectId: string }) {
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })
  const { data, isLoading } = useConsort(projectId)
  const update = useUpdateConsort(projectId)
  const push = usePushConsort(projectId)

  const [form, setForm] = useState<ConsortDataPayload>({})
  const [reasons, setReasons] = useState<{ label: string; count: number }[]>([])

  useEffect(() => {
    if (!data) return
    const payload: ConsortDataPayload = { ...data.data }
    setForm(payload)
    if (data.data.enrollment_excluded_reasons) {
      setReasons(
        Object.entries(data.data.enrollment_excluded_reasons).map(([label, count]) => ({
          label,
          count,
        })),
      )
    }
  }, [data])

  const isRCT = project?.study_type === 'Randomised Controlled Trial'

  const submit = async () => {
    const reasonsDict =
      reasons.length > 0
        ? Object.fromEntries(reasons.filter((r) => r.label).map((r) => [r.label, r.count]))
        : null
    try {
      await update.mutateAsync({ ...form, enrollment_excluded_reasons: reasonsDict })
      toast.success('Saved')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    }
  }

  const onPush = async () => {
    try {
      await push.mutateAsync()
      toast.success('Pushed to Methodology')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Push failed')
    }
  }

  const warnings = data?.warnings ?? []
  const svgBase64 = data?.svg_base64 ?? ''

  const fields = useMemo(() => NUM_FIELDS, [])

  return (
    <div className="px-6 py-6 max-w-[1200px] mx-auto">
      <header className="flex items-center justify-between mb-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            CONSORT 2010
          </div>
          <h1 className="text-[18px] font-semibold tracking-tight">
            {project?.title ?? 'Loading…'}
          </h1>
        </div>
        <button
          onClick={onPush}
          disabled={!isRCT}
          title={isRCT ? 'Push to Methodology' : 'Available for Randomised Controlled Trial projects'}
          className="px-3 py-1.5 rounded bg-zinc-900 text-white text-sm disabled:opacity-40"
        >
          Push to Methodology
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section aria-label="CONSORT counters">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                submit()
              }}
              className="space-y-3"
            >
              {fields.map((f) => (
                <label key={f.key} className="flex items-center justify-between gap-2">
                  <span className="text-sm">{f.label}</span>
                  <input
                    type="number"
                    min={0}
                    value={(form[f.key] as number | null | undefined) ?? ''}
                    onChange={(e) => {
                      const v = e.target.value === '' ? null : parseInt(e.target.value, 10)
                      setForm((prev) => ({ ...prev, [f.key]: v as never }))
                    }}
                    className="w-24 rounded border border-border px-2 py-1 text-sm"
                  />
                </label>
              ))}

              <div className="border-t pt-3">
                <div className="text-sm font-medium mb-2">Reasons for exclusion</div>
                {reasons.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 mb-2">
                    <input
                      placeholder="Reason"
                      value={r.label}
                      onChange={(e) => {
                        const next = [...reasons]
                        next[i] = { ...next[i], label: e.target.value }
                        setReasons(next)
                      }}
                      className="flex-1 rounded border border-border px-2 py-1 text-sm"
                    />
                    <input
                      type="number"
                      min={0}
                      value={r.count}
                      onChange={(e) => {
                        const next = [...reasons]
                        next[i] = { ...next[i], count: parseInt(e.target.value, 10) || 0 }
                        setReasons(next)
                      }}
                      className="w-24 rounded border border-border px-2 py-1 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setReasons(reasons.filter((_, idx) => idx !== i))}
                      className="px-2 text-xs"
                      aria-label="Remove reason"
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setReasons([...reasons, { label: '', count: 0 }])}
                  className="text-xs underline"
                >
                  + Add reason
                </button>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded bg-zinc-900 text-white text-sm"
                >
                  Save
                </button>
              </div>

              {warnings.length > 0 && (
                <div
                  role="alert"
                  className="mt-3 p-3 bg-amber-50 border border-amber-300 rounded text-xs text-amber-900"
                >
                  <strong>Warnings</strong>
                  <ul className="list-disc pl-4 mt-1 space-y-0.5">
                    {warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </form>
          )}
        </section>

        <section aria-label="CONSORT diagram">
          <CONSORTFlowChart svgBase64={svgBase64} />
        </section>
      </div>
    </div>
  )
}
