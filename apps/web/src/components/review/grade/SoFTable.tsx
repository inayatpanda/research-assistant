import { Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { GradeAssessmentRead } from '@/lib/api'
import { CERTAINTY_LABEL, CERTAINTY_SYMBOL } from '@/lib/grade'
import { useDeleteGrade } from '@/hooks/useGrade'

export function SoFTable({
  projectId,
  rows,
  onSelect,
}: {
  projectId: string
  rows: GradeAssessmentRead[]
  onSelect?: (row: GradeAssessmentRead) => void
}) {
  const remove = useDeleteGrade(projectId)

  if (rows.length === 0) {
    return (
      <div className="rounded border border-dashed p-6 text-center text-sm text-muted-foreground">
        No GRADE outcomes yet. Add one above to start building the Summary of
        Findings table.
      </div>
    )
  }

  return (
    <table
      className="sof-table w-full border-collapse text-sm"
      data-testid="sof-table"
    >
      <thead>
        <tr className="border-b">
          <th className="px-3 py-2 text-left">Outcome</th>
          <th className="px-3 py-2 text-left">Starting</th>
          <th className="px-3 py-2 text-left">Downgrades</th>
          <th className="px-3 py-2 text-left">Certainty</th>
          <th className="px-3 py-2 text-left">Notes</th>
          <th className="px-3 py-2" />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const downgrades = [
            row.domain_risk_of_bias,
            row.domain_inconsistency,
            row.domain_indirectness,
            row.domain_imprecision,
            row.domain_publication_bias,
          ].filter((d) => d !== 'not_serious')
          return (
            <tr key={row.id} className="border-b">
              <td className="px-3 py-2">
                <button
                  className="text-left underline-offset-2 hover:underline"
                  onClick={() => onSelect?.(row)}
                >
                  {row.outcome_label}
                </button>
              </td>
              <td className="px-3 py-2 capitalize">
                {row.starting_certainty}
              </td>
              <td className="px-3 py-2 text-xs">
                {downgrades.length === 0 ? (
                  <span className="text-muted-foreground">none</span>
                ) : (
                  downgrades.join(', ')
                )}
              </td>
              <td className="px-3 py-2">
                <span
                  className={`cert cert-${row.certainty} rounded px-2 py-0.5 text-xs font-medium`}
                  data-certainty={row.certainty}
                >
                  {CERTAINTY_LABEL[row.certainty]}{' '}
                  {CERTAINTY_SYMBOL[row.certainty]}
                </span>
              </td>
              <td className="px-3 py-2 text-xs text-muted-foreground">
                {row.notes ?? ''}
              </td>
              <td className="px-3 py-2 text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${row.outcome_label}`}
                  onClick={() => remove.mutate(row.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
