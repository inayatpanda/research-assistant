import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MixedEffectsWizard, type MixedEffectsConfig } from '../MixedEffectsWizard'

afterEach(() => cleanup())

describe('MixedEffectsWizard', () => {
  it('emits the *latest* outcome when the user picks one (no stale state)', () => {
    const onChange = vi.fn<(c: MixedEffectsConfig) => void>()
    render(
      <MixedEffectsWizard
        variables={['hhs', 'patient_id', 'approach', 'timepoint']}
        onChange={onChange}
      />,
    )
    const selects = screen.getAllByRole('combobox')
    const outcome = selects[0]
    fireEvent.change(outcome, { target: { value: 'hhs' } })

    // Find the most recent call — it must reflect the new outcome, not the
    // previous render's empty string.
    const lastCall = onChange.mock.calls.at(-1)?.[0]
    expect(lastCall?.outcome).toBe('hhs')
  })

  it('emits inner_cluster, reml and interaction_pair correctly', () => {
    const onChange = vi.fn<(c: MixedEffectsConfig) => void>()
    render(
      <MixedEffectsWizard
        variables={['hhs', 'patient_id', 'centre', 'approach', 'timepoint']}
        onChange={onChange}
      />,
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'hhs' } })
    fireEvent.change(selects[1], { target: { value: 'patient_id' } })
    fireEvent.change(selects[2], { target: { value: 'centre' } })

    // Pick ML (the second radio); use position to avoid the REML name overlap.
    const radios = screen.getAllByRole('radio')
    fireEvent.click(radios[1])
    fireEvent.click(screen.getByRole('checkbox'))
    const intA = screen.getByLabelText('interaction-a')
    const intB = screen.getByLabelText('interaction-b')
    fireEvent.change(intA, { target: { value: 'approach' } })
    fireEvent.change(intB, { target: { value: 'timepoint' } })

    const lastCall = onChange.mock.calls.at(-1)?.[0]
    expect(lastCall?.outcome).toBe('hhs')
    expect(lastCall?.cluster).toBe('patient_id')
    expect(lastCall?.inner_cluster).toBe('centre')
    expect(lastCall?.reml).toBe(false)
    expect(lastCall?.interaction_pair).toEqual(['approach', 'timepoint'])
  })

  it('does NOT emit interaction_pair when the checkbox is off', () => {
    const onChange = vi.fn<(c: MixedEffectsConfig) => void>()
    render(<MixedEffectsWizard variables={['hhs', 'pid']} onChange={onChange} />)
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'hhs' } })
    fireEvent.change(selects[1], { target: { value: 'pid' } })
    const lastCall = onChange.mock.calls.at(-1)?.[0]
    expect(lastCall?.interaction_pair).toBeUndefined()
  })
})
