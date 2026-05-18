import { describe, expect, it } from 'vitest'

import {
  MetaAnalysisReadSchema,
  MetaInputReadSchema,
  metaAnalysisApi,
} from '../api'

describe('metaAnalysisApi schemas', () => {
  it('parses a MetaInputRead payload', () => {
    const parsed = MetaInputReadSchema.parse({
      id: 'i1',
      meta_id: 'm1',
      article_id: 'a1',
      study_label: 'Smith 2020',
      subgroup: null,
      mean_a: 1.5,
      sd_a: 0.5,
      n_a: 20,
      mean_b: 0.5,
      sd_b: 0.5,
      n_b: 20,
      events_a: null,
      n_a_total: null,
      events_b: null,
      n_b_total: null,
      log_hr: null,
      se_log_hr: null,
      hr: null,
      hr_ci_low: null,
      hr_ci_high: null,
      r: null,
      n_r: null,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    })
    expect(parsed.study_label).toBe('Smith 2020')
    expect(parsed.mean_a).toBe(1.5)
  })

  it('parses a MetaAnalysisRead payload with inputs', () => {
    const parsed = MetaAnalysisReadSchema.parse({
      id: 'm1',
      review_id: 'r1',
      title: 'Pain at 6 weeks',
      effect_metric: 'smd',
      model: 'random',
      subgroup_variable: null,
      pooled_estimate: 0.45,
      pooled_se: 0.08,
      ci_low: 0.29,
      ci_high: 0.61,
      z_value: 5.6,
      p_value: 0.0000001,
      q_value: 5.4,
      q_df: 3,
      q_p: 0.14,
      i2: 44.4,
      tau2: 0.012,
      subgroup_summary: null,
      ai_interpretation: null,
      status: 'completed',
      inputs: [],
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    })
    expect(parsed.effect_metric).toBe('smd')
    expect(parsed.status).toBe('completed')
  })

  it('provides absolute URLs for plot endpoints', () => {
    const url = metaAnalysisApi.forestUrl('p1', 'm1')
    expect(url).toContain('/api/projects/p1/reviews/meta/m1/forest.png')
    const url2 = metaAnalysisApi.funnelUrl('p1', 'm1')
    expect(url2).toContain('/api/projects/p1/reviews/meta/m1/funnel.png')
  })
})
