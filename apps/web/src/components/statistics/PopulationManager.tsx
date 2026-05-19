/**
 * Phase 17 (MP17) — Per-dataset analysis-population manager.
 *
 * Defines + lists named sub-population definitions (ITT / PP / safety / …).
 * Each population is a pandas filter expression with a study-assignment
 * column. Pure metadata — the population is only applied at analysis time
 * by passing its id with the request.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import {
  populationsApi,
  type AnalysisPopulation,
  type PopulationCreateBody,
} from '../../lib/api'

interface Props {
  projectId: string
  datasetId: string
}

export function PopulationManager({ projectId, datasetId }: Props) {
  const qc = useQueryClient()
  const { data: populations, isLoading } = useQuery({
    queryKey: ['populations', projectId, datasetId],
    queryFn: () => populationsApi.list(projectId, datasetId),
  })

  const [form, setForm] = useState<PopulationCreateBody>({
    name: '',
    definition: { filter: '', label: '' },
    study_assignment_field: '',
    treatment_received_field: null,
  })

  const createMutation = useMutation({
    mutationFn: (body: PopulationCreateBody) =>
      populationsApi.create(projectId, datasetId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['populations', projectId, datasetId] })
      setForm({
        name: '',
        definition: { filter: '', label: '' },
        study_assignment_field: '',
        treatment_received_field: null,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => populationsApi.delete(projectId, datasetId, id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['populations', projectId, datasetId] }),
  })

  return (
    <div className="population-manager" data-testid="population-manager">
      <h3>Analysis populations</h3>
      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <ul>
          {(populations ?? []).map((p: AnalysisPopulation) => (
            <li key={p.id}>
              <strong>{p.name}</strong>
              {p.definition?.filter ? <code>{p.definition.filter}</code> : null}
              <button
                onClick={() => deleteMutation.mutate(p.id)}
                aria-label={`delete-${p.name}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          createMutation.mutate(form)
        }}
      >
        <input
          aria-label="population-name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="e.g. ITT / PP / Safety"
        />
        <input
          aria-label="population-filter"
          value={form.definition.filter}
          onChange={(e) =>
            setForm({
              ...form,
              definition: { ...form.definition, filter: e.target.value },
            })
          }
          placeholder='pandas filter, e.g. arm == "treated"'
        />
        <input
          aria-label="population-assignment-field"
          value={form.study_assignment_field}
          onChange={(e) =>
            setForm({ ...form, study_assignment_field: e.target.value })
          }
          placeholder="assignment column"
        />
        <button type="submit" disabled={createMutation.isPending}>
          Add population
        </button>
      </form>
    </div>
  )
}

export default PopulationManager
