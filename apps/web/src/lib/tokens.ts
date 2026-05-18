export const highlightColors = {
  intro:      { solid: '#EF4444', fill: 'rgba(239,68,68,0.22)',  ring: 'rgba(239,68,68,0.55)' },
  method:     { solid: '#3B82F6', fill: 'rgba(59,130,246,0.22)', ring: 'rgba(59,130,246,0.55)' },
  results:    { solid: '#22C55E', fill: 'rgba(34,197,94,0.22)',  ring: 'rgba(34,197,94,0.55)' },
  discussion: { solid: '#EAB308', fill: 'rgba(234,179,8,0.22)',  ring: 'rgba(234,179,8,0.55)' },
} as const

export type HighlightColor = keyof typeof highlightColors

export const sectionLabels: Record<HighlightColor, string> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

export const studyTypes = [
  'Before/After Intervention',
  'Outcome Study',
  'Risk Factor Analysis',
  'Group Comparison',
  'Prospective Cohort',
  'Retrospective Case Series',
  'Systematic Review',
  'Randomised Controlled Trial',
] as const
export type StudyType = (typeof studyTypes)[number]

export const citationStyles = ['vancouver', 'apa', 'harvard'] as const
export type CitationStyle = (typeof citationStyles)[number]

export const aiProviders = ['gemini', 'claude', 'openai'] as const
export type AIProviderName = (typeof aiProviders)[number]
