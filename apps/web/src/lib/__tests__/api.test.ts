import { describe, expect, it } from 'vitest'

import {
  __internal,
  AIScreeningSuggestResponseSchema,
  BibliographyResponseSchema,
  ExtractionFieldGroupSchema,
  ExtractionRecordSchema,
  PrismaResponseSchema,
  ReviewSchema,
  RoBAssessmentSchema,
  RoBToolDefSchema,
  ScreeningRecordSchema,
  SearchRecordSchema,
} from '../api'

describe('reviewsApi schemas', () => {
  it('parses a Review payload', () => {
    const parsed = ReviewSchema.parse({
      id: 'r1',
      project_id: 'p1',
      pico_population: 'adults',
      pico_intervention: 'TKA',
      pico_comparator: null,
      pico_outcome: 'infection',
      eligibility_inclusion: null,
      eligibility_exclusion: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    })
    expect(parsed.id).toBe('r1')
  })

  it('parses a SearchRecord', () => {
    const parsed = SearchRecordSchema.parse({
      id: 's1',
      review_id: 'r1',
      database_name: 'PubMed',
      query_string: 'tka AND infection',
      date_searched: '2024-02-03T00:00:00Z',
      n_results: 42,
      notes: null,
      created_at: '2024-02-04T00:00:00Z',
    })
    expect(parsed.n_results).toBe(42)
  })

  it('parses a ScreeningRecord with ai_suggestion', () => {
    const parsed = ScreeningRecordSchema.parse({
      id: 'sc1',
      review_id: 'r1',
      article_id: 'a1',
      stage: 'title_abstract',
      decision: 'include',
      exclusion_category: null,
      reason: null,
      reviewer_id: 'u1',
      ai_suggestion: { vote: 'include', reason: 'matches PICO', model: 'gemini' },
      decided_at: null,
      created_at: '2024-03-01T00:00:00Z',
    })
    expect(parsed.decision).toBe('include')
  })

  it('parses an AI screening response', () => {
    const parsed = AIScreeningSuggestResponseSchema.parse({
      vote: 'maybe',
      reason: 'unclear from abstract',
      model: 'claude',
    })
    expect(parsed.vote).toBe('maybe')
  })

  it('parses a RoB tool catalogue entry', () => {
    const parsed = RoBToolDefSchema.parse({
      key: 'rob2',
      label: 'RoB 2',
      applies_to: ['RCT'],
      domains: [
        {
          key: 'randomisation',
          label: 'Randomisation process',
          question: 'q?',
          answers: ['low', 'some_concerns', 'high', 'unclear'],
          critical: false,
        },
      ],
    })
    expect(parsed.domains.length).toBe(1)
  })

  it('parses a RoBAssessment', () => {
    const parsed = RoBAssessmentSchema.parse({
      id: 'rb1',
      review_id: 'r1',
      article_id: 'a1',
      tool: 'rob2',
      domain_answers: { randomisation: 'low' },
      overall_auto: 'low',
      overall_override: null,
      notes: null,
      created_at: '2024-03-02T00:00:00Z',
      updated_at: '2024-03-02T00:00:00Z',
    })
    expect(parsed.tool).toBe('rob2')
  })

  it('parses an ExtractionFieldGroup', () => {
    const parsed = ExtractionFieldGroupSchema.parse({
      key: 'basic',
      label: 'Basic',
      fields: [
        {
          key: 'first_author',
          label: 'First author',
          type: 'text',
          required: true,
          choices: null,
        },
      ],
    })
    expect(parsed.fields[0].required).toBe(true)
  })

  it('parses an ExtractionRecord', () => {
    const parsed = ExtractionRecordSchema.parse({
      id: 'e1',
      review_id: 'r1',
      article_id: 'a1',
      fields: { basic: { first_author: 'Smith' } },
      created_at: '2024-03-03T00:00:00Z',
      updated_at: '2024-03-03T00:00:00Z',
    })
    expect(parsed.fields).toBeTypeOf('object')
  })

  it('parses a BibliographyResponse', () => {
    const parsed = BibliographyResponseSchema.parse({
      style: 'ieee',
      entries: [
        {
          number: 1,
          article_id: 'art-1',
          formatted_entry: '[1] J. Doe, "Title," Journal, 2024.',
          first_section: 'Introduction',
        },
      ],
    })
    expect(parsed.style).toBe('ieee')
    expect(parsed.entries).toHaveLength(1)
  })

  it('parses Content-Disposition filenames', () => {
    const p = __internal.parseContentDispositionFilename
    expect(p('attachment; filename="report-2024-05-18.docx"')).toBe('report-2024-05-18.docx')
    expect(p('inline; filename=plain.pdf')).toBe('plain.pdf')
    expect(p("attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf")).toBe('résumé.pdf')
    expect(p(null)).toBeNull()
    expect(p('')).toBeNull()
  })

  // E2E-sweep bug #UX1 — fetch wrapper used to surface "Network Error"
  // instead of the FastAPI `detail` body. The new extractor walks several
  // body shapes before falling back.
  describe('extractErrorMessage', () => {
    const extract = __internal.extractErrorMessage

    function fakeError(opts: {
      status?: number
      statusText?: string
      data?: unknown
      message?: string
    }) {
      // Minimal AxiosError shape — only `response` + `message` are
      // touched by the extractor.
      return {
        isAxiosError: true,
        message: opts.message ?? 'Network Error',
        response: opts.status
          ? { status: opts.status, statusText: opts.statusText ?? '', data: opts.data }
          : undefined,
      } as unknown as Parameters<typeof extract>[0]
    }

    it('uses string `detail` when present', () => {
      expect(
        extract(
          fakeError({ status: 500, data: { detail: 'population_id required' } }),
        ),
      ).toBe('population_id required')
    })

    it('joins Pydantic list-style `detail` entries with loc prefixes', () => {
      const msg = extract(
        fakeError({
          status: 422,
          data: {
            detail: [
              { msg: 'field required', loc: ['body', 'name'] },
              { msg: 'must be int', loc: ['body', 'year'] },
            ],
          },
        }),
      )
      expect(msg).toContain('body.name: field required')
      expect(msg).toContain('body.year: must be int')
    })

    it('falls back to body.message', () => {
      expect(
        extract(fakeError({ status: 500, data: { message: 'boom' } })),
      ).toBe('boom')
    })

    it('falls back to status text when body has nothing useful', () => {
      expect(
        extract(fakeError({ status: 503, statusText: 'Service Unavailable', data: {} })),
      ).toBe('503 Service Unavailable')
    })

    it('returns `Request failed` for raw network errors', () => {
      expect(extract(fakeError({ message: 'Network Error' }))).toBe('Request failed')
    })
  })

  it('parses a Prisma response', () => {
    const parsed = PrismaResponseSchema.parse({
      counts: {
        identified: 60,
        after_dedupe: 60,
        screened: 2,
        excluded_title: 1,
        full_text_assessed: 1,
        excluded_full: {
          population: 0,
          intervention: 0,
          outcome: 0,
          study_design: 0,
          language: 0,
          duplicate: 0,
          other: 0,
        },
        included: 1,
      },
      svg: '<svg/>',
    })
    expect(parsed.counts.identified).toBe(60)
  })
})
