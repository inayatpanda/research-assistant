/**
 * Phase M1.2 — Full-screen reader for a single Learn entry.
 *
 * Mounted at `/m/learn/:category/:slug`. The five categories share a
 * common Markdown rendering pipeline (the desktop MarkdownView) — only
 * the metadata strip up top differs per-category.
 *
 * For walkthrough entries we additionally:
 *   - Show a "min read" pill from `estimated_reading_minutes`.
 *   - Surface an "On this page" button in the header that opens the
 *     TOC inside a <BottomSheet>.
 *
 * "Related concepts" appears at the bottom as a row of chip-style
 * buttons that route to other Learn entries within the same category.
 * (The desktop page also surfaces these, but as inline badges; on
 * mobile we want them tappable.)
 */
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Clock, ListTree, WifiOff } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { MarkdownView } from '@/components/learn/MarkdownView'
import { Badge } from '@/components/ui/badge'
import {
  learnApi,
  type LearnChecklistRead,
  type LearnEconomicsRead,
  type LearnStatTestRead,
  type LearnSubmissionRead,
  type LearnWalkthroughRead,
} from '@/lib/api'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'
import { MobileHeader } from '../components/MobileHeader'
import { cacheable, entryKey } from '../lib/offlineLearn'
import type { LearnCategory } from './MobileLearn'

type AnyEntry =
  | LearnStatTestRead
  | LearnChecklistRead
  | LearnEconomicsRead
  | LearnSubmissionRead
  | LearnWalkthroughRead

function isWalkthrough(e: AnyEntry): e is LearnWalkthroughRead {
  return 'estimated_reading_minutes' in e
}

function extractToc(src: string): { id: string; text: string }[] {
  const out: { id: string; text: string }[] = []
  for (const raw of src.split('\n')) {
    const line = raw.trim()
    if (line.startsWith('## ') && !line.startsWith('### ')) {
      const text = line.replace(/^##\s+/, '')
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
      out.push({ id, text })
    }
  }
  return out
}

export default function MobileLearnEntryPage() {
  const navigate = useNavigate()
  const params = useParams<{ category: LearnCategory; slug: string }>()
  const category = params.category as LearnCategory
  const slug = params.slug ?? ''
  const [tocOpen, setTocOpen] = useState(false)

  const detail = useQuery({
    queryKey: ['mlearn', 'entry', category, slug],
    queryFn: async () => {
      return cacheable<AnyEntry>(entryKey(category, slug), async () => {
        switch (category) {
          case 'stat-tests':
            return (await learnApi.getStatTest(slug)) as AnyEntry
          case 'checklists':
            return (await learnApi.getChecklist(slug)) as AnyEntry
          case 'economics':
            return (await learnApi.getEconomics(slug)) as AnyEntry
          case 'submission':
            return (await learnApi.getSubmission(slug)) as AnyEntry
          case 'walkthroughs':
            return (await learnApi.getWalkthrough(slug)) as AnyEntry
          default:
            throw new Error(`Unknown category: ${category}`)
        }
      })
    },
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  })

  const entry = detail.data?.data
  const offline = detail.data?.offline ?? false

  // Only walkthroughs surface a TOC bottom-sheet button.
  const toc = useMemo(
    () => (entry && isWalkthrough(entry) ? extractToc(entry.body_md) : []),
    [entry],
  )
  const showTocButton = entry && isWalkthrough(entry) && toc.length > 0

  const related = entry && 'related_concepts' in entry ? entry.related_concepts : []

  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader
        title={entry?.title ?? 'Learn entry'}
        onBack={() => navigate(-1)}
        right={
          showTocButton ? (
            <button
              type="button"
              onClick={() => setTocOpen(true)}
              aria-label="Open table of contents"
              data-testid="mlearn-entry-toc-button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-md text-foreground hover:bg-muted"
            >
              <ListTree className="h-5 w-5" />
            </button>
          ) : null
        }
      />

      {detail.isLoading && (
        <div className="px-4 py-12 text-center text-[13px] text-muted-foreground">
          Loading entry…
        </div>
      )}

      {!detail.isLoading && !entry && (
        <MobileEmpty
          icon={BookOpen}
          title="Entry not found"
          subtitle="This Learn entry may have been removed or renamed."
          cta={{ label: 'Back to Learn', onClick: () => navigate('/m/learn') }}
          testId="mlearn-entry-missing"
        />
      )}

      {entry && (
        <div data-testid="mlearn-entry-body" className="space-y-4 px-4 py-3">
          {/* Header strip */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-[10px] uppercase tracking-wide">
                {category.replace(/-/g, ' ')}
              </Badge>
              {entry && isWalkthrough(entry) && (
                <Badge
                  variant="secondary"
                  className="flex items-center gap-1 text-[11px]"
                  data-testid="mlearn-reading-time"
                >
                  <Clock className="h-3 w-3" />
                  {entry.estimated_reading_minutes} min read
                </Badge>
              )}
              {offline && (
                <Badge
                  data-testid="mlearn-entry-offline-badge"
                  variant="outline"
                  className="flex items-center gap-1 text-[10px] uppercase tracking-wide"
                >
                  <WifiOff className="h-3 w-3" />
                  Offline
                </Badge>
              )}
            </div>
            <h1 className="text-[20px] font-semibold tracking-tight leading-tight">
              {entry.title}
            </h1>
          </div>

          {/* Body */}
          <div className="prose prose-sm max-w-none">
            <MarkdownView source={entry.body_md} />
          </div>

          {/* Related concepts */}
          {related && related.length > 0 && (
            <div data-testid="mlearn-related-concepts" className="space-y-2 pt-2">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Related concepts
              </div>
              <div className="flex flex-wrap gap-2">
                {related.map((rel) => (
                  <button
                    key={rel}
                    type="button"
                    data-testid={`mlearn-related-${rel}`}
                    onClick={() => navigate(`/m/learn/${category}/${rel}`)}
                    className="inline-flex h-8 items-center rounded-full border border-border bg-card px-3 text-[12px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {rel.replace(/-/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <BottomSheet
        open={tocOpen}
        onClose={() => setTocOpen(false)}
        title="On this page"
        snapPoints={['50%']}
      >
        {toc.length === 0 ? (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No sections.
          </div>
        ) : (
          <ol data-testid="mlearn-toc-list" className="space-y-2.5 py-2">
            {toc.map((t) => (
              <li key={t.id}>
                <a
                  href={`#${t.id}`}
                  onClick={() => setTocOpen(false)}
                  className="block rounded-md px-2 py-2 text-[14px] text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {t.text}
                </a>
              </li>
            ))}
          </ol>
        )}
      </BottomSheet>
    </div>
  )
}
