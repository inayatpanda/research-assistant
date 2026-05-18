import { describe, expect, it } from 'vitest'

import { ConsortGetResponseSchema, JournalTemplateSchema } from '../api'

describe('ConsortGetResponseSchema', () => {
  it('parses a fully-populated response', () => {
    const parsed = ConsortGetResponseSchema.parse({
      data: {
        id: 'c1',
        project_id: 'p1',
        enrollment_assessed: 200,
        enrollment_excluded: 50,
        enrollment_excluded_reasons: { Declined: 30, Ineligible: 20 },
        randomised: 150,
        allocated_intervention: 75,
        allocated_control: 75,
        intervention_received: 75,
        control_received: 75,
        intervention_lost_followup: 3,
        control_lost_followup: 2,
        intervention_discontinued: 1,
        control_discontinued: 1,
        intervention_analysed: 71,
        control_analysed: 72,
        created_at: '2026-05-18T00:00:00Z',
        updated_at: '2026-05-18T00:01:00Z',
      },
      warnings: [],
      svg_base64: 'YWJj',
    })
    expect(parsed.data.randomised).toBe(150)
    expect(parsed.warnings).toEqual([])
  })

  it('accepts null counters', () => {
    const parsed = ConsortGetResponseSchema.parse({
      data: {
        id: 'c1',
        project_id: 'p1',
        created_at: '2026-05-18T00:00:00Z',
        updated_at: '2026-05-18T00:00:00Z',
      },
      warnings: ['some warning'],
      svg_base64: '',
    })
    expect(parsed.warnings).toEqual(['some warning'])
  })
})

describe('JournalTemplateSchema', () => {
  it('parses a JBJS entry', () => {
    const parsed = JournalTemplateSchema.parse({
      key: 'jbjs',
      label: 'JBJS',
      max_total_words: 4000,
      max_words_by_section: { Abstract: 300, Introduction: 600 },
      required_sections: ['Abstract', 'Introduction'],
      structured_abstract: true,
      reference_style: 'vancouver',
      max_figures: 8,
      max_tables: 4,
    })
    expect(parsed.key).toBe('jbjs')
    expect(parsed.max_total_words).toBe(4000)
  })
})
