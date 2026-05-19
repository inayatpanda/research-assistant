import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  type HighlightColour,
  type ManuscriptSectionName,
  type SectionDraftResponse,
  compilationApi,
  manuscriptApi,
} from '@/lib/api'

import { AISuggestionBlock } from './AISuggestionBlock'

const COLOUR_TO_SECTION: Record<HighlightColour, ManuscriptSectionName> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

export function SectionDraftPanel({
  projectId,
  colour,
  cardCount,
}: {
  projectId: string
  colour: HighlightColour
  cardCount: number
}) {
  const section = COLOUR_TO_SECTION[colour]
  const qc = useQueryClient()
  const [draft, setDraft] = useState<SectionDraftResponse | null>(null)

  const { data: msSection } = useQuery({
    queryKey: ['manuscript-section', projectId, section],
    queryFn: () => manuscriptApi.getSection(projectId, section),
  })

  const generate = useMutation({
    mutationFn: () => compilationApi.sectionDraft(projectId, colour),
    onSuccess: (resp) => setDraft(resp),
    onError: (e: Error) => toast.error(e.message),
  })

  async function handleAccept(text: string) {
    const current = msSection?.content ?? ''
    if (current.trim().length > 0) {
      if (!confirm(`${section} already has content. Replace it with this draft?`)) return
    }
    try {
      // E2E-sweep #C1: the server-side draft contains
      // `<sup data-citation data-article-id="…">` markup. Wrap the
      // paragraph so the section persists as valid block-level HTML.
      const paragraph = text.trim().startsWith('<p>') ? text : `<p>${text}</p>`
      await manuscriptApi.upsertSection(projectId, section, paragraph)
      qc.invalidateQueries({ queryKey: ['manuscript-section', projectId, section] })
      toast.success(`${section} updated`)
      setDraft(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    }
  }

  return (
    <div className="rounded-lg border border-border bg-white p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-[14px] font-semibold tracking-tight">
            <FileText className="h-4 w-4 text-muted-foreground" />
            {section} draft
          </div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {msSection
              ? msSection.content
                ? `${msSection.word_count} words in manuscript`
                : 'No content saved yet'
              : 'Loading…'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/projects/${projectId}/manuscript?tab=${colour}`}
            className="text-[12px] text-accent hover:underline px-2 py-1 rounded hover:bg-accent/5"
          >
            Open in Manuscript →
          </Link>
        </div>
      </div>

      {generate.isPending && (
        <AISuggestionBlock text={null} pending={true} onAccept={() => {}} onReject={() => {}} />
      )}
      {draft && !generate.isPending && (
        <AISuggestionBlock
          text={draft.draft}
          pending={false}
          onAccept={handleAccept}
          onReject={() => setDraft(null)}
          acceptLabel="Push to Manuscript"
          acceptHint={
            msSection?.content
              ? `Replaces the existing ${section} section (${msSection.word_count} words).`
              : `Writes this paragraph into the ${section} section.`
          }
        />
      )}
      {draft?.used_citations && draft.used_citations.length > 0 && (
        <div className="text-[11px] text-muted-foreground">
          References: {draft.used_citations.join(' · ')}
        </div>
      )}

      {!draft && !generate.isPending && (
        <Button
          onClick={() => generate.mutate()}
          disabled={cardCount === 0}
          className="h-9 text-[13px] bg-ai hover:bg-ai/90 text-white"
        >
          <Sparkles className="h-3.5 w-3.5 mr-1.5" />
          Generate paragraph from {cardCount} {cardCount === 1 ? 'card' : 'cards'}
        </Button>
      )}
    </div>
  )
}
