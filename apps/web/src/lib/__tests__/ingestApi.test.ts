import { describe, expect, it } from 'vitest'

import {
  ArticleMetadataSchema,
  ArticleSchema,
  ArticleSourceSchema,
  DuplicateGroupSchema,
  ImportFromMetadataResponseSchema,
} from '../api'

describe('ingestApi schemas (Phase 8.6)', () => {
  it('parses every ArticleSource enum value', () => {
    for (const src of ['upload', 'doi', 'pubmed', 'ris', 'bibtex', 'manual']) {
      expect(ArticleSourceSchema.parse(src)).toBe(src)
    }
    expect(() => ArticleSourceSchema.parse('telegram')).toThrow()
  })

  it('parses an ArticleMetadata payload', () => {
    const meta = ArticleMetadataSchema.parse({
      title: 'X',
      authors: ['A', 'B'],
      journal: 'J',
      year: 2023,
      doi: '10.1/x',
      pmid: '12345',
      abstract: 'lorem',
      source: 'doi',
    })
    expect(meta.title).toBe('X')
    expect(meta.source).toBe('doi')
  })

  it('parses a DuplicateGroup with score in [0, 1]', () => {
    const grp = DuplicateGroupSchema.parse({
      keep_candidate_id: 'a',
      candidate_ids: ['a', 'b'],
      reason: 'doi_exact',
      score: 1.0,
    })
    expect(grp.reason).toBe('doi_exact')
    expect(grp.candidate_ids.length).toBe(2)
    // Singleton group rejected by the min(2) constraint
    expect(() =>
      DuplicateGroupSchema.parse({
        keep_candidate_id: 'a',
        candidate_ids: ['a'],
        reason: 'title_fuzzy',
        score: 0.95,
      }),
    ).toThrow()
  })

  it('parses an ImportFromMetadataResponse with created + duplicate_groups', () => {
    const article = {
      id: 'a1',
      user_id: 'u1',
      project_id: 'p1',
      title: 'X',
      authors: [],
      journal: null,
      year: null,
      volume: null,
      issue: null,
      pages: null,
      doi: null,
      file_ref: null,
      file_type: null,
      study_design: null,
      review_status: 'pending',
      exclusion_reason: null,
      conflict_of_interest: null,
      source: 'doi',
      created_at: '2024-01-01T00:00:00Z',
    }
    const resp = ImportFromMetadataResponseSchema.parse({
      created: [article],
      skipped_duplicates: [],
      duplicate_groups: [
        {
          keep_candidate_id: 'a1',
          candidate_ids: ['a1', 'a2'],
          reason: 'title_fuzzy',
          score: 0.93,
        },
      ],
    })
    expect(resp.created.length).toBe(1)
    expect(resp.duplicate_groups[0].reason).toBe('title_fuzzy')
  })

  it('ArticleSchema defaults source to upload when omitted', () => {
    const a = ArticleSchema.parse({
      id: 'a1',
      user_id: 'u1',
      project_id: 'p1',
      title: 'X',
      authors: [],
      journal: null,
      year: null,
      volume: null,
      issue: null,
      pages: null,
      doi: null,
      file_ref: null,
      file_type: null,
      study_design: null,
      review_status: 'pending',
      exclusion_reason: null,
      conflict_of_interest: null,
      created_at: '2024-01-01T00:00:00Z',
    })
    expect(a.source).toBe('upload')
  })
})
