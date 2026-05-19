/**
 * Phase 17 (MP17) — Stats depth frontend API stubs.
 *
 * These tests target the URL composition + body shape of the new
 * populations / imputation / CACE / sensitivity / IRR / instrument
 * helpers added in MP17. We mock axios so the test exercises pure URL
 * + payload logic without spinning up the backend.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  api,
  caceApi,
  imputationApi,
  instrumentsApi,
  irrApi,
  populationsApi,
  postHocApi,
  sapApi,
  sensitivityApi,
  analysisPlanLockApi,
} from '../api'

describe('MP17 stats depth API stubs', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('populationsApi.list composes the right URL', async () => {
    const spy = vi
      .spyOn(api, 'get')
      .mockResolvedValueOnce({ data: [] } as any)
    await populationsApi.list('p1', 'd1')
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/populations',
    )
  })

  it('populationsApi.create POSTs the body', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({ data: { id: 'pop-1' } } as any)
    await populationsApi.create('p1', 'd1', {
      name: 'ITT',
      definition: { filter: '', label: 'ITT' },
      study_assignment_field: 'arm',
    })
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/populations',
      expect.objectContaining({ name: 'ITT' }),
    )
  })

  it('postHocApi.run targets /post-hoc with the chosen method', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({
        data: { method: 'tukey', n_groups: 3, pairs: [] },
      } as any)
    const res = await postHocApi.run('p1', 'a1', {
      method: 'tukey',
      outcome: 'y',
      groups: 'arm',
    })
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/analyses/a1/post-hoc',
      expect.objectContaining({ method: 'tukey' }),
    )
    expect(res.method).toBe('tukey')
  })

  it('imputationApi.run fills sensible defaults for n_imputations + seed', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({ data: { id: 'r1' } } as any)
    await imputationApi.run('p1', 'd1', {
      method: 'mice',
      target_cols: ['y'],
    })
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/impute',
      expect.objectContaining({
        method: 'mice',
        target_cols: ['y'],
        n_imputations: 5,
        seed: 42,
      }),
    )
  })

  it('caceApi.run POSTs the required body shape', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({ data: { cace_estimate: 1, se: 0.1, p: 0.01, compliance_rate: 0.7, n: 100 } } as any)
    await caceApi.run('p1', 'a1', {
      outcome: 'y',
      assigned: 'z',
      received: 'd',
    })
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/analyses/a1/cace',
      expect.objectContaining({ assigned: 'z' }),
    )
  })

  it('sensitivityApi.run targets /sensitivity with the requested type', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({
        data: { type: 'tipping_point', effect_estimate: 0, p_value: 0.5, threshold: 1.5, n_imputed: 5, note: '' },
      } as any)
    await sensitivityApi.run('p1', 'a1', {
      type: 'tipping_point',
      outcome: 'y',
      group: 'arm',
    })
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/analyses/a1/sensitivity',
      expect.objectContaining({ type: 'tipping_point' }),
    )
  })

  it('irrApi.fleiss POSTs a Fleiss matrix', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({
        data: { kappa: 1, z: 10, p: 0, n_subjects: 5, n_raters: 5, n_categories: 2 },
      } as any)
    await irrApi.fleiss('p1', 'd1', [
      [5, 0],
      [5, 0],
    ])
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/irr',
      expect.objectContaining({ method: 'fleiss' }),
    )
  })

  it('irrApi.weightedKappa defaults to linear weights', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({
        data: { kappa: 1, weights: 'linear', n: 4, ci_low: null, ci_high: null, se: null },
      } as any)
    await irrApi.weightedKappa('p1', 'd1', [0, 1, 2, 3], [0, 1, 2, 3])
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/irr',
      expect.objectContaining({ method: 'weighted_kappa', weights: 'linear' }),
    )
  })

  it('instrumentsApi.catalogue hits /api/instruments/catalogue', async () => {
    const spy = vi
      .spyOn(api, 'get')
      .mockResolvedValueOnce({ data: { instruments: [] } } as any)
    await instrumentsApi.catalogue()
    expect(spy).toHaveBeenCalledWith('/api/instruments/catalogue')
  })

  it('instrumentsApi.bind PATCHes the variable binding', async () => {
    const spy = vi
      .spyOn(api, 'patch')
      .mockResolvedValueOnce({
        data: { variable_id: 'v1', instrument_key: 'HHS' },
      } as any)
    await instrumentsApi.bind('p1', 'd1', 'v1', 'HHS')
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/datasets/d1/variables/v1/instrument-binding',
      expect.objectContaining({ instrument_key: 'HHS' }),
    )
  })

  it('analysisPlanLockApi.lock POSTs to /lock', async () => {
    const spy = vi
      .spyOn(api, 'post')
      .mockResolvedValueOnce({
        data: { plan_id: 'pl1', integrity_hash: 'abc', locked_at: '2026-05-19T00:00:00Z' },
      } as any)
    await analysisPlanLockApi.lock('p1', 'pl1')
    expect(spy).toHaveBeenCalledWith(
      '/api/projects/p1/analysis-plans/pl1/lock',
    )
  })

  it('sapApi.exportUrl builds a download path', () => {
    expect(sapApi.exportUrl('p1', 'pl1', 'docx')).toBe(
      '/api/projects/p1/analysis-plans/pl1/sap?format=docx',
    )
    expect(sapApi.exportUrl('p1', 'pl1', 'pdf')).toBe(
      '/api/projects/p1/analysis-plans/pl1/sap?format=pdf',
    )
  })
})
