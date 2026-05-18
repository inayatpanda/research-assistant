import { describe, expect, it } from 'vitest'

import {
  AuthorReadSchema,
  AffiliationReadSchema,
  ContributionReadSchema,
  CREDIT_ROLES,
  CreditRoleSchema,
  ProjectFrontmatterSchema,
} from '../api'

describe('CreditRoleSchema', () => {
  it('exposes exactly 14 CRediT roles', () => {
    expect(CREDIT_ROLES.length).toBe(14)
  })

  it('accepts every canonical role', () => {
    for (const role of CREDIT_ROLES) {
      expect(CreditRoleSchema.parse(role)).toBe(role)
    }
  })

  it('rejects an unknown role', () => {
    expect(() => CreditRoleSchema.parse('Bogus')).toThrow()
  })
})

describe('AuthorReadSchema', () => {
  it('parses a full server payload', () => {
    const parsed = AuthorReadSchema.parse({
      id: 'a1',
      project_id: 'p1',
      full_name: 'Jane Doe',
      given_name: 'Jane',
      family_name: 'Doe',
      orcid: '0000-0002-1825-0097',
      email: 'jane@example.com',
      is_corresponding: true,
      position: 1,
      created_at: '2026-05-18T00:00:00Z',
      updated_at: '2026-05-18T00:01:00Z',
      affiliation_ids: ['af1', 'af2'],
    })
    expect(parsed.full_name).toBe('Jane Doe')
    expect(parsed.affiliation_ids).toEqual(['af1', 'af2'])
  })

  it('allows orcid and email to be null', () => {
    const parsed = AuthorReadSchema.parse({
      id: 'a1',
      project_id: 'p1',
      full_name: 'Anon',
      given_name: '',
      family_name: '',
      orcid: null,
      email: null,
      is_corresponding: false,
      position: 2,
      created_at: '2026-05-18T00:00:00Z',
      updated_at: '2026-05-18T00:00:00Z',
      affiliation_ids: [],
    })
    expect(parsed.orcid).toBeNull()
    expect(parsed.email).toBeNull()
  })
})

describe('AffiliationReadSchema', () => {
  it('parses a server payload', () => {
    const parsed = AffiliationReadSchema.parse({
      id: 'af1',
      project_id: 'p1',
      name: 'Oxford',
      address: null,
      city: 'Oxford',
      country: 'UK',
      position: 1,
      created_at: '2026-05-18T00:00:00Z',
    })
    expect(parsed.name).toBe('Oxford')
    expect(parsed.city).toBe('Oxford')
  })
})

describe('ContributionReadSchema', () => {
  it('enforces CRediT role enum', () => {
    expect(() =>
      ContributionReadSchema.parse({
        id: 'c1',
        author_id: 'a1',
        role: 'Not A Role',
      }),
    ).toThrow()
  })
  it('parses a valid row', () => {
    const parsed = ContributionReadSchema.parse({
      id: 'c1',
      author_id: 'a1',
      role: 'Conceptualization',
    })
    expect(parsed.role).toBe('Conceptualization')
  })
})

describe('ProjectFrontmatterSchema', () => {
  it('parses the auto-created shape', () => {
    const parsed = ProjectFrontmatterSchema.parse({
      id: 'fm1',
      project_id: 'p1',
      funding_statement: null,
      funders: [],
      ethics_irb: null,
      ethics_approval_number: null,
      ethics_consent: null,
      conflicts_statement: null,
      structured_abstract_enabled: false,
      structured_abstract: {
        background: '',
        methods: '',
        results: '',
        conclusions: '',
      },
      updated_at: '2026-05-18T00:00:00Z',
    })
    expect(parsed.structured_abstract_enabled).toBe(false)
    expect(parsed.funders).toEqual([])
  })

  it('parses a populated frontmatter with funders + structured abstract', () => {
    const parsed = ProjectFrontmatterSchema.parse({
      id: 'fm1',
      project_id: 'p1',
      funding_statement: 'NIH grant',
      funders: [{ name: 'NIH', grant_id: 'R01-1' }],
      ethics_irb: 'Local IRB',
      ethics_approval_number: 'IRB-2024-01',
      ethics_consent: 'Written informed consent',
      conflicts_statement: 'None',
      structured_abstract_enabled: true,
      structured_abstract: {
        background: 'B',
        methods: 'M',
        results: 'R',
        conclusions: 'C',
      },
      updated_at: '2026-05-18T00:00:00Z',
    })
    expect(parsed.funders).toEqual([{ name: 'NIH', grant_id: 'R01-1' }])
    expect(parsed.structured_abstract.methods).toBe('M')
  })
})
