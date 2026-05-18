import { useState } from 'react'

import { Input } from '@/components/ui/input'
import { useUpsertMetaInput } from '@/hooks/useMeta'
import type {
  EffectMetric,
  MetaAnalysisRead,
  MetaInputCreate,
  MetaInputRead,
} from '@/lib/api'

const CONTINUOUS = ['mean_a', 'sd_a', 'n_a', 'mean_b', 'sd_b', 'n_b'] as const
const BINARY = ['events_a', 'n_a_total', 'events_b', 'n_b_total'] as const
const HR_LOG = ['log_hr', 'se_log_hr'] as const
const HR_CI = ['hr', 'hr_ci_low', 'hr_ci_high'] as const
const CORR = ['r', 'n_r'] as const

function columnsForMetric(metric: EffectMetric, hrMode: 'log' | 'ci'): readonly string[] {
  switch (metric) {
    case 'md':
    case 'smd':
      return CONTINUOUS
    case 'or':
    case 'rr':
      return BINARY
    case 'hr':
      return hrMode === 'log' ? HR_LOG : HR_CI
    case 'r':
      return CORR
  }
}

export function PerStudyInputs({
  projectId,
  meta,
}: {
  projectId: string
  meta: MetaAnalysisRead
}) {
  const [hrMode, setHrMode] = useState<'log' | 'ci'>('log')
  const { mutate: upsert } = useUpsertMetaInput(projectId, meta.id)
  const columns = columnsForMetric(meta.effect_metric, hrMode)

  const handleBlur = (inp: MetaInputRead, column: string, raw: string) => {
    const value = raw === '' ? null : Number(raw)
    if (raw !== '' && Number.isNaN(value)) return
    const body: MetaInputCreate = {
      article_id: inp.article_id,
      study_label: inp.study_label,
    }
    // Carry over all existing fields except the one being edited
    ;([
      'mean_a', 'sd_a', 'n_a', 'mean_b', 'sd_b', 'n_b',
      'events_a', 'n_a_total', 'events_b', 'n_b_total',
      'log_hr', 'se_log_hr', 'hr', 'hr_ci_low', 'hr_ci_high',
      'r', 'n_r',
    ] as const).forEach((k) => {
      ;(body as Record<string, unknown>)[k] = (inp as Record<string, unknown>)[k]
    })
    ;(body as Record<string, unknown>)[column] = value
    upsert(body)
  }

  return (
    <div className="space-y-3">
      {meta.effect_metric === 'hr' && (
        <div className="flex items-center gap-3 text-[12px]">
          <span className="text-muted-foreground">HR input mode:</span>
          <button
            className={`rounded-md border px-2 py-0.5 ${hrMode === 'log' ? 'bg-foreground text-background' : 'bg-white'}`}
            onClick={() => setHrMode('log')}
          >
            log_hr / se
          </button>
          <button
            className={`rounded-md border px-2 py-0.5 ${hrMode === 'ci' ? 'bg-foreground text-background' : 'bg-white'}`}
            onClick={() => setHrMode('ci')}
          >
            HR / 95% CI
          </button>
        </div>
      )}
      <div className="overflow-x-auto rounded-md border border-border bg-white">
        <table className="w-full text-[12px]">
          <thead className="bg-muted/30">
            <tr>
              <th className="px-2 py-1.5 text-left">Study</th>
              {columns.map((c) => (
                <th key={c} className="px-2 py-1.5 text-left">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {meta.inputs.map((inp) => (
              <tr key={inp.id} className="border-t border-border">
                <td className="px-2 py-1.5">
                  <div className="font-medium truncate max-w-[200px]" title={inp.study_label || inp.article_id}>
                    {inp.study_label || inp.article_id.slice(0, 8)}
                  </div>
                </td>
                {columns.map((c) => (
                  <td key={c} className="px-2 py-1.5">
                    <Input
                      type="number"
                      defaultValue={
                        (inp as Record<string, unknown>)[c] != null
                          ? String((inp as Record<string, unknown>)[c])
                          : ''
                      }
                      className="h-7 w-24"
                      step="any"
                      onBlur={(e) => handleBlur(inp, c, e.currentTarget.value)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-[11px] text-muted-foreground">
        Values save automatically on blur. After every edit you'll need to re-run.
      </div>
    </div>
  )
}
