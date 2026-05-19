import { describe, expect, it } from 'vitest'

import {
  LivingReviewHitReadSchema,
  LivingReviewJobReadSchema,
  LivingReviewRunResultSchema,
} from '../api'

describe('livingReviewApi schemas', () => {
  it('parses a LivingReviewJobRead with a null last_run_at', () => {
    const parsed = LivingReviewJobReadSchema.parse({
      id: 'j1',
      project_id: 'p1',
      review_id: 'r1',
      pubmed_query: 'aspirin AND stroke',
      schedule: 'weekly',
      enabled: true,
      last_run_at: null,
      last_hit_count: null,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    })
    expect(parsed.schedule).toBe('weekly')
    expect(parsed.last_run_at).toBeNull()
  })

  it('rejects an unknown schedule', () => {
    expect(() =>
      LivingReviewJobReadSchema.parse({
        id: 'j1',
        project_id: 'p1',
        review_id: 'r1',
        pubmed_query: 'x',
        schedule: 'fortnightly',
        enabled: true,
        last_run_at: null,
        last_hit_count: null,
        created_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
      }),
    ).toThrow()
  })

  it('parses a LivingReviewHitRead', () => {
    const parsed = LivingReviewHitReadSchema.parse({
      id: 'h1',
      job_id: 'j1',
      run_at: '2026-05-10T02:00:00Z',
      pmid: '12345',
      title: 'Aspirin and primary prevention',
      decision: 'new',
      seen_in_baseline: false,
      created_at: '2026-05-10T02:00:00Z',
    })
    expect(parsed.pmid).toBe('12345')
    expect(parsed.decision).toBe('new')
  })

  it('rejects an unknown hit decision', () => {
    expect(() =>
      LivingReviewHitReadSchema.parse({
        id: 'h1',
        job_id: 'j1',
        run_at: '2026-05-10T02:00:00Z',
        pmid: '12345',
        title: 'x',
        decision: 'maybe',
        seen_in_baseline: false,
        created_at: '2026-05-10T02:00:00Z',
      }),
    ).toThrow()
  })

  it('parses a LivingReviewRunResult', () => {
    const parsed = LivingReviewRunResultSchema.parse({
      job_id: 'j1',
      new_hits: 3,
      total_fetched: 50,
      ran_at: '2026-05-10T02:00:00Z',
    })
    expect(parsed.new_hits).toBe(3)
    expect(parsed.total_fetched).toBe(50)
  })
})
