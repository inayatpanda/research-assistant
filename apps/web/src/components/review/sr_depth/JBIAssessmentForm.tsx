/**
 * JBIAssessmentForm (MP19) — renders one of the 7 JBI Critical Appraisal
 * Tools as a yes/no/unclear/na per-item form. Mirrors RoBAssessmentForm
 * but uses the JBI item-IDs and 4-state answer set.
 *
 * The actual persistence path reuses ``rob_assessments`` via the existing
 * RoB API — the parent component is responsible for posting answers via
 * ``robApi.upsert(...)`` so this component is a pure rendered form.
 */
import { useEffect, useState } from 'react'

import type { RoBToolDef } from '@/lib/api'

const ANSWERS = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'unclear', label: 'Unclear' },
  { value: 'na', label: 'NA' },
] as const

type Props = {
  tool: RoBToolDef
  initial?: Record<string, string>
  onChange?: (answers: Record<string, string>) => void
  readOnly?: boolean
}

export function JBIAssessmentForm({
  tool,
  initial,
  onChange,
  readOnly = false,
}: Props) {
  const [answers, setAnswers] = useState<Record<string, string>>(initial ?? {})

  useEffect(() => {
    if (initial) setAnswers(initial)
  }, [initial])

  const set = (key: string, value: string) => {
    const next = { ...answers, [key]: value }
    setAnswers(next)
    onChange?.(next)
  }

  return (
    <fieldset
      data-testid={`jbi-form-${tool.key}`}
      className="space-y-3"
      disabled={readOnly}
    >
      <legend className="text-sm font-medium">{tool.label}</legend>
      {tool.domains.map((d) => (
        <div key={d.key} className="rounded border border-border p-3">
          <div className="text-sm">{d.question}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {ANSWERS.map((a) => (
              <label
                key={a.value}
                className="inline-flex items-center gap-1.5 text-[12px]"
              >
                <input
                  type="radio"
                  name={`${tool.key}-${d.key}`}
                  value={a.value}
                  checked={answers[d.key] === a.value}
                  onChange={() => set(d.key, a.value)}
                />
                {a.label}
              </label>
            ))}
          </div>
        </div>
      ))}
    </fieldset>
  )
}
