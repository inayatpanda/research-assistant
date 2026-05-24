import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import type { DatasetVariable } from '@/lib/api'

import {
  ColumnPicker,
  MultiColumnPicker,
  displayName,
  effectiveType,
} from '../ColumnPicker'

beforeAll(() => {
  // Radix Select needs these polyfills under jsdom.
  const proto = Element.prototype as unknown as Record<string, unknown>
  if (!proto.scrollIntoView) proto.scrollIntoView = vi.fn()
  if (!('hasPointerCapture' in proto)) {
    proto.hasPointerCapture = vi.fn(() => false)
    proto.releasePointerCapture = vi.fn()
  }
})

afterEach(() => cleanup())

function v(
  name: string,
  type: DatasetVariable['inferred_type'],
  display?: string,
): DatasetVariable {
  return {
    id: `v-${name}`,
    dataset_id: 'd',
    name,
    position: 0,
    inferred_type: type,
    user_type: null,
    n_missing: 0,
    sample_values: [],
    instrument_key: null,
    display_label: display ?? null,
  }
}

describe('ColumnPicker', () => {
  it('renders the label + placeholder for empty selection', () => {
    render(
      <ColumnPicker
        label="Outcome"
        variables={[v('score', 'numeric'), v('arm', 'nominal')]}
        value={null}
        onChange={() => {}}
      />,
    )
    expect(screen.getByText('Outcome')).toBeTruthy()
    expect(screen.getByText('Select a column')).toBeTruthy()
  })

  it('shows "No matching columns" when filter has no hits', () => {
    render(
      <ColumnPicker
        label="Time"
        variables={[v('score', 'numeric')]}
        value={null}
        onChange={() => {}}
        acceptedTypes={['time']}
      />,
    )
    expect(screen.getByText('No matching columns')).toBeTruthy()
  })

  it('prefers display_label over canonical column name', () => {
    const var1 = v('age_years', 'numeric', 'Age (years)')
    expect(displayName(var1)).toBe('Age (years)')
    expect(effectiveType(var1)).toBe('numeric')
  })

  it('falls back to canonical name when display_label is empty', () => {
    expect(displayName(v('age', 'numeric', ''))).toBe('age')
  })
})

describe('MultiColumnPicker', () => {
  it('renders one checkbox per filtered column', () => {
    render(
      <MultiColumnPicker
        label="Predictors"
        variables={[
          v('age', 'numeric'),
          v('sex', 'nominal'),
          v('arm', 'nominal'),
        ]}
        value={['age']}
        onChange={() => {}}
        acceptedTypes={['numeric']}
      />,
    )
    const boxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    expect(boxes).toHaveLength(1)
    expect(boxes[0].checked).toBe(true)
  })

  it('shows empty state when no columns match', () => {
    render(
      <MultiColumnPicker
        label="Confounders"
        variables={[v('age', 'numeric')]}
        value={[]}
        onChange={() => {}}
        acceptedTypes={['event_indicator']}
      />,
    )
    expect(screen.getByText('No matching columns')).toBeTruthy()
  })

  it('invokes onChange with toggled value on click', () => {
    const onChange = vi.fn()
    render(
      <MultiColumnPicker
        label="Predictors"
        variables={[v('age', 'numeric')]}
        value={[]}
        onChange={onChange}
      />,
    )
    const box = screen.getByRole('checkbox') as HTMLInputElement
    box.click()
    expect(onChange).toHaveBeenCalledWith(['age'])
  })
})
