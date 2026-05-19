import { Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { PROSPERO_FIELDS } from '@/lib/api'
import {
  useExportProspero,
  useProspero,
  useUpdateProspero,
} from '@/hooks/useProspero'

const SECTIONS: { title: string; keys: string[] }[] = [
  {
    title: 'Administrative',
    keys: [
      'title',
      'anticipated_start_date',
      'anticipated_completion_date',
      'stage',
      'named_contact',
      'named_contact_email',
      'named_contact_address',
      'organisational_affiliation',
      'review_team_members',
      'collaborators',
    ],
  },
  {
    title: 'Methods',
    keys: [
      'review_question',
      'searches',
      'url_to_protocol',
      'condition_or_domain',
      'participants',
      'intervention_exposure',
      'comparators_control',
      'types_of_study',
      'context',
    ],
  },
  {
    title: 'Outcomes',
    keys: ['primary_outcomes'],
  },
  {
    title: 'Funding & conflicts',
    keys: ['funding_sources', 'conflicts_of_interest'],
  },
]

const LABEL_BY_KEY = Object.fromEntries(
  PROSPERO_FIELDS.map((f) => [f.key, f.label] as const),
)

/** Lines a textarea would render — covers the multi-line cases. */
const MULTILINE_KEYS = new Set([
  'review_team_members',
  'searches',
  'review_question',
  'condition_or_domain',
  'participants',
  'intervention_exposure',
  'comparators_control',
  'types_of_study',
  'context',
  'primary_outcomes',
  'funding_sources',
  'conflicts_of_interest',
  'collaborators',
  'named_contact_address',
])

export function PROSPEROForm({ projectId }: { projectId: string }) {
  const query = useProspero(projectId)
  const update = useUpdateProspero(projectId)
  const exportDraft = useExportProspero(projectId)

  // Local edits — flushed on Save.
  const [draft, setDraft] = useState<Record<string, string>>({})

  useEffect(() => {
    if (query.data?.fields) {
      setDraft(query.data.fields)
    }
  }, [query.data])

  const dirty = useMemo(() => {
    if (!query.data) return false
    return PROSPERO_FIELDS.some(
      ({ key }) => (draft[key] ?? '') !== (query.data!.fields[key] ?? ''),
    )
  }, [draft, query.data])

  function setField(key: string, value: string) {
    setDraft((d) => ({ ...d, [key]: value }))
  }

  function autofill() {
    // Re-fetch which will surface server-side defaults again.
    query.refetch()
    toast.success('Re-loaded auto-fill from review')
  }

  function save() {
    update.mutate(draft, {
      onSuccess: () => toast.success('PROSPERO draft saved'),
      onError: () => toast.error('Failed to save PROSPERO draft'),
    })
  }

  function copyFormatted() {
    exportDraft.mutate(undefined, {
      onSuccess: async (text) => {
        try {
          await navigator.clipboard.writeText(text)
          toast.success('Copied formatted PROSPERO text to clipboard')
        } catch {
          toast.error('Clipboard unavailable; the text is in the response body')
        }
      },
      onError: () => toast.error('Failed to fetch export text'),
    })
  }

  if (query.isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading PROSPERO
        draft…
      </div>
    )
  }
  if (query.isError) {
    return (
      <div className="rounded border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        Could not load PROSPERO draft.
      </div>
    )
  }

  return (
    <div className="space-y-6" data-testid="prospero-form">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          onClick={autofill}
          data-testid="prospero-autofill"
        >
          Re-load auto-fill from review
        </Button>
        <Button onClick={save} disabled={!dirty || update.isPending}>
          {update.isPending ? 'Saving…' : 'Save draft'}
        </Button>
        <Button
          variant="secondary"
          onClick={copyFormatted}
          data-testid="prospero-copy"
        >
          Copy formatted text
        </Button>
      </div>

      {SECTIONS.map((section) => (
        <section key={section.title} className="space-y-3">
          <h3 className="text-sm font-medium uppercase text-muted-foreground">
            {section.title}
          </h3>
          {section.keys.map((key) => {
            const label = LABEL_BY_KEY[key] ?? key
            const value = draft[key] ?? ''
            return (
              <div key={key}>
                <Label htmlFor={`prospero-${key}`}>{label}</Label>
                {MULTILINE_KEYS.has(key) ? (
                  <Textarea
                    id={`prospero-${key}`}
                    data-testid={`prospero-field-${key}`}
                    value={value}
                    onChange={(e) => setField(key, e.target.value)}
                    rows={3}
                  />
                ) : (
                  <Input
                    id={`prospero-${key}`}
                    data-testid={`prospero-field-${key}`}
                    value={value}
                    onChange={(e) => setField(key, e.target.value)}
                  />
                )}
              </div>
            )
          })}
        </section>
      ))}
    </div>
  )
}
