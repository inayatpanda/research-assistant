/**
 * Phase 17 (MP17) — Curated outcome-instrument library browser.
 *
 * Search the 30-item catalogue + click-to-bind to a dataset column. The
 * binding is pure metadata — it never changes analysis behaviour.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { instrumentsApi, type InstrumentSpec } from '../../lib/api'

interface Variable {
  id: string
  name: string
  instrument_key?: string | null
}

interface Props {
  projectId: string
  datasetId: string
  variables: Variable[]
}

export function InstrumentLibraryBrowser({ projectId, datasetId, variables }: Props) {
  const qc = useQueryClient()
  const { data: instruments } = useQuery({
    queryKey: ['instrument-catalogue'],
    queryFn: () => instrumentsApi.catalogue(),
  })
  const [query, setQuery] = useState('')
  const [selectedVar, setSelectedVar] = useState<string>('')

  const filtered = (instruments ?? []).filter((i: InstrumentSpec) => {
    const q = query.toLowerCase()
    return (
      !q ||
      i.name.toLowerCase().includes(q) ||
      i.abbreviation.toLowerCase().includes(q) ||
      i.category.toLowerCase().includes(q)
    )
  })

  const bindMutation = useMutation({
    mutationFn: ({ varId, key }: { varId: string; key: string | null }) =>
      instrumentsApi.bind(projectId, datasetId, varId, key),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['dataset', projectId, datasetId] }),
  })

  return (
    <div data-testid="instrument-library">
      <h4>Outcome instrument library</h4>
      <input
        aria-label="search-instruments"
        placeholder="Search by name, abbreviation, or category"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <label>
        Bind to variable
        <select value={selectedVar} onChange={(e) => setSelectedVar(e.target.value)}>
          <option value="">—</option>
          {variables.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}{v.instrument_key ? ` (currently: ${v.instrument_key})` : ''}
            </option>
          ))}
        </select>
      </label>
      <ul className="instrument-list">
        {filtered.map((i: InstrumentSpec) => (
          <li key={i.abbreviation}>
            <strong>{i.abbreviation}</strong> — {i.name}
            <em> ({i.scale_low}–{i.scale_high}, {i.direction})</em>
            {selectedVar ? (
              <button
                onClick={() => bindMutation.mutate({ varId: selectedVar, key: i.abbreviation })}
              >
                Bind
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default InstrumentLibraryBrowser
