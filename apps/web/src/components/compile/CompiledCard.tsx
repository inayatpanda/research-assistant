import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, GripVertical, MessageSquareText, Sparkles, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  type CardDraftResponse,
  type CompiledCard as CardType,
  type ManuscriptSectionName,
  compilationApi,
  highlightsApi,
  manuscriptApi,
} from '@/lib/api'
import { highlightColors, sectionLabels } from '@/lib/tokens'
import { cn } from '@/lib/utils'

import { AISuggestionBlock } from './AISuggestionBlock'

const COLOUR_TO_SECTION: Record<CardType['colour'], ManuscriptSectionName> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

export function CompiledCard({
  card,
  projectId,
  dragHandleProps,
}: {
  card: CardType
  projectId: string
  /** Spread these onto the drag handle button to make ONLY that element draggable. */
  dragHandleProps?: {
    attributes: Record<string, unknown>
    listeners: Record<string, unknown> | undefined
  }
}) {
  const palette = highlightColors[card.colour]
  const qc = useQueryClient()
  const [draft, setDraft] = useState<CardDraftResponse | null>(null)

  const generate = useMutation({
    mutationFn: () => compilationApi.cardDraft(card.highlight_id),
    onSuccess: (resp) => setDraft(resp),
    onError: (e: Error) => toast.error(e.message),
  })

  const del = useMutation({
    mutationFn: () => highlightsApi.delete(card.highlight_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['compilation', projectId, card.colour] })
      qc.invalidateQueries({ queryKey: ['highlights'] })
      toast.success('Highlight deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  async function handleAccept(text: string) {
    const section = COLOUR_TO_SECTION[card.colour]
    try {
      const current = await manuscriptApi.getSection(projectId, section)
      const next = current.content ? `${current.content.trim()} ${text}` : text
      await manuscriptApi.upsertSection(projectId, section, next)
      qc.invalidateQueries({ queryKey: ['manuscript-section', projectId, section] })
      toast.success(`Added to ${section}`)
      setDraft(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to save')
    }
  }

  return (
    <div
      className="group flex gap-3 rounded-lg border border-border bg-white overflow-hidden"
      style={{ boxShadow: '0 1px 2px rgba(15,17,23,0.04)' }}
    >
      <div className="w-1 shrink-0" style={{ background: palette.solid }} aria-hidden />
      <div className="flex-1 min-w-0 p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>{sectionLabels[card.colour]}</span>
            <span>·</span>
            <span>page {card.page_number}</span>
            <Badge
              variant="outline"
              className={cn(
                'h-5 text-[10px] uppercase tracking-wider font-medium ml-1',
              )}
              style={{ borderColor: palette.ring, color: palette.solid, background: palette.fill }}
            >
              {card.citation}
            </Badge>
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Link
              to={`/projects/${projectId}/reader/${card.article_id}`}
              className="text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-muted"
              aria-label="Open in Reader"
            >
              <ExternalLink className="h-3 w-3" />
              Reader
            </Link>
            <button
              onClick={() => {
                if (confirm('Delete this highlight?')) del.mutate()
              }}
              className="text-[11px] text-rose-600 hover:text-rose-700 inline-flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-rose-50"
            >
              <Trash2 className="h-3 w-3" />
            </button>
            {dragHandleProps && (
              <button
                {...dragHandleProps.attributes}
                {...(dragHandleProps.listeners ?? {})}
                aria-label="Drag to reorder"
                className="text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing p-0.5"
              >
                <GripVertical className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Source highlight */}
        <div
          className="rounded-md p-3 text-[13px] leading-[20px] border"
          style={{ background: palette.fill, borderColor: palette.ring }}
        >
          “{card.selected_text}”
        </div>

        {/* User paraphrase */}
        <div>
          <div className="flex items-center gap-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
            <MessageSquareText className="h-3 w-3" />
            Your paraphrase
          </div>
          {card.user_note ? (
            <div className="text-[13px] leading-[20px] italic">{card.user_note}</div>
          ) : (
            <div className="text-[12px] text-muted-foreground italic">
              No paraphrase. Open in Reader and add one for richer AI drafts.
            </div>
          )}
        </div>

        {/* Article meta */}
        <div className="text-[11px] text-muted-foreground line-clamp-1">
          {card.article_title}
          {card.article_journal ? ` · ${card.article_journal}` : ''}
        </div>

        {/* AI draft */}
        {draft && (
          <AISuggestionBlock
            text={draft.draft}
            pending={false}
            onAccept={handleAccept}
            onReject={() => setDraft(null)}
            acceptLabel="Push to Manuscript"
            acceptHint={`Appends this sentence to the ${COLOUR_TO_SECTION[card.colour]} section.`}
          />
        )}
        {generate.isPending && !draft && (
          <AISuggestionBlock text={null} pending={true} onAccept={() => {}} onReject={() => {}} />
        )}

        {/* Actions */}
        {!draft && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="h-8 text-[12px] border-ai/30 text-ai hover:bg-ai-tint hover:text-ai"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              {generate.isPending ? 'Drafting…' : 'Generate sentence'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

